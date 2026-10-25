import json
import time
from pathlib import Path
from typing import Dict, Any, List

from kayasearch.config import Config
from kayasearch.eval.metrics import calculate_wer, calculate_cer, calculate_rtf
from kayasearch.transcribe import Transcriber, FasterWhisperTranscriber

def evaluate_transcription(
    test_samples: List[Dict[str, Any]],
    transcriber: Transcriber
) -> Dict[str, float]:
    """Evaluate transcriber on a list of samples: [{'audio_path': Path, 'reference': str}].
    
    Returns average WER, CER, and RTF.
    """
    total_wer = 0.0
    total_cer = 0.0
    total_audio_s = 0.0
    total_proc_s = 0.0
    count = len(test_samples)

    for item in test_samples:
        audio_path = Path(item["audio_path"])
        ref_text = item["reference"]
        audio_duration = item.get("duration_s", 1.0)
        
        t0 = time.time()
        res = transcriber.transcribe(audio_path)
        t1 = time.time()

        hyp_text = " ".join(seg.text for seg in res.segments)
        
        total_wer += calculate_wer(ref_text, hyp_text)
        total_cer += calculate_cer(ref_text, hyp_text)
        total_audio_s += audio_duration
        total_proc_s += (t1 - t0)

    avg_wer = total_wer / count if count > 0 else 0.0
    avg_cer = total_cer / count if count > 0 else 0.0
    rtf = calculate_rtf(total_audio_s, total_proc_s)

    return {
        "samples_evaluated": count,
        "avg_wer": round(avg_wer, 4),
        "avg_cer": round(avg_cer, 4),
        "rtf": round(rtf, 4),
    }
