import os
import pytest
from pathlib import Path
from kayasearch.config import load_config

def test_load_valid_config(tmp_path):
    config_yaml = """
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
  model_path: null
search:
  fuzzy_threshold: 85
  max_results: 50
privacy:
  offline: true
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_yaml)
    
    config = load_config("config.yaml", project_root=tmp_path)
    assert config.paths.audio_dir == tmp_path / "data/audio"
    assert config.transcription.model_size == "small"
    assert config.privacy.offline is True
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"

def test_load_invalid_config(tmp_path):
    config_yaml = """
paths:
  audio_dir: "data/audio"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_yaml)
    
    with pytest.raises(ValueError, match="Missing required config key"):
        load_config("config.yaml", project_root=tmp_path)

def test_missing_config():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")
