import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Any
from rapidfuzz import process, fuzz
from kayasearch.text import normalize_text, tokenize

@dataclass
class SearchResult:
    segment_id: int
    recording_id: int
    recording_path: str
    start_s: float
    end_s: float
    text: str
    confidence: float
    model: str
    match_type: str  # 'exact', 'variant', 'fuzzy'
    matched_term: str
    score: float

def get_variants_for_term(conn: sqlite3.Connection, term: str) -> List[str]:
    """Look up alternative spellings/synonyms from the variants table."""
    norm_term = normalize_text(term)
    if not norm_term:
        return []
        
    cursor = conn.execute(
        "SELECT variant FROM variants WHERE term = ? UNION SELECT term FROM variants WHERE variant = ?",
        (norm_term, norm_term)
    )
    variants = [row[0] for row in cursor.fetchall() if row[0] != norm_term]
    return variants

def add_variant(conn: sqlite3.Connection, term: str, variant: str, note: str = "") -> int:
    """Add a new researcher-specified variant/spelling."""
    norm_term = normalize_text(term)
    norm_var = normalize_text(variant)
    cursor = conn.execute(
        "INSERT INTO variants (term, variant, note) VALUES (?, ?, ?)",
        (norm_term, norm_var, note)
    )
    conn.commit()
    return cursor.lastrowid

def search_exact(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 50,
    match_type: str = "exact"
) -> List[SearchResult]:
    """Search for exact terms or phrases using SQLite FTS5."""
    tokens = tokenize(query)
    if not tokens:
        return []
        
    # Format tokens safely for FTS5: each token enclosed in double quotes
    fts_query = " ".join(f'"{t}"' for t in tokens)
    
    sql = """
        SELECT s.id, s.recording_id, r.path, s.start_s, s.end_s, s.text, s.confidence, s.model,
               bm25(segments_fts) AS rank
        FROM segments_fts f
        JOIN segments s ON s.id = f.rowid
        JOIN recordings r ON r.id = s.recording_id
        WHERE segments_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        cursor = conn.execute(sql, (fts_query, limit))
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return []
        
    results: List[SearchResult] = []
    for row in rows:
        results.append(
            SearchResult(
                segment_id=row["id"],
                recording_id=row["recording_id"],
                recording_path=row["path"],
                start_s=row["start_s"],
                end_s=row["end_s"],
                text=row["text"],
                confidence=row["confidence"],
                model=row["model"],
                match_type=match_type,
                matched_term=query,
                score=100.0 if match_type == "exact" else 95.0
            )
        )
    return results

def search_fuzzy_vocab(
    conn: sqlite3.Connection,
    query: str,
    threshold: int = 85,
    limit: int = 50
) -> List[SearchResult]:
    """Find fuzzy matches against vocab table using RapidFuzz, then retrieve segments."""
    tokens = tokenize(query)
    if not tokens:
        return []
        
    cursor = conn.execute("SELECT norm FROM vocab")
    vocab_words = [row["norm"] for row in cursor.fetchall()]
    if not vocab_words:
        return []

    fuzzy_matched_terms: Set[str] = set()
    for token in tokens:
        matches = process.extract(
            token,
            vocab_words,
            scorer=fuzz.ratio,
            score_cutoff=threshold,
            limit=5
        )
        for matched_word, score, _ in matches:
            if matched_word != token:
                fuzzy_matched_terms.add(matched_word)

    results: List[SearchResult] = []
    for term in fuzzy_matched_terms:
        matches = search_exact(conn, term, limit=limit, match_type="fuzzy")
        for m in matches:
            m.matched_term = term
            m.score = float(fuzz.ratio(query, term))
            results.append(m)
            
    return results

def search(
    conn: sqlite3.Connection,
    query: str,
    fuzzy_threshold: int = 85,
    max_results: int = 50,
    enable_fuzzy: bool = True
) -> List[SearchResult]:
    """Unified search: exact match -> variants -> fuzzy fallback."""
    norm_query = normalize_text(query)
    if not norm_query:
        return []
        
    seen_segment_ids: Set[int] = set()
    combined_results: List[SearchResult] = []
    
    # 1. Exact FTS5 Search
    exact_results = search_exact(conn, norm_query, limit=max_results, match_type="exact")
    for r in exact_results:
        if r.segment_id not in seen_segment_ids:
            seen_segment_ids.add(r.segment_id)
            combined_results.append(r)
            
    # 2. Variant Terms
    variants = get_variants_for_term(conn, norm_query)
    for var in variants:
        if len(combined_results) >= max_results:
            break
        var_results = search_exact(conn, var, limit=max_results - len(combined_results), match_type="variant")
        for r in var_results:
            if r.segment_id not in seen_segment_ids:
                seen_segment_ids.add(r.segment_id)
                combined_results.append(r)
                
    # 3. Fuzzy search if enabled and results under limit
    if enable_fuzzy and len(combined_results) < max_results:
        fuzzy_results = search_fuzzy_vocab(
            conn,
            norm_query,
            threshold=fuzzy_threshold,
            limit=max_results - len(combined_results)
        )
        # Sort fuzzy results by match score descending
        fuzzy_results.sort(key=lambda x: x.score, reverse=True)
        for r in fuzzy_results:
            if r.segment_id not in seen_segment_ids:
                seen_segment_ids.add(r.segment_id)
                combined_results.append(r)
                if len(combined_results) >= max_results:
                    break
                    
    return combined_results
