import pytest
from kayasearch.text import normalize_text, tokenize

def test_normalize_basic():
    assert normalize_text("Habari za Asubuhi") == "habari za asubuhi"

def test_normalize_diacritics():
    assert normalize_text("Café naïve") == "cafe naive"

def test_normalize_intra_word_apostrophe():
    # Intra-word apostrophe must be kept (e.g., Swahili ng'ombe)
    assert normalize_text("Ng'ombe wanakula") == "ng'ombe wanakula"
    # Curly apostrophe should also be normalized and preserved if intra-word
    assert normalize_text("Ng’ombe") == "ng'ombe"

def test_normalize_quotes_and_punctuation():
    # Quotes around words should be removed, not kept
    assert normalize_text("'habari' na \"rafiki\"!") == "habari na rafiki"
    assert normalize_text("Jambo, habari gani? Nzuri sana...") == "jambo habari gani nzuri sana"

def test_normalize_whitespace():
    assert normalize_text("   habari \t\n  za jioni   ") == "habari za jioni"
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""

def test_tokenize():
    assert tokenize("Ng'ombe 10 wako shambani!") == ["ng'ombe", "10", "wako", "shambani"]
    assert tokenize("") == []
