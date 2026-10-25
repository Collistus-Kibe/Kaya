import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import List, Optional, Set
import av

SUPPORTED_AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".m4a", ".flac"}

def discover_audio_files(audio_dir: Path) -> List[Path]:
    """Recursively discover supported audio files in audio_dir.
    
    Supports .mp3, .wav, .m4a, .flac files.
    """
    if not audio_dir.exists():
        return []
    
    found: List[Path] = []
    for root, _, files in os.walk(audio_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in SUPPORTED_AUDIO_EXTENSIONS:
                found.append(Path(root) / file)
                
    found.sort()
    return found

def get_audio_duration(file_path: Path) -> float:
    """Get the duration of an audio file in seconds.
    
    Uses standard wave module for .wav if possible, otherwise PyAV.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    if file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass
            
    with av.open(str(file_path)) as container:
        if container.duration is not None:
            return float(container.duration) / float(av.time_base)
        if container.streams.audio:
            stream = container.streams.audio[0]
            if stream.duration is not None and stream.time_base is not None:
                return float(stream.duration * stream.time_base)
                
    return 0.0

def convert_to_wav(input_path: Path, output_path: Path, target_sr: int = 16000) -> Path:
    """Convert an audio file to 16 kHz mono WAV.
    
    Uses ffmpeg command-line if available, otherwise PyAV.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try ffmpeg CLI first if available
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(input_path),
            "-ar", str(target_sr),
            "-ac", "1",
            str(output_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and output_path.exists():
            return output_path

    # Fallback to PyAV conversion
    resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)
    with av.open(str(input_path)) as in_container:
        if not in_container.streams.audio:
            raise ValueError(f"No audio stream found in {input_path}")
        audio_stream = in_container.streams.audio[0]
        
        with wave.open(str(output_path), "wb") as out_wav:
            out_wav.setnchannels(1)
            out_wav.setsampwidth(2)  # 16-bit PCM = 2 bytes
            out_wav.setframerate(target_sr)
            
            for packet in in_container.demux(audio_stream):
                for frame in packet.decode():
                    for resampled in resampler.resample(frame):
                        out_wav.writeframes(resampled.to_ndarray().tobytes())
                        
            # Flush remaining frames
            for resampled in resampler.resample(None):
                out_wav.writeframes(resampled.to_ndarray().tobytes())
                
    return output_path

def clip_audio(input_path: Path, output_path: Path, start_s: float, end_s: Optional[float] = None) -> Path:
    """Clip audio from start_s to end_s.
    
    For WAV files, uses standard wave module.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # If not already WAV, convert first or use ffmpeg/av
    if input_path.suffix.lower() != ".wav":
        temp_wav = output_path.with_suffix(".tmp.wav")
        convert_to_wav(input_path, temp_wav)
        input_file = temp_wav
        cleanup_temp = True
    else:
        input_file = input_path
        cleanup_temp = False
        
    try:
        with wave.open(str(input_file), "rb") as wf:
            sr = wf.getframerate()
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            total_frames = wf.getnframes()
            
            start_frame = max(0, int(start_s * sr))
            if end_s is not None:
                end_frame = min(int(end_s * sr), total_frames)
            else:
                end_frame = total_frames
                
            num_frames = max(0, end_frame - start_frame)
            wf.setpos(start_frame)
            frames = wf.readframes(num_frames)
            
        with wave.open(str(output_path), "wb") as out_wf:
            out_wf.setnchannels(nchannels)
            out_wf.setsampwidth(sampwidth)
            out_wf.setframerate(sr)
            out_wf.writeframes(frames)
    finally:
        if cleanup_temp and input_file.exists():
            input_file.unlink()
            
    return output_path
