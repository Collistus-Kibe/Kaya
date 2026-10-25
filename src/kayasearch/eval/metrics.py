from typing import List, Dict, Any
import jiwer
from kayasearch.text import normalize_text

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate (WER) after standard text normalization."""
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)
    if not ref_norm and not hyp_norm:
        return 0.0
    if not ref_norm:
        return 1.0
    return float(jiwer.wer(ref_norm, hyp_norm))

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate (CER) after standard text normalization."""
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)
    if not ref_norm and not hyp_norm:
        return 0.0
    if not ref_norm:
        return 1.0
    return float(jiwer.cer(ref_norm, hyp_norm))

def calculate_rtf(audio_duration_s: float, processing_time_s: float) -> float:
    """Calculate Real-Time Factor (RTF = processing_time / audio_duration).
    
    An RTF < 1.0 indicates faster-than-realtime transcription.
    """
    if audio_duration_s <= 0:
        return 0.0
    return float(processing_time_s) / float(audio_duration_s)

def calculate_retrieval_metrics(
    ground_truth_ids: List[int],
    retrieved_ids: List[int],
    k: int = 5
) -> Dict[str, float]:
    """Calculate precision@k, recall@k, and Mean Reciprocal Rank (MRR)."""
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0}
        
    top_k = retrieved_ids[:k]
    hits = [seg_id for seg_id in top_k if seg_id in gt_set]
    
    precision = len(hits) / float(k) if k > 0 else 0.0
    recall = len(hits) / float(len(gt_set))
    
    mrr = 0.0
    for rank, seg_id in enumerate(retrieved_ids, start=1):
        if seg_id in gt_set:
            mrr = 1.0 / rank
            break
            
    return {
        "precision_at_k": precision,
        "recall_at_k": recall,
        "mrr": mrr
    }
