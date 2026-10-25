import re
import unicodedata
from typing import List

def normalize_text(text: str) -> str:
    """Normalize text according to PROJECT_SPEC rules.
    
    1. Lowercase
    2. Decompose diacritics (NFD), remove nonspacing marks, recompose to NFC
    3. Strip punctuation while preserving intra-word apostrophes (e.g. ng'ombe)
    4. Collapse whitespace
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove diacritics
    # Decompose unicode characters into base char + combining marks
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    text = unicodedata.normalize("NFC", stripped)
    
    # Standardize curly apostrophes/quotes to standard ASCII single quote
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    
    # Remove apostrophes that are not flanked on both sides by alphanumeric characters
    # Lookbehind (?<=\w)'(?=\w) preserves intra-word apostrophes; any other ' is stripped.
    # First, replace all unwanted punctuation (anything not alphanumeric, whitespace, or ')
    text = re.sub(r"[^\w\s']", " ", text)
    
    # Remove apostrophes that are at word boundaries / standalone quotes
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)
    
    # Replace underscores (since \w includes _) with space
    text = text.replace("_", " ")
    
    # 4. Collapse whitespace and strip
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str) -> List[str]:
    """Tokenize normalized text into a list of words."""
    norm = normalize_text(text)
    if not norm:
        return []
    return norm.split()
