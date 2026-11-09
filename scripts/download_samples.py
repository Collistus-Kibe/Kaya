import json
import logging
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_samples")

def download_fleurs_swahili_samples(target_dir: Path, num_samples: int = 10) -> List[Path]:
    """Download authentic Swahili speech samples from Google FLEURS dataset via Hugging Face API."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    api_url = f"https://datasets-server.huggingface.co/rows?dataset=google/fleurs&config=sw_ke&split=train&offset=0&length={num_samples}"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "KayaSearchOralHistory/1.0"}
    )
    
    logger.info(f"Connecting to Hugging Face Datasets API for Swahili (FLEURS)...")
    downloaded_files: List[Path] = []
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        rows = data.get("rows", [])
        logger.info(f"Retrieved metadata for {len(rows)} Swahili speech samples.")
        
        for i, r in enumerate(rows):
            row_data = r.get("row", {})
            audio_info = row_data.get("audio", {})
            transcription = row_data.get("transcription", "")
            
            # Extract streaming / download URL
            src_url = None
            if isinstance(audio_info, dict):
                src_url = audio_info.get("src")
            elif isinstance(audio_info, list) and len(audio_info) > 0:
                src_url = audio_info[0].get("src")
                
            if not src_url:
                continue
                
            # Clean file name
            filename = f"fleurs_swahili_{i+1:02d}.wav"
            dest_path = target_dir / filename
            
            logger.info(f"Downloading sample {i+1}/{len(rows)}: {filename}...")
            
            # Download audio file
            audio_req = urllib.request.Request(src_url, headers={"User-Agent": "KayaSearchOralHistory/1.0"})
            with urllib.request.urlopen(audio_req, timeout=30) as a_resp:
                dest_path.write_bytes(a_resp.read())
                
            downloaded_files.append(dest_path)
            logger.info(f"Saved: {filename} ({dest_path.stat().st_size // 1024} KB)")
            
    return downloaded_files

def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    target_audio_dir = base_dir / "data" / "audio"
    
    logger.info(f"Target audio directory: {target_audio_dir}")
    files = download_fleurs_swahili_samples(target_audio_dir, num_samples=10)
    logger.info(f"Successfully downloaded {len(files)} audio recordings into {target_audio_dir}")
    print("\nNext step: Run 'kayasearch ingest' or click 'Run / Resume Batch Ingestion' in the Web UI!")

if __name__ == "__main__":
    main()

