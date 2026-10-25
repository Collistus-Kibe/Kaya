from pathlib import Path
import pytest
from kayasearch.transcribe import (
    Transcriber,
    FakeTranscriber,
    Segment,
    Word,
    TranscriptionResult
)

def test_transcriber_protocol():
    fake = FakeTranscriber()
    assert isinstance(fake, Transcriber)

def test_fake_transcriber_default(tmp_path):
    audio_file = tmp_path / "dummy.wav"
    audio_file.touch()

    fake = FakeTranscriber()
    res = fake.transcribe(audio_file)

    assert isinstance(res, TranscriptionResult)
    assert len(res.segments) == 1
    assert res.segments[0].text == "Jambo bwana habari"
    assert len(res.segments[0].words) == 3
    assert res.segments[0].words[0].word == "Jambo"
    assert res.model_name == "fake-whisper"
    assert "fake-whisper" in res.settings

def test_fake_transcriber_custom_segments(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.touch()

    custom_words = [
        Word(word="Wazee", start_s=0.0, end_s=0.5, confidence=0.99),
        Word(word="wa", start_s=0.6, end_s=0.8, confidence=0.98),
        Word(word="Kaya", start_s=0.9, end_s=1.5, confidence=0.95),
    ]
    custom_segments = [
        Segment(
            start_s=0.0,
            end_s=1.5,
            text="Wazee wa Kaya",
            confidence=0.97,
            words=custom_words
        )
    ]

    fake = FakeTranscriber(
        canned_segments=custom_segments,
        model_name="test-model"
    )
    res = fake.transcribe(audio_file)
    assert len(res.segments) == 1
    assert res.segments[0].text == "Wazee wa Kaya"
    assert res.model_name == "test-model"

def test_fake_transcriber_missing_file(tmp_path):
    fake = FakeTranscriber()
    with pytest.raises(FileNotFoundError):
        fake.transcribe(tmp_path / "nonexistent.wav")
