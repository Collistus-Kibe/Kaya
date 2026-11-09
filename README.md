# 🌿 Kaya Search

> **Privacy-first offline audio search engine for indexing indigenous Kaya medical knowledge & Swahili elder oral histories.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local Only](https://img.shields.io/badge/Privacy-100%25%20Offline-emerald.svg)](#privacy--ethics-rules)
[![Tests: 37 Passed](https://img.shields.io/badge/tests-37%20passed-brightgreen.svg)](#testing)

---

## 🎯 Case Study & Mission

> *"Fatuma is a PhD student in Kwale researching indigenous Kaya medical knowledge. She has 300 hours of audio recordings—interviews with village elders who are the last keepers of knowledge about rare medicinal roots. To write her thesis, she has to manually listen to days of audio just to find a specific mention of a cure for 'Malaria.' With elders passing away and university deadlines approaching, she needs an automated indexing tool that works like Google search for audio recordings—tuned for local coastal dialects and running 100% offline to protect sacred community knowledge."*

**Kaya Search** solves this challenge by combining local speech-to-text models (`faster-whisper`), SQLite FTS5 full-text search, and dialect-aware fuzzy matching (`rapidfuzz`) to index oral history archives into sub-second, searchable audio transcripts with exact timestamp playback.

> ⚠️ **Core Philosophy**: Machine transcripts are finding aids pointing to specific places in the audio recordings. They are never presented as authoritative text. The researcher always listens to verify.

---

## 🛡️ Privacy & Ethics Rules (Non-Negotiable)

* **100% Local Execution**: The recordings contain sacred community knowledge and some speakers have passed away. Everything runs locally on the researcher's machine.
* **Zero Runtime Network Calls**: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are enforced by default. The only permitted network usage is downloading model files via an explicit `download-models` command.
* **No Transcript Logging**: Raw transcript text is never logged to disk or sent across networks. Only file names, durations, counts, and error codes are logged.
* **Separation of Machine & Human Knowledge**: Machine transcripts are never overwritten. Human corrections live in a separate `corrections` review table.
* **Clear Labeling**: Every transcript displayed in the UI carries the visible notice:  
  `⚠️ Machine-generated: verify against the audio`

---

## ✨ Features

- **High-Performance Audio Pipeline**: Discovers and converts `.mp3`, `.wav`, `.m4a`, and `.flac` into 16 kHz mono WAV via PyAV and FFmpeg.
- **Whisper Transcription Engine**: Powered by `faster-whisper` (CTranslate2) with language support tailored for Swahili (`sw`) and word-level timestamps.
- **SQLite FTS5 Full-Text Indexing**: Sub-second full-text retrieval with BM25 ranking across hundreds of hours of transcripts.
- **Dialect & Variant Search**:
  - Exact phrase and token search.
  - Researcher-editable `variants` table for coastal dialect shifts (e.g. *ng'ombe* ↔ *ngombe*, *mzee* ↔ *muzee*).
  - RapidFuzz vocabulary matching with adjustable sensitivity.
- **Interactive Streamlit Web UI**:
  - Search suggestion chips (`#kaya`, `#wazee`, `#ng'ombe`, `#mila`, `#pwani`).
  - Matched keyword highlighting within excerpts.
  - In-browser playback with timestamp jumping.
  - One-click **✂️ Audio Clip Extraction** to download focused segments.
  - Human verification & corrections drawer with reviewer attribution.
  - One-click CSV export of search results.
- **Batch Processing with Resume**: Processes audio directories in the background, automatically skipping previously completed files and isolating corrupt files without crashing.
- **Evaluation Framework**: Built-in metrics for Word Error Rate (WER), Character Error Rate (CER), Real-Time Factor (RTF), and retrieval precision/recall.

---

## 🏗️ Repository Architecture

```
kaya-search/
├── PROJECT_SPEC.md          # Technical specifications and working rules
├── README.md                # Project documentation
├── pyproject.toml           # Package configuration & dependencies
├── config.yaml              # Local paths and engine configuration
├── .gitignore               # Ensures data/, *.db, models/ are never committed
├── src/kayasearch/
│   ├── __init__.py
│   ├── config.py            # Dataclasses & offline environment configuration
│   ├── db.py                # SQLite schema, FTS5 triggers & helpers
│   ├── audio.py             # Audio discovery, conversion & clipping
│   ├── transcribe.py        # Transcriber protocol, FasterWhisper & FakeTranscriber
│   ├── search.py            # FTS5 search, variant expansion & fuzzy matching
│   ├── pipeline.py          # Batch ingestion runner with resume support
│   ├── text.py              # Single source of truth for text normalization
│   ├── cli.py               # Command-line interface
│   ├── eval/                # WER, CER, RTF, and retrieval metrics
│   └── ui/
│       └── app.py           # Streamlit web application
└── tests/                   # 37 offline unit tests (zero GPU/network required)
```

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/Collistus-Kibe/Kaya.git
cd Kaya

# Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Configuration (`config.yaml`)

Edit `config.yaml` to configure local paths:

```yaml
paths:
  audio_dir: "data/audio"
  db_path: "data/db/kaya.db"
  work_dir: "data/work"
  models_dir: "models"

transcription:
  model_size: "small"
  language: "sw"
  device: "auto"
  compute_type: "auto"
  beam_size: 5
  vad_filter: true

search:
  fuzzy_threshold: 85
  max_results: 50

privacy:
  offline: true
```

### 3. Download Model (One-Time Setup)

Download the Whisper model for offline use:

```bash
kayasearch download-models --model small
```

### 4. Running the Web Application

Launch the research interface:

```bash
kayasearch ui
# Or directly via streamlit:
streamlit run src/kayasearch/ui/app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 💻 CLI Commands

| Command | Description |
| :--- | :--- |
| `kayasearch search "<keyword>"` | Search the transcript index directly from terminal |
| `kayasearch ingest` | Run batch ingestion and transcription over `audio_dir` |
| `kayasearch download-models` | Download Whisper models for offline execution |
| `kayasearch ui` | Launch the Streamlit web research interface |

---

## 🧪 Testing

Run the test suite offline (runs entirely without GPU, network, or real audio files):

```bash
pytest
```

**Result**: 37 passed in < 3s.

---

## 📜 License

Licensed under the [MIT License](LICENSE).
