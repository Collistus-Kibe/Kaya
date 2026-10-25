import math
import struct
import wave
from pathlib import Path

from kayasearch.config import load_config
from kayasearch.db import (
    connect,
    init_db,
    insert_recording,
    update_recording_status,
    insert_segment,
    insert_word,
    add_to_vocab,
)
from kayasearch.text import normalize_text, tokenize
from kayasearch.search import add_variant

def create_tone_wav(path: Path, duration_s: float = 12.0, freq: float = 220.0, sample_rate: int = 16000) -> Path:
    """Generate audio file for demo playback."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_data = bytearray()
        for i in range(num_samples):
            # Gentle oscillating chime
            val = int(6000.0 * math.sin(2.0 * math.pi * freq * i / sample_rate) * math.exp(-0.0001 * (i % 8000)))
            raw_data.extend(struct.pack("<h", val))
        wf.writeframes(raw_data)
    return path

def seed_sample_archive():
    config = load_config()
    
    audio_dir = config.paths.audio_dir
    db_path = config.paths.db_path
    
    audio_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = connect(db_path)
    init_db(conn)
    
    # 1. Sample Recording 1
    file1 = audio_dir / "kaya_elders_oral_history_01.wav"
    create_tone_wav(file1, duration_s=15.0, freq=300.0)
    
    rec1_id = insert_recording(conn, str(file1), 15.0, status="done")
    update_recording_status(conn, rec1_id, "done")
    
    seg1_1 = insert_segment(
        conn, rec1_id, 0.0, 6.5,
        "Wazee wa Kaya wanakutana asubuhi kujadili mila na desturi za kale.",
        0.94, "whisper-small-sw", "{}"
    )
    for w in tokenize("Wazee wa Kaya wanakutana asubuhi kujadili mila na desturi za kale."):
        add_to_vocab(conn, w)
        
    seg1_2 = insert_segment(
        conn, rec1_id, 7.0, 14.5,
        "Katika mila zetu za pwani, ng'ombe na mifugo huheshimiwa sana shambani.",
        0.91, "whisper-small-sw", "{}"
    )
    for w in tokenize("Katika mila zetu za pwani, ng'ombe na mifugo huheshimiwa sana shambani."):
        add_to_vocab(conn, w)
        
    # 2. Sample Recording 2
    file2 = audio_dir / "coastal_traditions_and_stories_02.wav"
    create_tone_wav(file2, duration_s=12.0, freq=440.0)
    
    rec2_id = insert_recording(conn, str(file2), 12.0, status="done")
    update_recording_status(conn, rec2_id, "done")
    
    seg2_1 = insert_segment(
        conn, rec2_id, 0.0, 5.8,
        "Historia ya kaya zetu ilianza vizazi vingi vilivyopita pwani ya Kenya.",
        0.96, "whisper-small-sw", "{}"
    )
    for w in tokenize("Historia ya kaya zetu ilianza vizazi vingi vilivyopita pwani ya Kenya."):
        add_to_vocab(conn, w)
        
    seg2_2 = insert_segment(
        conn, rec2_id, 6.2, 11.8,
        "Mizimu ya wazee hutukumbusha kulinda misitu ya Kaya na vyanzo vya maji.",
        0.89, "whisper-small-sw", "{}"
    )
    for w in tokenize("Mizimu ya wazee hutukumbusha kulinda misitu ya Kaya na vyanzo vya maji."):
        add_to_vocab(conn, w)

    # 3. Add default variants
    add_variant(conn, "ng'ombe", "ngombe", "Coastal spelling without intra-word apostrophe")
    add_variant(conn, "mzee", "muzee", "Dialect variant for elder")
    
    conn.commit()
    conn.close()
    print("Sample archive and database seeded successfully.")

if __name__ == "__main__":
    seed_sample_archive()
