import math
import struct
import wave
from pathlib import Path
import pytest
from kayasearch.audio import (
    discover_audio_files,
    get_audio_duration,
    convert_to_wav,
    clip_audio,
)

def create_synthetic_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 16000, channels: int = 1) -> Path:
    """Generate a clean synthetic WAV file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 440 Hz tone
        raw_data = bytearray()
        for i in range(num_samples):
            value = int(10000.0 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            for _ in range(channels):
                raw_data.extend(struct.pack("<h", value))
        wf.writeframes(raw_data)
    return path

def test_discover_audio_files(tmp_path):
    (tmp_path / "song1.wav").touch()
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "interview.mp3").touch()
    (tmp_path / "subdir" / "chant.flac").touch()
    (tmp_path / "subdir" / "story.m4a").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "db.sqlite3").touch()

    files = discover_audio_files(tmp_path)
    file_names = [f.name for f in files]
    assert len(files) == 4
    assert sorted(file_names) == ["chant.flac", "interview.mp3", "song1.wav", "story.m4a"]

def test_get_audio_duration(tmp_path):
    wav_file = tmp_path / "test_2s.wav"
    create_synthetic_wav(wav_file, duration_s=2.0, sample_rate=16000)
    
    dur = get_audio_duration(wav_file)
    assert pytest.approx(dur, rel=1e-2) == 2.0

def test_convert_to_wav(tmp_path):
    input_wav = tmp_path / "input_stereo.wav"
    # Create stereo 8000 Hz wav
    create_synthetic_wav(input_wav, duration_s=1.5, sample_rate=8000, channels=2)
    
    output_wav = tmp_path / "converted_16k_mono.wav"
    res_path = convert_to_wav(input_wav, output_wav, target_sr=16000)
    assert res_path.exists()
    
    with wave.open(str(output_wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        # Check duration is approximately 1.5s
        frames = wf.getnframes()
        assert pytest.approx(frames / 16000.0, rel=1e-2) == 1.5

def test_clip_audio(tmp_path):
    wav_file = tmp_path / "long.wav"
    create_synthetic_wav(wav_file, duration_s=3.0, sample_rate=16000)
    
    clipped = tmp_path / "clipped.wav"
    clip_audio(wav_file, clipped, start_s=1.0, end_s=2.5)
    
    assert clipped.exists()
    with wave.open(str(clipped), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        dur = wf.getnframes() / wf.getframerate()
        assert pytest.approx(dur, rel=1e-2) == 1.5
