import io
import csv
import html
import re
from pathlib import Path
from typing import List, Set
import streamlit as st

from kayasearch.config import load_config
from kayasearch.db import connect, init_db
from kayasearch.search import search, add_variant, SearchResult
from kayasearch.pipeline import run_pipeline
from kayasearch.audio import clip_audio

st.set_page_config(
    page_title="Kaya Search — Oral History Audio Archive",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State
if "search_query" not in st.session_state:
    st.session_state["search_query"] = "kaya"
if "reviewer_name" not in st.session_state:
    st.session_state["reviewer_name"] = "Researcher"

# Load configuration and DB connection
def get_config_and_db():
    config = load_config()
    conn = connect(config.paths.db_path, check_same_thread=False)
    init_db(conn)
    return config, conn

config, conn = get_config_and_db()

# Premium Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #091326 0%, #172554 45%, #1e293b 100%);
        color: #ffffff;
        padding: 32px 36px;
        border-radius: 18px;
        margin-bottom: 28px;
        box-shadow: 0 12px 30px -8px rgba(15, 23, 42, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    .hero-badge {
        display: inline-block;
        padding: 5px 14px;
        background: rgba(56, 189, 248, 0.18);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 20px;
        color: #7dd3fc;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 8px 0;
        background: linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        font-size: 1.0rem;
        color: #94a3b8;
        margin: 0;
        max-width: 780px;
        line-height: 1.5;
    }
    .hero-pills {
        margin-top: 18px;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }
    .hero-pill {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        color: #e2e8f0;
    }

    /* Result Cards */
    .result-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 22px;
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px -4px rgba(15, 23, 42, 0.09);
        border-color: #cbd5e1;
    }
    .card-header-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
    }
    .recording-name {
        font-family: 'Outfit', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .timestamp-badge {
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .kw-highlight {
        background: linear-gradient(120deg, #fef08a 0%, #fde047 100%);
        color: #854d0e;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 700;
    }
    .machine-notice {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #fffbeb;
        color: #b45309;
        border: 1px solid #fde68a;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 10px 0;
    }
    .verified-banner {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 10px 0;
    }
    .excerpt-box {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 1.02rem;
        color: #1e293b;
        margin: 12px 0 16px 0;
        line-height: 1.6;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.78rem;
        font-weight: 700;
        border-radius: 14px;
        letter-spacing: 0.02em;
    }
    .badge-exact { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .badge-variant { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    .badge-fuzzy { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .badge-conf { background: #faf5ff; color: #6b21a8; border: 1px solid #f3e8ff; }

    /* Suggestion Chips */
    .chip-container {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 6px;
        margin-bottom: 18px;
        flex-wrap: wrap;
    }
    .chip-label {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 600;
    }
    
    /* Stats Metric Cards */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

def highlight_matches(text: str, query: str, matched_term: str = "") -> str:
    """Highlight matched keywords in excerpt safely."""
    safe_text = html.escape(text)
    terms: Set[str] = set()
    for term in [query, matched_term]:
        if term and term.strip():
            terms.add(term.strip())
            for t in term.strip().split():
                if len(t) >= 3:
                    terms.add(t)

    for t in sorted(terms, key=len, reverse=True):
        pattern = re.compile(rf"(?i)\b({re.escape(t)})\b")
        safe_text = pattern.sub(r'<mark class="kw-highlight">\1</mark>', safe_text)
    return safe_text

# Header Banner
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">Oral History & Coastal Dialects Archive</div>
    <h1 class="hero-title">Kaya Audio Search</h1>
    <p class="hero-sub">
        Explore and verify ~300 hours of elder speech recordings. Fast local keyword search across Swahili and coastal dialect oral histories with instant playback from verified timestamps.
    </p>
    <div class="hero-pills">
        <span class="hero-pill">🛡️ 100% Offline & Private</span>
        <span class="hero-pill">⚡ SQLite FTS5 Indexed</span>
        <span class="hero-pill">🎯 Dialect-Aware Matching</span>
        <span class="hero-pill">🔍 Machine Finding Aid</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tabs = st.tabs(["🔍 Search Audio Archive", "📖 Dialect & Spelling Variants", "📊 Archive Status & Batch Ingestion"])

# ==========================================
# TAB 1: SEARCH AUDIO ARCHIVE
# ==========================================
with tabs[0]:
    # Search Bar & Controls
    col_search, col_btn = st.columns([5, 1])
    with col_search:
        user_input = st.text_input(
            "Search Archive:",
            value=st.session_state["search_query"],
            placeholder="Type a word or phrase (e.g. wazee, kaya, ng'ombe, mila, historia)...",
            label_visibility="collapsed"
        )
    with col_btn:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    # Suggestion Chips
    st.markdown("""
    <div class="chip-container">
        <span class="chip-label">Quick Suggestions:</span>
    </div>
    """, unsafe_allow_html=True)

    chip_cols = st.columns([1, 1, 1, 1, 1, 3])
    suggestions = ["kaya", "wazee", "ng'ombe", "mila", "pwani"]
    for i, word in enumerate(suggestions):
        with chip_cols[i]:
            if st.button(f"#{word}", key=f"chip_{word}", use_container_width=True):
                st.session_state["search_query"] = word
                st.rerun()

    # Search Settings Expander
    with st.expander("⚙️ Search Filters & Sensitivity Options", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            enable_fuzzy = st.checkbox("Enable approximate / fuzzy matching", value=True, help="Finds similar words even if there are typos or dialect pronunciation shifts.")
        with c2:
            fuzzy_threshold = st.slider("Fuzzy match sensitivity", min_value=70, max_value=95, value=config.search.fuzzy_threshold, help="Higher values require closer character matches.")
        with c3:
            max_results = st.number_input("Maximum matches", min_value=10, max_value=200, value=config.search.max_results)

    # Run Search
    active_query = user_input.strip()
    if active_query:
        results = search(
            conn,
            active_query,
            fuzzy_threshold=fuzzy_threshold,
            max_results=max_results,
            enable_fuzzy=enable_fuzzy
        )

        if not results:
            st.warning(f"No recordings found matching '{active_query}'. You can try enabling fuzzy matching or adding a spelling variant in the **📖 Dialect & Spelling Variants** tab.")
        else:
            # Result Meta Header
            st.markdown(f"#### Found **{len(results)}** audio match{'es' if len(results) > 1 else ''} for *\"{active_query}\"*")

            # Quick Export Action
            col_exp1, col_exp2 = st.columns([4, 1])
            with col_exp2:
                csv_buf = io.StringIO()
                csv_w = csv.writer(csv_buf)
                csv_w.writerow(["recording", "timestamp", "start_seconds", "end_seconds", "excerpt", "match_type", "confidence"])
                for r in results:
                    m, s = divmod(int(r.start_s), 60)
                    csv_w.writerow([Path(r.recording_path).name, f"{m:02d}:{s:02d}", r.start_s, r.end_s, r.text, r.match_type, r.confidence])
                
                st.download_button(
                    label="📥 Export to CSV",
                    data=csv_buf.getvalue(),
                    file_name=f"kaya_search_{active_query}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.write("")

            # Display Result Cards
            for idx, r in enumerate(results, 1):
                rec_path = Path(r.recording_path)
                rec_name = rec_path.name
                m, s = divmod(int(r.start_s), 60)
                timestamp_str = f"{m:02d}:{s:02d}"

                # Match badges
                badge_type = f"badge-{r.match_type}"
                match_label = f"{r.match_type.upper()}"
                if r.match_type == "variant":
                    match_label = f"VARIANT ({r.matched_term})"

                highlighted_excerpt = highlight_matches(r.text, active_query, r.matched_term)

                # Check if human corrections exist
                cur = conn.execute("SELECT * FROM corrections WHERE segment_id = ? ORDER BY id DESC LIMIT 1", (r.segment_id,))
                latest_corr = cur.fetchone()

                st.markdown(f"""
                <div class="result-card">
                    <div class="card-header-flex">
                        <div class="recording-name">
                            <span>🎙️ {rec_name}</span>
                        </div>
                        <div>
                            <span class="timestamp-badge">⏱️ {timestamp_str} ({r.start_s:.1f}s)</span>
                            <span class="badge {badge_type}">Match: {match_label}</span>
                            <span class="badge badge-conf">AI Conf: {r.confidence:.0%}</span>
                        </div>
                    </div>
                    <div>
                        <span class="machine-notice">⚠️ Machine-generated: verify against the audio</span>
                        {'<span class="verified-banner">✅ Verified by ' + html.escape(latest_corr["reviewer"]) + '</span>' if latest_corr else ''}
                    </div>
                    <div class="excerpt-box">
                        "{highlighted_excerpt}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Audio Player & Quick Snippet Action
                col_play, col_clip = st.columns([4, 1])
                with col_play:
                    if rec_path.exists():
                        st.audio(str(rec_path), start_time=int(r.start_s))
                    else:
                        st.error(f"Audio file not found at: `{rec_path}`")
                        
                with col_clip:
                    # Clip download button
                    clip_name = f"clip_{rec_path.stem}_{int(r.start_s)}s.wav"
                    clip_out = config.paths.work_dir / clip_name
                    if st.button(f"✂️ Extract Clip", key=f"clip_btn_{r.segment_id}", use_container_width=True):
                        try:
                            start_clip = max(0.0, r.start_s - 1.0)
                            end_clip = r.end_s + 1.0
                            clip_audio(rec_path, clip_out, start_s=start_clip, end_s=end_clip)
                            if clip_out.exists():
                                with open(clip_out, "rb") as f:
                                    st.download_button(
                                        label=f"💾 Save {clip_name}",
                                        data=f.read(),
                                        file_name=clip_name,
                                        mime="audio/wav",
                                        key=f"dl_clip_{r.segment_id}",
                                        use_container_width=True
                                    )
                        except Exception as e:
                            st.warning(f"Could not extract clip: {e}")

                # Human Verification & Correction Expander
                with st.expander("✍️ Human Verification & Corrections (Researcher Log)"):
                    cur_all = conn.execute("SELECT * FROM corrections WHERE segment_id = ? ORDER BY id DESC", (r.segment_id,))
                    all_corrs = cur_all.fetchall()
                    if all_corrs:
                        st.markdown("**Previous Verified Corrections:**")
                        for c in all_corrs:
                            st.success(f"“{c['corrected_text']}” — *{c['reviewer']}* ({c['created_at']})")

                    st.markdown("**Add or Update Verified Transcript:**")
                    c_col1, c_col2 = st.columns([3, 1])
                    with c_col1:
                        new_corr_text = st.text_input(
                            "Verified text heard in audio:",
                            value=latest_corr["corrected_text"] if latest_corr else r.text,
                            key=f"input_corr_{r.segment_id}"
                        )
                    with c_col2:
                        rev_name = st.text_input(
                            "Reviewer:",
                            value=st.session_state["reviewer_name"],
                            key=f"input_rev_{r.segment_id}"
                        )
                        st.session_state["reviewer_name"] = rev_name

                    if st.button("Save Verified Correction", key=f"save_btn_{r.segment_id}", type="secondary"):
                        if new_corr_text.strip():
                            conn.execute(
                                "INSERT INTO corrections (segment_id, corrected_text, reviewer, created_at) VALUES (?, ?, ?, datetime('now'))",
                                (r.segment_id, new_corr_text.strip(), rev_name.strip())
                            )
                            conn.commit()
                            st.toast("✅ Correction saved to research archive!", icon="🎉")
                            st.rerun()

                st.markdown("<hr style='margin: 18px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)
    else:
        st.info("Enter a keyword above to search across the audio recordings.")

# ==========================================
# TAB 2: SPELLING & DIALECT VARIANTS
# ==========================================
with tabs[1]:
    st.subheader("📖 Researcher Spelling Variants & Coastal Dialect Synonyms")
    st.caption("Oral history recordings feature coastal Swahili dialects (e.g. Mijikenda, Bajuni, Kimvita). Define variants so searches automatically cover alternative pronunciations and spellings.")

    # Preset Suggestions
    with st.expander("💡 One-Click Coastal Dialect Presets", expanded=True):
        st.write("Add common coastal variations to your archive:")
        preset_cols = st.columns(4)
        presets = [
            ("ng'ombe", "ngombe", "Coastal spelling without apostrophe"),
            ("mzee", "muzee", "Dialect variant for elder"),
            ("kikao", "chao", "Coastal dialect meeting"),
            ("chake", "tshake", "Dialect sound shift"),
        ]
        for idx, (p_term, p_var, p_note) in enumerate(presets):
            with preset_cols[idx % 4]:
                if st.button(f"+ {p_term} ↔ {p_var}", key=f"preset_{idx}", use_container_width=True):
                    add_variant(conn, p_term, p_var, p_note)
                    st.toast(f"Added variant pair: {p_term} ↔ {p_var}")
                    st.rerun()

    # Add Custom Variant Form
    with st.form("add_custom_variant_form"):
        st.markdown("##### Add New Variant Pair")
        col_v1, col_v2, col_v3 = st.columns([2, 2, 3])
        with col_v1:
            term_val = st.text_input("Standard Term", placeholder="e.g. ng'ombe")
        with col_v2:
            var_val = st.text_input("Variant / Dialect Spelling", placeholder="e.g. ngombe")
        with col_v3:
            note_val = st.text_input("Linguistic Note / Dialect", placeholder="e.g. Giriama or Digo dialect variation")

        if st.form_submit_button("Add Variant Pair", type="primary"):
            if term_val.strip() and var_val.strip():
                add_variant(conn, term_val.strip(), var_val.strip(), note_val.strip())
                st.success(f"Added variant: **{term_val.strip()}** ↔ **{var_val.strip()}**")
                st.rerun()
            else:
                st.error("Both Standard Term and Variant are required.")

    # Variants Table & Management
    st.markdown("##### Active Variants in Database")
    cur_v = conn.execute("SELECT id, term, variant, note FROM variants ORDER BY id DESC")
    all_v = cur_v.fetchall()

    if all_v:
        # Display as clean cards with delete option
        for v in all_v:
            v_col_t, v_col_del = st.columns([6, 1])
            with v_col_t:
                st.markdown(f"**`{v['term']}`** ↔ **`{v['variant']}`** &nbsp; <span style='color: #64748b; font-size: 0.9rem;'>{v['note'] or ''}</span>", unsafe_allow_html=True)
            with v_col_del:
                if st.button("🗑️ Remove", key=f"del_v_{v['id']}", use_container_width=True):
                    conn.execute("DELETE FROM variants WHERE id = ?", (v['id'],))
                    conn.commit()
                    st.toast("Variant removed.")
                    st.rerun()
    else:
        st.info("No variants added yet. Use the presets or form above.")

# ==========================================
# TAB 3: ARCHIVE STATUS & BATCH INGESTION
# ==========================================
with tabs[2]:
    st.subheader("📊 Archive Status & Batch Pipeline Management")
    st.caption("Monitor the status of oral-history recordings, ingestion health, and offline safeguards.")

    # Stats Calculation
    cur_rec = conn.execute("SELECT COUNT(*) FROM recordings")
    total_recs = cur_rec.fetchone()[0]

    cur_done = conn.execute("SELECT COUNT(*) FROM recordings WHERE status = 'done'")
    done_recs = cur_done.fetchone()[0]

    cur_fail = conn.execute("SELECT COUNT(*) FROM recordings WHERE status = 'failed'")
    fail_recs = cur_fail.fetchone()[0]

    cur_segs = conn.execute("SELECT COUNT(*) FROM segments")
    total_segs = cur_segs.fetchone()[0]

    cur_dur = conn.execute("SELECT SUM(duration_s) FROM recordings WHERE status = 'done'")
    total_dur_s = cur_dur.fetchone()[0] or 0.0
    total_hours = total_dur_s / 3600.0

    cur_vocab = conn.execute("SELECT COUNT(*) FROM vocab")
    total_vocab = cur_vocab.fetchone()[0]

    # Metrics Grid
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Recordings Indexed</div>
            <div class="metric-value">{done_recs} <span style="font-size: 1rem; color: #94a3b8;">/ {total_recs}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Indexed Audio Time</div>
            <div class="metric-value">{total_hours:.1f} <span style="font-size: 1rem; color: #94a3b8;">hrs</span></div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Searchable Segments</div>
            <div class="metric-value">{total_segs:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Vocabulary Terms</div>
            <div class="metric-value">{total_vocab:,}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Progress toward 300 Hours Collection Goal
    target_hours = 300.0
    progress_val = min(1.0, max(0.001, total_hours / target_hours))
    st.markdown(f"**Collection Ingestion Progress:** {total_hours:.1f} of {target_hours:.0f} target hours ({progress_val * 100:.1f}%)")
    st.progress(progress_val)

    st.divider()

    # Privacy and Local Execution Audit Box
    st.markdown("##### 🛡️ Privacy & Local Security Safeguards")
    st.info("""
    - **100% Offline Mode**: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are actively enforced.
    - **Zero Data Leakage**: All audio transcription and search indexing executes strictly on this machine.
    - **Cultural Sensitivity**: Raw machine transcript text is never logged to files or transmitted across networks.
    """)

    # Batch Ingestion Runner
    st.markdown("##### 📁 Batch Ingestion Runner")
    st.markdown(f"""
    - **Audio Source Directory:** `{config.paths.audio_dir}`
    - **Target Database:** `{config.paths.db_path}`
    - **Whisper Model:** `{config.transcription.model_size}` (Swahili `'sw'`)
    """)
    st.write("Drop new `.mp3`, `.wav`, `.m4a`, or `.flac` files into the audio folder, then click below. The pipeline automatically skips previously completed files.")

    if st.button("🚀 Run / Resume Batch Ingestion", type="primary", use_container_width=True):
        with st.spinner("Processing oral-history audio files... Please wait."):
            stats = run_pipeline(config)
            st.success(f"Batch run completed! New: {stats['done']}, Skipped (already done): {stats['skipped']}, Failed: {stats['failed']}.")
            st.rerun()

    # Failed Files Log (if any)
    if fail_recs > 0:
        st.markdown("##### ⚠️ Problematic Files Log")
        cur_err = conn.execute("SELECT path, error, processed_at FROM recordings WHERE status = 'failed'")
        err_rows = cur_err.fetchall()
        for err in err_rows:
            st.error(f"**{Path(err['path']).name}**: {err['error']} ({err['processed_at']})")
