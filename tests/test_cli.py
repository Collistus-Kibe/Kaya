import sys
import pytest
from kayasearch.cli import main
from kayasearch.config import load_config
from kayasearch.db import connect, init_db, insert_recording, insert_segment

def test_cli_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["kayasearch", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Kaya Search CLI" in captured.out

def test_cli_search(monkeypatch, capsys, tmp_path):
    # Setup test config and database
    db_file = tmp_path / "test.db"
    conn = connect(db_file)
    init_db(conn)
    rec_id = insert_recording(conn, "sample.wav", 10.0, "done")
    insert_segment(conn, rec_id, 0.0, 5.0, "wazee wa kaya", 0.95, "small", "{}")
    conn.commit()
    conn.close()

    posix_tmp = tmp_path.as_posix()
    posix_db = db_file.as_posix()
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(f"""
paths:
  audio_dir: "{posix_tmp}"
  db_path: "{posix_db}"
  work_dir: "{posix_tmp}"
  models_dir: "{posix_tmp}"
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
""")

    monkeypatch.setattr(sys, "argv", ["kayasearch", "--config", str(cfg_file), "search", "kaya"])
    main()
    captured = capsys.readouterr()
    assert "Found 1 matches" in captured.out
    assert "wazee wa kaya" in captured.out
    assert "Machine-generated: verify against the audio" in captured.out
