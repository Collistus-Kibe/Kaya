# PROJECT_SPEC.md: Kaya Search

## Purpose
A local tool that lets a researcher search a large collection of oral-history audio recordings
(about 300 hours of Swahili and coastal-dialect speech from elders) by keyword. The tool transcribes
audio, indexes the transcripts, and returns for each match the recording, the timestamp, a text
excerpt, and a button to play the audio from that point.

The transcripts are machine output and contain errors. They are finding aids that point to places in
the audio. They are never presented as authoritative text. The researcher verifies by listening.

## Users
One researcher who is not a developer. After one short training session she must be able to
run a search and play a result. Everything she touches must be a web page with plain-language labels.

## Privacy and ethics rules (non-negotiable)
- The recordings contain community knowledge and some speakers have died. Everything runs locally.
- No audio or transcript text is ever sent to any external service at runtime.
  The only permitted network use is downloading model files, and only when the user runs an explicit
  `download-models` command. After that the tool must work fully offline.
- Provide a config flag `offline: true` (the default) that sets `HF_HUB_OFFLINE=1` and
  `TRANSFORMERS_OFFLINE=1` and refuses any code path that would use the network.
- Never log transcript text. Log file names, counts, durations and errors only.
- Transcripts shown in the UI carry a visible label: "Machine-generated: verify against the audio".
- The tool gives no medical advice and makes no claims about what the content means.

## Tech stack
- Python 3.10+, project managed with `pyproject.toml`, tests with `pytest`.
- Transcription: `faster-whisper` (Whisper models, CTranslate2), language `sw` (Swahili) by default.
- Audio: `ffmpeg` (command line) for conversion and clipping; `silero-vad` or the VAD built into
  faster-whisper for speech detection.
- Storage: SQLite (standard library `sqlite3`) with FTS5.
- Fuzzy matching: `rapidfuzz`.
- UI: `streamlit`.
- Metrics: `jiwer`.
- Training (optional, separate): `transformers`, `peft`, `datasets`, `accelerate`.

## Repository layout
```
kaya-search/
  PROJECT_SPEC.md
  README.md
  pyproject.toml
  config.yaml
  .gitignore                  # must ignore data/, *.db, models/
  src/kayasearch/
    __init__.py
    config.py                 # load and validate config.yaml
    db.py                     # schema, connection, helpers
    audio.py                  # discovery, conversion, clipping
    transcribe.py             # Transcriber protocol, FasterWhisperTranscriber, FakeTranscriber
    pipeline.py               # batch run with resume
    text.py                   # normalisation shared by indexing and search
    search.py                 # exact and fuzzy search, variants
    cli.py                    # command line entry point
    ui/app.py                 # Streamlit app
    eval/metrics.py           # WER, CER, retrieval, RTF
    eval/run_eval.py
  training/
    finetune_whisper_lora.py
    convert_to_ct2.md
  tests/
  data/                       # git-ignored
    audio/                    # the researcher's recordings (never committed)
    db/kaya.db
    eval/
```

## Data model (SQLite)
```
recordings(id INTEGER PK, path TEXT UNIQUE, duration_s REAL, status TEXT,   -- pending|done|failed
           error TEXT, added_at TEXT, processed_at TEXT)
segments(id INTEGER PK, recording_id INT, start_s REAL, end_s REAL, text TEXT,
         confidence REAL, model TEXT, settings TEXT, created_at TEXT)
words(id INTEGER PK, segment_id INT, word TEXT, norm TEXT, start_s REAL, end_s REAL, confidence REAL)
vocab(norm TEXT PRIMARY KEY, freq INT)                      -- distinct normalised words, for fuzzy search
segments_fts  -- FTS5 virtual table over segments.text (external content or content-linked),
                 tokenizer: unicode61 remove_diacritics 2
variants(id INTEGER PK, term TEXT, variant TEXT, note TEXT) -- researcher-editable spellings/synonyms
corrections(id INTEGER PK, segment_id INT, corrected_text TEXT, reviewer TEXT, created_at TEXT)
```
Machine output in `segments` is never overwritten. Human corrections live only in `corrections`.

## Text normalisation (single source of truth in `text.py`)
Lower-case, Unicode NFC, remove diacritics, strip punctuation, collapse whitespace, keep
apostrophes inside words. The same function is used when indexing, searching and evaluating.

## Functional requirements
FR01 accept mp3/wav/m4a/flac from a folder. FR02 convert to 16 kHz mono wav and detect speech.
FR03 transcribe with timestamps and a confidence value. FR04 choose between models and record which
one made each segment. FR05 index into SQLite FTS5. FR06 exact and fuzzy search with a variants list.
FR07 show file, timestamp, excerpt, confidence. FR08 play audio from the timestamp. FR09 batch
processing with resume. FR10 corrections stored separately. FR11 export to CSV.

## Non-functional requirements
Search under 5 s across the full collection. Index and transcripts under 5 GB for 300 hours.
A batch run must not crash on a bad file: log it, mark it failed, continue.
Every transcript records model, settings and date.

## Working rules for the coding agent
1. Read this file before doing anything. Implement only the module named in the current prompt.
2. Do not add dependencies that are not listed here without saying why.
3. Every module must have pytest tests that run with no GPU, no network and no real audio.
   Use `FakeTranscriber` and small synthetic fixtures.
4. Type-hint public functions and write short docstrings. Keep functions small.
5. Never hard-code paths. Read them from `config.yaml`.
6. Never log transcript text. Never add any network call outside `download-models`.
7. At the end of each task, run the tests and report the real output. If something fails, say so.
   Do not claim success without running the code. Do not silently skip or delete failing tests.
8. When something in the spec is ambiguous or wrong, stop and ask. Do not guess.
