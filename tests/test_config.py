import os
import pytest
from pathlib import Path
from kayasearch.config import find_project_root, load_config

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


def test_find_project_root_prefers_cwd_over_site_packages_hint(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("paths: {}\n")
    fake_site_pkg = tmp_path / ".venv" / "lib" / "python3.14" / "site-packages" / "kayasearch" / "seed_demo.py"
    fake_site_pkg.parent.mkdir(parents=True)
    fake_site_pkg.write_text("# stub\n")

    monkeypatch.chdir(tmp_path)
    resolved = find_project_root(hint=fake_site_pkg)
    assert resolved == tmp_path


def test_find_project_root_walks_up_from_source_hint(tmp_path, monkeypatch):
    project = tmp_path / "repo"
    app_file = project / "src" / "kayasearch" / "ui" / "app.py"
    app_file.parent.mkdir(parents=True)
    app_file.write_text("# app\n")
    (project / "config.yaml").write_text("paths: {}\n")

    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    resolved = find_project_root(hint=app_file)
    assert resolved == project
