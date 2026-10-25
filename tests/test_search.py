import pytest
from kayasearch.db import connect, init_db, insert_recording, insert_segment, add_to_vocab
from kayasearch.search import search, add_variant, get_variants_for_term

@pytest.fixture
def populated_db(tmp_path):
    conn = connect(tmp_path / "search_test.db")
    init_db(conn)

    rec1 = insert_recording(conn, "data/audio/interview1.wav", 120.0, "done")
    rec2 = insert_recording(conn, "data/audio/interview2.wav", 80.0, "done")

    # Segment 1
    insert_segment(conn, rec1, 0.0, 5.0, "wazee wa kaya wanakutana asubuhi", 0.95, "small", "{}")
    for w in ["wazee", "wa", "kaya", "wanakutana", "asubuhi"]:
        add_to_vocab(conn, w)

    # Segment 2
    insert_segment(conn, rec1, 5.5, 10.0, "ng'ombe wanakula majani shambani", 0.91, "small", "{}")
    for w in ["ng'ombe", "wanakula", "majani", "shambani"]:
        add_to_vocab(conn, w)

    # Segment 3
    insert_segment(conn, rec2, 2.0, 7.0, "mila na desturi za pwani", 0.88, "small", "{}")
    for w in ["mila", "na", "desturi", "za", "pwani"]:
        add_to_vocab(conn, w)

    conn.commit()
    yield conn
    conn.close()

def test_search_exact(populated_db):
    results = search(populated_db, "kaya")
    assert len(results) == 1
    assert results[0].text == "wazee wa kaya wanakutana asubuhi"
    assert results[0].match_type == "exact"
    assert results[0].recording_path == "data/audio/interview1.wav"

def test_search_intra_word_apostrophe(populated_db):
    results = search(populated_db, "ng'ombe")
    assert len(results) == 1
    assert "ng'ombe" in results[0].text
    assert results[0].match_type == "exact"

def test_search_variant(populated_db):
    add_variant(populated_db, "ngombe", "ng'ombe", note="alternate spelling")
    # Search for "ngombe" should match "ng'ombe" via variant expansion
    results = search(populated_db, "ngombe")
    assert len(results) >= 1
    assert any("ng'ombe" in r.text for r in results)

def test_search_fuzzy(populated_db):
    # Search for "desturii" (typo) should fuzzy match "desturi"
    results = search(populated_db, "desturii", fuzzy_threshold=80)
    assert len(results) >= 1
    assert any("desturi" in r.text for r in results)
    fuzzy_matches = [r for r in results if r.match_type == "fuzzy"]
    assert len(fuzzy_matches) > 0

def test_search_empty_and_no_match(populated_db):
    assert search(populated_db, "") == []
    assert search(populated_db, "xyznonexistentword") == []
