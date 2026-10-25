import argparse
import os
import subprocess
import sys
from pathlib import Path

from kayasearch.config import load_config
from kayasearch.pipeline import run_pipeline
from kayasearch.db import connect, init_db
from kayasearch.search import search

def cmd_ingest(args):
    config = load_config(args.config)
    print(f"Starting batch ingestion from: {config.paths.audio_dir}")
    stats = run_pipeline(config)
    print("Ingestion completed:")
    print(f"  Total audio files: {stats['total']}")
    print(f"  Newly processed:   {stats['done']}")
    print(f"  Already processed: {stats['skipped']}")
    print(f"  Failed:            {stats['failed']}")

def cmd_search(args):
    config = load_config(args.config)
    conn = connect(config.paths.db_path)
    init_db(conn)
    
    results = search(
        conn,
        args.query,
        fuzzy_threshold=config.search.fuzzy_threshold,
        max_results=config.search.max_results
    )
    conn.close()
    
    print(f"Found {len(results)} matches for '{args.query}':\n")
    for idx, r in enumerate(results, 1):
        m, s = divmod(int(r.start_s), 60)
        time_str = f"{m:02d}:{s:02d}"
        print(f"[{idx}] {Path(r.recording_path).name} @ {time_str} ({r.start_s:.1f}s) | Match: {r.match_type} (Score: {r.score:.0f}%, Conf: {r.confidence:.2f})")
        print(f"    Excerpt: \"{r.text}\"")
        print("    [Machine-generated: verify against the audio]\n")

def cmd_download_models(args):
    config = load_config(args.config)
    model_name = args.model or config.transcription.model_size
    dest_dir = config.paths.models_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading Whisper model '{model_name}' to {dest_dir}...")
    
    # Temporarily allow network for explicit download-models command per spec
    old_hf = os.environ.get("HF_HUB_OFFLINE")
    old_tf = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"
    
    try:
        from faster_whisper import download_model
        downloaded_path = download_model(model_name, output_dir=str(dest_dir))
        print(f"Model downloaded successfully to: {downloaded_path}")
    except Exception as e:
        print(f"Error downloading model: {e}")
        sys.exit(1)
    finally:
        # Restore offline protection
        if old_hf is not None:
            os.environ["HF_HUB_OFFLINE"] = old_hf
        if old_tf is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = old_tf

def cmd_ui(args):
    ui_script = Path(__file__).parent / "ui" / "app.py"
    if not ui_script.exists():
        print(f"UI script not found at: {ui_script}")
        sys.exit(1)
        
    cmd = [sys.executable, "-m", "streamlit", "run", str(ui_script)]
    if args.port:
        cmd.extend(["--server.port", str(args.port)])
        
    print("Launching Kaya Search Web UI...")
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Kaya Search CLI - Oral History Search Tool")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")
    
    # Ingest
    ingest_parser = subparsers.add_parser("ingest", help="Run batch ingestion and transcription")
    ingest_parser.set_defaults(func=cmd_ingest)
    
    # Search
    search_parser = subparsers.add_parser("search", help="Search transcripts by keyword")
    search_parser.add_argument("query", help="Keyword or phrase to search for")
    search_parser.set_defaults(func=cmd_search)
    
    # Download models
    dl_parser = subparsers.add_parser("download-models", help="Download Whisper models for offline use")
    dl_parser.add_argument("--model", default=None, help="Model name (e.g. tiny, small, medium)")
    dl_parser.set_defaults(func=cmd_download_models)
    
    # UI
    ui_parser = subparsers.add_parser("ui", help="Launch the Streamlit web interface")
    ui_parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on")
    ui_parser.set_defaults(func=cmd_ui)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
