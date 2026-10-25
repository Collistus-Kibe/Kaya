import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

@dataclass
class Word:
    word: str
    start_s: float
    end_s: float
    confidence: float

@dataclass
class Segment:
    start_s: float
    end_s: float
    text: str
    confidence: float
    words: List[Word] = field(default_factory=list)

@dataclass
class TranscriptionResult:
    segments: List[Segment]
    language: str
    model_name: str
    settings: str

@runtime_checkable
class Transcriber(Protocol):
    """Protocol for audio transcription engines."""
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        ...

class FakeTranscriber:
    """Mock transcriber for testing without GPU, network, or Whisper models."""
    def __init__(
        self,
        canned_segments: Optional[List[Segment]] = None,
        language: str = "sw",
        model_name: str = "fake-whisper",
        settings: Optional[str] = None
    ) -> None:
        self.canned_segments = canned_segments
        self.language = language
        self.model_name = model_name
        self.settings = settings or json.dumps({"model": model_name, "mode": "mock"})

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        if self.canned_segments is not None:
            return TranscriptionResult(
                segments=self.canned_segments,
                language=self.language,
                model_name=self.model_name,
                settings=self.settings
            )
            
        # Default mock transcript: 1 segment with 3 words
        words = [
            Word(word="Jambo", start_s=0.0, end_s=0.5, confidence=0.95),
            Word(word="bwana", start_s=0.6, end_s=1.0, confidence=0.92),
            Word(word="habari", start_s=1.1, end_s=1.8, confidence=0.88),
        ]
        seg = Segment(
            start_s=0.0,
            end_s=1.8,
            text="Jambo bwana habari",
            confidence=0.92,
            words=words
        )
        return TranscriptionResult(
            segments=[seg],
            language=self.language,
            model_name=self.model_name,
            settings=self.settings
        )

class FasterWhisperTranscriber:
    """Production transcriber using faster-whisper."""
    def __init__(
        self,
        model_size_or_path: str = "small",
        language: str = "sw",
        device: str = "auto",
        compute_type: str = "auto",
        beam_size: int = 5,
        vad_filter: bool = True,
        download_root: Optional[str] = None
    ) -> None:
        self.model_size_or_path = model_size_or_path
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.download_root = download_root
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size_or_path,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.download_root
            )
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        model = self._get_model()
        segments_gen, info = model.transcribe(
            str(audio_path),
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            word_timestamps=True
        )

        results: List[Segment] = []
        for s in segments_gen:
            words: List[Word] = []
            if s.words:
                for w in s.words:
                    words.append(
                        Word(
                            word=w.word.strip(),
                            start_s=w.start,
                            end_s=w.end,
                            confidence=w.probability if w.probability is not None else 1.0
                        )
                    )
            
            # Confidence from average logprob
            conf = math.exp(s.avg_logprob) if s.avg_logprob is not None else 0.8
            conf = min(max(conf, 0.0), 1.0)
            
            results.append(
                Segment(
                    start_s=s.start,
                    end_s=s.end,
                    text=s.text.strip(),
                    confidence=conf,
                    words=words
                )
            )

        settings_str = json.dumps({
            "model": self.model_size_or_path,
            "language": self.language,
            "device": self.device,
            "compute_type": self.compute_type,
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter
        })

        return TranscriptionResult(
            segments=results,
            language=info.language or self.language,
            model_name=self.model_size_or_path,
            settings=settings_str
        )
