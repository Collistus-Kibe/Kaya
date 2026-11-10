import asyncio
import math
import struct
import wave
from pathlib import Path
from typing import Optional

from kayasearch.audio import get_audio_duration
from kayasearch.config import find_project_root, load_config
from kayasearch.db import (
    connect,
    init_db,
    insert_recording,
    update_recording_status,
    insert_segment,
    add_to_vocab,
)
from kayasearch.text import tokenize
from kayasearch.search import add_variant

DEMO_RECORDINGS = [
    {
        "stem": "kaya_kinondo_elder_malaria_cure",
        "voice": "sw-KE-RafikiNeural",
        "duration_s": 26.0,
        "segments": [
            (0.0, 6.8, "Katika msitu wa Kaya Kinondo kule Kwale, wazee wetu wa kale walikuwa na siri kubwa ya tiba asilia.", 0.94),
            (7.2, 12.6, "Mtu akipatwa na homa kali au ugonjwa wa malaria, hatukukimbia hospitalini mbali.", 0.92),
            (13.4, 18.2, "Tulichukua mizizi ya mti wa mwarubaini pamoja na magome ya mti wa muvumo.", 0.91),
            (19.0, 25.0, "Ukichemsha mizizi hii na kunywa asubuhi na jioni, malaria inakwisha kabisa ndani ya siku tatu.", 0.95),
        ],
    },
    {
        "stem": "kaya_waa_medicinal_roots_and_herbs",
        "voice": "sw-KE-RafikiNeural",
        "duration_s": 21.4,
        "segments": [
            (0.0, 4.1, "Hapa Kaya Waa, wazee wa tiba wanajua kila mti na dawa yake.", 0.93),
            (4.8, 9.5, "Miti shamba na mizizi ya kiasili inatibu magonjwa mengi ya pwani.", 0.90),
            (10.0, 13.8, "Dawa ya malaria hupatikana kwenye mizizi michungu ya mwarubaini.", 0.92),
            (14.5, 20.6, "Pia kwa homa ya matumbo na maumivu ya viungo, majani ya mpera na mizizi ya mdimu huchemshwa pamoja.", 0.89),
        ],
    },
    {
        "stem": "kaya_tiwi_traditional_healing_secrets",
        "voice": "sw-KE-ZuriNeural",
        "duration_s": 19.3,
        "segments": [
            (0.0, 5.7, "Mimi nimejifunza ukunga na tiba ya kiasili kutoka kwa nyanya yangu hapa Tiwi Kwale.", 0.94),
            (6.5, 8.9, "Maarifa haya ya Kaya ni amana yetu.", 0.91),
            (9.6, 18.6, "Tunawafundisha vijana jinsi ya kutunza misitu ya Kaya kwa sababu miti hii inatupa dawa asilia za kutibu malaria, kikohozi na uzazi.", 0.93),
        ],
    },
]


def create_tone_wav(path: Path, duration_s: float = 12.0, freq: float = 220.0, sample_rate: int = 16000) -> Path:
    """Generate offline fallback WAV file when no speech audio exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_data = bytearray()
        for i in range(num_samples):
            val = int(4000.0 * math.sin(2.0 * math.pi * freq * i / sample_rate) * math.exp(-0.0001 * (i % 8000)))
            raw_data.extend(struct.pack("<h", val))
        wf.writeframes(raw_data)
    return path


async def _synthesize_edge_tts(text: str, voice: str, dest: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def _prepare_audio_file(audio_dir: Path, entry: dict, allow_tts: bool) -> tuple[Path, float]:
    mp3_path = audio_dir / f"{entry['stem']}.mp3"
    wav_path = audio_dir / f"{entry['stem']}.wav"

    if mp3_path.exists():
        return mp3_path, get_audio_duration(mp3_path)

    if allow_tts:
        try:
            full_text = " ".join(seg[2] for seg in entry["segments"])
            asyncio.run(_synthesize_edge_tts(full_text, entry["voice"], mp3_path))
            if mp3_path.exists() and mp3_path.stat().st_size > 0:
                return mp3_path, get_audio_duration(mp3_path)
        except Exception:
            if mp3_path.exists():
                mp3_path.unlink(missing_ok=True)

    if not wav_path.exists():
        create_tone_wav(wav_path, duration_s=entry["duration_s"], freq=260.0)
    return wav_path, entry["duration_s"]


def seed_sample_archive(project_root: Optional[Path] = None, allow_tts: bool = False) -> None:
    """Seed Kwale Kaya medicinal roots demo archive if not already populated."""
    if project_root is None:
        project_root = find_project_root(hint=Path(__file__).resolve())
    config = load_config("config.yaml", project_root=project_root)

    audio_dir = config.paths.audio_dir
    db_path = config.paths.db_path

    audio_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    init_db(conn)

    for entry in DEMO_RECORDINGS:
        audio_path, duration_s = _prepare_audio_file(audio_dir, entry, allow_tts=allow_tts)
        existing = conn.execute("SELECT id FROM recordings WHERE path = ?", (str(audio_path),)).fetchone()
        if existing:
            continue

        rec_id = insert_recording(conn, str(audio_path), duration_s, status="done")
        update_recording_status(conn, rec_id, "done")

        for start_s, end_s, text, conf in entry["segments"]:
            insert_segment(
                conn, rec_id, start_s, end_s,
                text, conf, "whisper-tiny-sw-demo", "{}"
            )
            for w in tokenize(text):
                add_to_vocab(conn, w)

    # Seed medical and coastal dialect variants idempotently
    default_variants = [
        ("malaria", "homa ya malaria", "Swahili term for malaria fever"),
        ("malaria", "mwarubaini", "Traditional neem tree used for malaria"),
        ("dawa", "miti shamba", "Traditional herbal medicine"),
        ("mizizi", "mizizi ya dawa", "Medicinal roots"),
        ("mzee", "muzee", "Coastal dialect spelling for elder"),
        ("ng'ombe", "ngombe", "Coastal spelling without apostrophe"),
    ]
    for term, variant, note in default_variants:
        exists = conn.execute(
            "SELECT 1 FROM variants WHERE term = ? AND variant = ?",
            (term, variant)
        ).fetchone()
        if not exists:
            add_variant(conn, term, variant, note)

    conn.commit()
    conn.close()
    print("Sample archive and database seeded successfully.")


if __name__ == "__main__":
    seed_sample_archive(allow_tts=True)
