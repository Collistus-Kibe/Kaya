import pytest
from pathlib import Path
from kayasearch.config import Config, PathsConfig, TranscriptionConfig, SearchConfig, PrivacyConfig
from kayasearch.db import connect, init_db
from kayasearch.transcribe import FakeTranscriber, Segment, Word
from kayasearch.audio import convert_to_wav
from kayasearch.pipeline import run_pipeline, process_file
from .test_audio import create_synthetic_wav

@pytest.fixture
def pipeline_env(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    db_path = tmp_path / "db" / "kaya.db"
    work_dir = tmp_path / "work"
    models_dir = tmp_path / "models"

    cfg = Config(
        paths=PathsConfig(
            audio_dir=audio_dir,
            db_path=db_path,
            work_dir=work_dir,
            models_dir=models_dir
        ),
        transcription=TranscriptionConfig(
            model_size="small",
            language="sw",
            device="auto",
            compute_type="auto",
            beam_size=5,
            vad_filter=True,
            model_path=None
        ),
        search=SearchConfig(
            fuzzy_threshold=85,
            max_results=50
        ),
        privacy=PrivacyConfig(
            offline=True
        )
    )
    return cfg

def test_pipeline_basic_run(pipeline_env):
    # Create two synthetic wav files
    file1 = pipeline_env.paths.audio_dir / "sample1.wav"
    file2 = pipeline_env.paths.audio_dir / "sample2.wav"
    create_synthetic_wav(file1, duration_s=1.0)
    create_synthetic_wav(file2, duration_s=1.0)

    fake_transcriber = FakeTranscriber()
    stats = run_pipeline(pipeline_env, transcriber=fake_transcriber)

    assert stats["total"] == 2
    assert stats["done"] == 2
    assert stats["failed"] == 0
    assert stats["skipped"] == 0

    conn = connect(pipeline_env.paths.db_path)
    cur = conn.execute("SELECT COUNT(*) FROM recordings WHERE status = 'done'")
    assert cur.fetchone()[0] == 2

    cur = conn.execute("SELECT COUNT(*) FROM segments")
    assert cur.fetchone()[0] == 2  # 1 segment per file from FakeTranscriber

    cur = conn.execute("SELECT COUNT(*) FROM vocab")
    assert cur.fetchone()[0] > 0
    conn.close()

def test_pipeline_resume(pipeline_env):
    file1 = pipeline_env.paths.audio_dir / "sample1.wav"
    create_synthetic_wav(file1, duration_s=1.0)

    fake = FakeTranscriber()
    stats1 = run_pipeline(pipeline_env, transcriber=fake)
    assert stats1["done"] == 1

    # Running pipeline again without changes should skip the file
    stats2 = run_pipeline(pipeline_env, transcriber=fake)
    assert stats2["skipped"] == 1
    assert stats2["done"] == 0

def test_pipeline_corrupt_file_resilience(pipeline_env):
    # Create one valid audio file and one corrupt file
    valid_file = pipeline_env.paths.audio_dir / "good.wav"
    create_synthetic_wav(valid_file, duration_s=1.0)

    corrupt_file = pipeline_env.paths.audio_dir / "corrupt.wav"
    corrupt_file.write_bytes(b"not an audio file at all")

    fake = FakeTranscriber()
    stats = run_pipeline(pipeline_env, transcriber=fake)

    assert stats["total"] == 2
    assert stats["done"] == 1
    assert stats["failed"] == 1

    conn = connect(pipeline_env.paths.db_path)
    cur = conn.execute("SELECT status, error FROM recordings WHERE path LIKE '%corrupt.wav'")
    row = cur.fetchone()
    assert row["status"] == "failed"
    assert row["error"] is not None
    conn.close()
