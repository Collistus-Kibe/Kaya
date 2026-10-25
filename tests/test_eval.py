import pytest
from kayasearch.eval.metrics import calculate_wer, calculate_cer, calculate_rtf, calculate_retrieval_metrics
from kayasearch.eval.run_eval import evaluate_transcription
from kayasearch.transcribe import FakeTranscriber, Segment

def test_wer_cer_metrics():
    ref = "Wazee wa Kaya wanakutana asubuhi"
    hyp = "Wazee wa Kaya wanakutana jioni"
    
    wer = calculate_wer(ref, hyp)
    assert 0.0 < wer < 1.0
    
    cer = calculate_cer(ref, hyp)
    assert 0.0 < cer < 1.0

def test_identical_text_metrics():
    text = "Habari ya asubuhi rafiki yangu"
    assert calculate_wer(text, text) == 0.0
    assert calculate_cer(text, text) == 0.0

def test_rtf_metric():
    # 10s audio processed in 2s -> RTF 0.2
    assert calculate_rtf(10.0, 2.0) == 0.2
    assert calculate_rtf(0.0, 2.0) == 0.0

def test_retrieval_metrics():
    gt = [1, 2, 3]
    retrieved = [2, 5, 1, 9, 8]
    metrics = calculate_retrieval_metrics(gt, retrieved, k=3)
    # top 3 are [2, 5, 1] -> hits are 2 and 1 (2 hits)
    assert pytest.approx(metrics["precision_at_k"], 1e-2) == 2.0 / 3.0
    assert pytest.approx(metrics["recall_at_k"], 1e-2) == 2.0 / 3.0
    assert metrics["mrr"] == 1.0  # first hit is rank 1 (id 2)

def test_evaluate_transcription(tmp_path):
    dummy_wav = tmp_path / "dummy.wav"
    dummy_wav.touch()

    fake = FakeTranscriber(
        canned_segments=[Segment(start_s=0.0, end_s=1.0, text="jambo bwana", confidence=0.9)]
    )
    samples = [{"audio_path": dummy_wav, "reference": "jambo bwana", "duration_s": 1.0}]
    results = evaluate_transcription(samples, fake)
    
    assert results["samples_evaluated"] == 1
    assert results["avg_wer"] == 0.0
    assert results["avg_cer"] == 0.0
