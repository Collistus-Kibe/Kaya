import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List

from kayasearch.config import Config
from kayasearch.db import (
    connect,
    init_db,
    insert_recording,
    update_recording_status,
    insert_segment,
    insert_word,
    add_to_vocab,
)
from kayasearch.audio import discover_audio_files, get_audio_duration, convert_to_wav
from kayasearch.transcribe import Transcriber, FasterWhisperTranscriber
from kayasearch.text import normalize_text, tokenize

# Configure logger (Rule 6: Never log transcript text. Log file names, counts, durations and errors only.)
logger = logging.getLogger("kayasearch.pipeline")

def get_or_create_recording(conn: sqlite3.Connection, file_path_str: str, duration_s: float = 0.0) -> sqlite3.Row:
    """Retrieve existing recording record or create a new pending one."""
    cursor = conn.execute("SELECT * FROM recordings WHERE path = ?", (file_path_str,))
    row = cursor.fetchone()
    if row is None:
        rec_id = insert_recording(conn, file_path_str, duration_s, status="pending")
        conn.commit()
        cursor = conn.execute("SELECT * FROM recordings WHERE id = ?", (rec_id,))
        row = cursor.fetchone()
    return row

def process_file(
    conn: sqlite3.Connection,
    audio_path: Path,
    transcriber: Transcriber,
    work_dir: Path
) -> str:
    """Process a single audio file with resume support and error isolation.
    
    Returns status: 'done', 'skipped', or 'failed'.
    """
    file_path_str = str(audio_path)
    row = get_or_create_recording(conn, file_path_str)
    
    if row["status"] == "done":
        logger.info(f"Skipping already processed file: {audio_path.name}")
        return "skipped"
        
    rec_id = row["id"]
    temp_wav: Optional[Path] = None
    
    try:
        duration_s = get_audio_duration(audio_path)
        logger.info(f"Processing {audio_path.name} (duration: {duration_s:.1f}s)")
        
        # Convert to 16kHz mono WAV in work_dir
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_wav = work_dir / f"proc_{rec_id}_{audio_path.stem}.wav"
        convert_to_wav(audio_path, temp_wav, target_sr=16000)
        
        # Transcribe
        result = transcriber.transcribe(temp_wav)
        
        # Persist segments, words, and vocab
        with conn:
            for seg in result.segments:
                seg_id = insert_segment(
                    conn,
                    recording_id=rec_id,
                    start_s=seg.start_s,
                    end_s=seg.end_s,
                    text=seg.text,
                    confidence=seg.confidence,
                    model=result.model_name,
                    settings=result.settings
                )
                
                # If segment words are provided, insert them
                if seg.words:
                    for w in seg.words:
                        norm_w = normalize_text(w.word)
                        if norm_w:
                            insert_word(conn, seg_id, w.word, norm_w, w.start_s, w.end_s, w.confidence)
                            add_to_vocab(conn, norm_w)
                else:
                    # Fallback to tokenizing segment text if word timestamps not available
                    for word_token in tokenize(seg.text):
                        add_to_vocab(conn, word_token)
                        
            conn.execute("UPDATE recordings SET duration_s = ? WHERE id = ?", (duration_s, rec_id))
            update_recording_status(conn, rec_id, status="done")
            
        logger.info(f"Successfully processed {audio_path.name} ({len(result.segments)} segments)")
        return "done"
        
    except Exception as e:
        # Never log transcript text - log only file name and error message
        logger.error(f"Error processing {audio_path.name}: {e}")
        try:
            update_recording_status(conn, rec_id, status="failed", error=str(e))
            conn.commit()
        except Exception:
            pass
        return "failed"
    finally:
        if temp_wav is not None and temp_wav.exists():
            try:
                temp_wav.unlink()
            except OSError:
                pass

def run_pipeline(config: Config, transcriber: Optional[Transcriber] = None) -> Dict[str, int]:
    """Run batch ingestion pipeline over audio directory with resume support."""
    conn = connect(config.paths.db_path)
    init_db(conn)
    
    if transcriber is None:
        model_target = config.transcription.model_path
        if not model_target:
            if (config.paths.models_dir / "model.bin").exists():
                model_target = str(config.paths.models_dir)
            else:
                model_target = config.transcription.model_size

        transcriber = FasterWhisperTranscriber(
            model_size_or_path=model_target,
            language=config.transcription.language,
            device=config.transcription.device,
            compute_type=config.transcription.compute_type,
            beam_size=config.transcription.beam_size,
            vad_filter=config.transcription.vad_filter,
            download_root=str(config.paths.models_dir)
        )
        
    audio_files = discover_audio_files(config.paths.audio_dir)
    stats = {"total": len(audio_files), "done": 0, "skipped": 0, "failed": 0}
    
    for audio_path in audio_files:
        status = process_file(
            conn=conn,
            audio_path=audio_path,
            transcriber=transcriber,
            work_dir=config.paths.work_dir
        )
        if status in stats:
            stats[status] += 1
            
    conn.close()
    return stats
