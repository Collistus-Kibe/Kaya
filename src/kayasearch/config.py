import os
import yaml
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

@dataclass
class PathsConfig:
    audio_dir: Path
    db_path: Path
    work_dir: Path
    models_dir: Path

@dataclass
class TranscriptionConfig:
    model_size: str
    language: str
    device: str
    compute_type: str
    beam_size: int
    vad_filter: bool
    model_path: Optional[str]

@dataclass
class SearchConfig:
    fuzzy_threshold: int
    max_results: int

@dataclass
class PrivacyConfig:
    offline: bool

@dataclass
class Config:
    paths: PathsConfig
    transcription: TranscriptionConfig
    search: SearchConfig
    privacy: PrivacyConfig

def find_project_root(config_name: str = "config.yaml", hint: Optional[Path] = None) -> Path:
    """Locate the project root containing config_name across CWD and ancestor directories."""
    env_root = os.environ.get("KAYA_PROJECT_ROOT")
    if env_root:
        candidate = Path(env_root)
        if (candidate / config_name).exists():
            return candidate

    cwd = Path.cwd()
    if (cwd / config_name).exists():
        return cwd
    if (cwd / "kaya-search" / config_name).exists():
        return cwd / "kaya-search"

    for base in ([hint] if hint is not None else []) + [Path(__file__).resolve()]:
        for parent in [base] + list(base.parents):
            if (parent / config_name).exists():
                return parent

    return cwd


def load_config(config_path: str = "config.yaml", project_root: Optional[Path] = None) -> Config:
    if project_root is None:
        project_root = Path.cwd()
        
    config_file = project_root / config_path
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
        
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        
    if not isinstance(data, dict):
        raise ValueError("Invalid config format. Expected a YAML dictionary.")
        
    try:
        paths = PathsConfig(
            audio_dir=project_root / data["paths"]["audio_dir"],
            db_path=project_root / data["paths"]["db_path"],
            work_dir=project_root / data["paths"]["work_dir"],
            models_dir=project_root / data["paths"]["models_dir"]
        )
        
        transcription = TranscriptionConfig(
            model_size=data["transcription"]["model_size"],
            language=data["transcription"]["language"],
            device=data["transcription"]["device"],
            compute_type=data["transcription"]["compute_type"],
            beam_size=data["transcription"]["beam_size"],
            vad_filter=data["transcription"]["vad_filter"],
            model_path=data["transcription"].get("model_path")
        )
        
        search = SearchConfig(
            fuzzy_threshold=data["search"]["fuzzy_threshold"],
            max_results=data["search"]["max_results"]
        )
        
        privacy = PrivacyConfig(
            offline=data["privacy"]["offline"]
        )
        
        config = Config(paths=paths, transcription=transcription, search=search, privacy=privacy)
    except KeyError as e:
        raise ValueError(f"Missing required config key: {e}")
        
    if config.privacy.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        
    return config
