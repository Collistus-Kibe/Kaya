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
from kayasearch.seed_demo import seed_sample_archive

st.set_page_config(
    page_title="Kaya Search — Kwale Indigenous Medical Knowledge Archive",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State
if "search_query" not in st.session_state:
    st.session_state["search_query"] = "malaria"
if "reviewer_name" not in st.session_state:
    st.session_state["reviewer_name"] = "Fatuma (PhD Researcher)"

# Load configuration and DB connection
def get_config_and_db():
    project_root = Path(__file__).resolve().parents[3]
    config = load_config("config.yaml", project_root=project_root)
    conn = connect(config.paths.db_path, check_same_thread=False)
    init_db(conn)
    count = conn.execute("SELECT COUNT(*) FROM recordings").fetchone()[0]
    if count == 0:
        conn.close()
        seed_sample_archive(project_root=project_root, allow_tts=False)
        conn = connect(config.paths.db_path, check_same_thread=False)
    return config, conn

config, conn = get_config_and_db()

# Custom Styling (Bespoke Sacred Kaya Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #064e3b 0%, #065f46 45%, #0f172a 100%);
        color: #ffffff;
        padding: 28px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px -6px rgba(6, 78, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .hero-badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(52, 211, 153, 0.2);
        border: 1px solid rgba(52, 211, 153, 0.4);
        border-radius: 20px;
        color: #6ee7b7;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: #ffffff;
    }
    .hero-sub {
        font-size: 0.98rem;
        color: #cbd5e1;
        margin: 0;
        max-width: 820px;
        line-height: 1.5;
    }
    .hero-pills {
        margin-top: 16px;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .hero-pill {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        color: #f1f5f9;
        font-weight: 500;
    }

    /* =================================================== */
    /* BESPOKE SEGMENTED TAB BAR NAVIGATION                */
    /* =================================================== */
    div[data-baseweb="tab-list"] {
        background: #09121f !important;
        padding: 6px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        gap: 8px !important;
        margin: 6px 0 24px 0 !important;
        display: flex !important;
        width: 100% !important;
        box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.45) !important;
    }

    div[data-baseweb="tab-border"],
    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 1 0 !important;
        height: auto !important;
        padding: 11px 20px !important;
        border-radius: 10px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.94rem !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
        justify-content: center !important;
        text-align: center !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #f1f5f9 !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #065f46 0%, #047857 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(52, 211, 153, 0.55) !important;
        box-shadow: 0 4px 14px -2px rgba(5, 150, 105, 0.5) !important;
    }

    /* =================================================== */
    /* THEME-MATCHED BUTTONS (EMERALD PRIMARY, NO RED)     */
    /* =================================================== */
    button[kind="primary"],
    div.stButton > button[kind="primary"],
    .stButton > button[type="primary"],
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        border: 1px solid rgba(52, 211, 153, 0.5) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 0.55rem 1.4rem !important;
        box-shadow: 0 4px 14px -2px rgba(16, 185, 129, 0.45) !important;
        transition: all 0.2s ease !important;
    }

    button[kind="primary"]:hover,
    div.stButton > button[kind="primary"]:hover,
    .stButton > button[type="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        border-color: #34d399 !important;
        box-shadow: 0 6px 20px -2px rgba(16, 185, 129, 0.65) !important;
        transform: translateY(-1px);
    }

    /* Secondary / Topic Pill Buttons */
    button[kind="secondary"],
    div.stButton > button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background: rgba(15, 23, 42, 0.65) !important;
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover,
    div.stButton > button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        border-color: rgba(52, 211, 153, 0.6) !important;
        background: rgba(16, 185, 129, 0.15) !important;
        color: #a7f3d0 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px -2px rgba(16, 185, 129, 0.25) !important;
    }

    /* Search & Text Inputs */
    div[data-baseweb="input"] {
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        background: rgba(15, 23, 42, 0.65) !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #10b981 !important;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25) !important;
    }

    /* Result Card Wrapper */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        background: rgba(15, 23, 42, 0.45) !important;
    }

    /* Badges */
    .badge-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .tag-exact { background: rgba(52, 211, 153, 0.18); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.4); }
    .tag-variant { background: rgba(96, 165, 250, 0.18); color: #93c5fd; border: 1px solid rgba(96, 165, 250, 0.4); }
    .tag-fuzzy { background: rgba(251, 191, 36, 0.18); color: #fde047; border: 1px solid rgba(251, 191, 36, 0.4); }
    .tag-time { background: rgba(148, 163, 184, 0.15); color: #e2e8f0; border: 1px solid rgba(148, 163, 184, 0.3); }

    /* Highlighting */
    mark.match-mark {
        background: rgba(250, 204, 21, 0.28);
        color: #fef08a;
        border: 1px solid rgba(250, 204, 21, 0.5);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
    }

    /* Dark Mode Compatible Excerpt Box */
    .excerpt-text {
        font-size: 1.05rem;
        line-height: 1.65;
        color: #f1f5f9;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #10b981;
        padding: 14px 18px;
        border-radius: 0 10px 10px 0;
        margin: 12px 0;
    }

    /* Machine notice */
    .machine-alert {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.35);
        color: #fcd34d;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* Citation Box */
    .citation-box {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.83rem;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 4px;
        overflow-x: auto;
    }
    .citation-label {
        font-weight: 700;
        color: #34d399;
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        background: rgba(52, 211, 153, 0.15);
        padding: 3px 7px;
        border-radius: 4px;
        white-space: nowrap;
    }
    .citation-text {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        color: #cbd5e1;
        word-break: break-all;
    }
</style>
""", unsafe_allow_html=True)

def highlight_excerpt(text: str, query: str, matched_term: str = "") -> str:
    """Highlight matched query words safely with regex and HTML escaping."""
    safe_text = html.escape(text)
    terms: Set[str] = set()
    for raw in [query, matched_term]:
        if raw and raw.strip():
            terms.add(raw.strip())
            for word in raw.strip().split():
                if len(word) >= 3:
                    terms.add(word)

    for t in sorted(terms, key=len, reverse=True):
        pattern = re.compile(rf"(?i)\b({re.escape(t)})\b")
        safe_text = pattern.sub(r'<mark class="match-mark">\1</mark>', safe_text)
    return safe_text

# Hero Banner
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">PhD Research Project — Kwale County, Kenya</div>
    <h1 class="hero-title">🌿 Kaya Indigenous Audio Search</h1>
    <p class="hero-sub">
        A fast, local audio search engine for <b>Fatuma's PhD research</b> on rare medicinal roots and healing knowledge preserved by Kwale Kaya elders. Search spoken recordings for specific diseases (like Malaria) or traditional cures with instant audio playback from exact timestamps.
    </p>
    <div class="hero-pills">
        <span class="hero-pill">100% Offline & Private</span>
        <span class="hero-pill">Kwale Sacred Kayas</span>
        <span class="hero-pill">Rare Medicinal Roots</span>
        <span class="hero-pill">Faster-Whisper ASR</span>
        <span class="hero-pill">SQLite FTS5 Indexed</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation
tabs = st.tabs([
    "Search Elder Recordings",
    "Medical & Dialect Variants",
    "Archive Health & Ingestion"
])

# ==========================================
# TAB 1: SEARCH ELDER RECORDINGS
# ==========================================
with tabs[0]:
    # Quick Topic Filters tailored for Fatuma's thesis
    st.markdown("##### Suggested Research Topics for Your Thesis:")
    q_cols = st.columns(6)
    quick_topics = [
        ("Malaria", "malaria"),
        ("Mwarubaini", "mwarubaini"),
        ("Mizizi ya Dawa", "mizizi"),
        ("Homa Kali", "homa"),
        ("Kaya Kinondo", "kinondo"),
        ("Wazee wa Kwale", "wazee")
    ]
    for idx, (label, kw) in enumerate(quick_topics):
        with q_cols[idx]:
            if st.button(label, key=f"quick_{kw}", use_container_width=True):
                st.session_state["search_query"] = kw
                st.rerun()

    st.write("")

    # Search Bar
    c_input, c_btn = st.columns([5, 1])
    with c_input:
        user_query = st.text_input(
            "Search Recordings:",
            value=st.session_state["search_query"],
            placeholder="Type disease, plant name, or topic (e.g. malaria, mwarubaini, mizizi, homa, tiba)...",
            label_visibility="collapsed"
        )
    with c_btn:
        search_pressed = st.button("Search", type="primary", use_container_width=True)

    # Search Options
    with st.expander("Search Sensitivity & Settings", expanded=False):
        s_c1, s_c2, s_c3 = st.columns(3)
        with s_c1:
            enable_fuzzy = st.checkbox("Enable dialect/fuzzy matching", value=True, help="Finds similar elder pronunciations and slight spelling differences.")
        with s_c2:
            fuzzy_threshold = st.slider("Fuzzy sensitivity", min_value=70, max_value=95, value=config.search.fuzzy_threshold)
        with s_c3:
            max_results = st.number_input("Max results", min_value=5, max_value=100, value=config.search.max_results)

    # Perform Search
    active_q = user_query.strip()
    if active_q:
        results = search(
            conn,
            active_q,
            fuzzy_threshold=fuzzy_threshold,
            max_results=max_results,
            enable_fuzzy=enable_fuzzy
        )

        if not results:
            st.warning(f"No recordings found containing **\"{active_q}\"**. Try searching for related Swahili terms like *homa*, *mizizi*, or *dawa*.")
        else:
            # Result Count & CSV Export
            r_head, r_exp = st.columns([4, 1])
            with r_head:
                st.markdown(f"### Found **{len(results)}** match{'es' if len(results) > 1 else ''} for *\"{active_q}\"*")
            with r_exp:
                csv_buf = io.StringIO()
                csv_w = csv.writer(csv_buf)
                csv_w.writerow(["recording", "timestamp", "start_s", "end_s", "excerpt", "match_type", "confidence"])
                for r in results:
                    m, s = divmod(int(r.start_s), 60)
                    csv_w.writerow([Path(r.recording_path).name, f"{m:02d}:{s:02d}", r.start_s, r.end_s, r.text, r.match_type, r.confidence])
                
                st.download_button(
                    label="Export to CSV",
                    data=csv_buf.getvalue(),
                    file_name=f"kwale_research_{active_q}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.write("")

            # Render Result Cards using clean st.container(border=True)
            for idx, r in enumerate(results, 1):
                rec_path = Path(r.recording_path)
                rec_name = rec_path.name
                m, s = divmod(int(r.start_s), 60)
                timestamp_str = f"{m:02d}:{s:02d}"

                # Match badges
                tag_class = f"tag-{r.match_type}"
                match_label = f"{r.match_type.upper()}"
                if r.match_type == "variant":
                    match_label = f"VARIANT ({r.matched_term})"

                highlighted_html = highlight_excerpt(r.text, active_q, r.matched_term)

                # Check for verified corrections
                cur = conn.execute("SELECT * FROM corrections WHERE segment_id = ? ORDER BY id DESC LIMIT 1", (r.segment_id,))
                latest_corr = cur.fetchone()

                with st.container(border=True):
                    # Header row
                    col_h1, col_h2 = st.columns([3, 2])
                    with col_h1:
                        st.markdown(f"#### {rec_name}")
                    with col_h2:
                        st.markdown(f"""
                        <div style="text-align: right;">
                            <span class="badge-tag tag-time">{timestamp_str} ({r.start_s:.1f}s)</span>
                            <span class="badge-tag {tag_class}">Match: {match_label} ({r.score:.0f}%)</span>
                        </div>
                        """, unsafe_allow_html=True)

                    # Required Ethics Notice & Verification Banner
                    st.markdown("""<div class="machine-alert">Machine-generated transcript — verify against audio before citing in thesis</div>""", unsafe_allow_html=True)
                    if latest_corr:
                        st.success(f"**Verified by {latest_corr['reviewer']}**: “{latest_corr['corrected_text']}”")

                    # Highlighted Excerpt (Rendered Cleanly, No Raw HTML Leaks)
                    st.markdown(f"""<div class="excerpt-text">"{highlighted_html}"</div>""", unsafe_allow_html=True)

                    # Audio Player
                    if rec_path.exists():
                        st.audio(str(rec_path), start_time=int(r.start_s))
                    else:
                        st.error(f"Audio file not found on disk at: `{rec_path}`")

                    # Actions Row: Citation & Clip Download
                    a_col1, a_col2 = st.columns([3, 1])
                    with a_col1:
                        # Quick thesis citation generator
                        citation_text = f"Kwale Kaya Oral Archive, Recording: {rec_name}, Timestamp: {timestamp_str} ({r.start_s:.1f}s). Excerpt: \"{latest_corr['corrected_text'] if latest_corr else r.text}\""
                        safe_cite = html.escape(citation_text)
                        st.markdown(f"""
                        <div class="citation-box">
                            <span class="citation-label">Thesis Citation</span>
                            <span class="citation-text">{safe_cite}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with a_col2:
                        clip_name = f"clip_{rec_path.stem}_{int(r.start_s)}s.wav"
                        clip_out = config.paths.work_dir / clip_name
                        if st.button("Extract Audio Clip", key=f"clip_btn_{r.segment_id}", use_container_width=True):
                            try:
                                start_clip = max(0.0, r.start_s - 1.0)
                                end_clip = r.end_s + 1.5
                                clip_audio(rec_path, clip_out, start_s=start_clip, end_s=end_clip)
                                if clip_out.exists():
                                    with open(clip_out, "rb") as f:
                                        st.download_button(
                                            label=f"Save {clip_name}",
                                            data=f.read(),
                                            file_name=clip_name,
                                            mime="audio/wav",
                                            key=f"dl_clip_{r.segment_id}",
                                            use_container_width=True
                                        )
                            except Exception as e:
                                st.warning(f"Could not extract clip: {e}")

                    # Human Verification Expander
                    with st.expander("Human Verification Note (Add / Edit Verified Transcript)"):
                        v_col1, v_col2 = st.columns([3, 1])
                        with v_col1:
                            corr_input = st.text_input(
                                "Verified elder words heard in audio:",
                                value=latest_corr["corrected_text"] if latest_corr else r.text,
                                key=f"corr_text_{r.segment_id}"
                            )
                        with v_col2:
                            rev_input = st.text_input(
                                "Reviewer Name:",
                                value=st.session_state["reviewer_name"],
                                key=f"rev_input_{r.segment_id}"
                            )
                            st.session_state["reviewer_name"] = rev_input

                        if st.button("Save Verified Transcript", key=f"save_corr_{r.segment_id}", type="secondary"):
                            if corr_input.strip():
                                conn.execute(
                                    "INSERT INTO corrections (segment_id, corrected_text, reviewer, created_at) VALUES (?, ?, ?, datetime('now'))",
                                    (r.segment_id, corr_input.strip(), rev_input.strip())
                                )
                                conn.commit()
                                st.toast("Verified transcript saved!")
                                st.rerun()

# ==========================================
# TAB 2: MEDICAL & DIALECT VARIANTS
# ==========================================
with tabs[1]:
    st.subheader("Kwale Dialect & Traditional Medical Synonyms")
    st.caption("Elders in Kwale use coastal dialect pronunciations and local names for diseases and herbs. Define variants so searching for 'malaria' automatically finds related indigenous terms.")

    # One-Click Coastal Medical Presets
    with st.expander("One-Click Presets for Kaya Medical Knowledge", expanded=True):
        st.write("Add common medical and dialect pairings for Kwale research:")
        p_cols = st.columns(3)
        medical_presets = [
            ("malaria", "homa ya malaria", "Swahili term for malaria fever"),
            ("malaria", "mwarubaini", "Traditional neem tree used for malaria"),
            ("dawa", "miti shamba", "Traditional herbal medicine"),
            ("mzee", "muzee", "Coastal dialect spelling for elder"),
            ("ng'ombe", "ngombe", "Coastal spelling without apostrophe"),
            ("homa", "kizunguzungu", "Fever and dizziness symptoms")
        ]
        for p_idx, (p_term, p_var, p_note) in enumerate(medical_presets):
            with p_cols[p_idx % 3]:
                if st.button(f"+ {p_term} ↔ {p_var}", key=f"p_med_{p_idx}", use_container_width=True):
                    add_variant(conn, p_term, p_var, p_note)
                    st.toast(f"Added variant: {p_term} ↔ {p_var}")
                    st.rerun()

    st.write("")

    # Add Custom Variant
    with st.form("custom_med_variant"):
        st.markdown("##### Add New Synonym / Dialect Pair")
        v1, v2, v3 = st.columns([2, 2, 3])
        with v1:
            term_in = st.text_input("Standard Term", placeholder="e.g. malaria")
        with v2:
            var_in = st.text_input("Dialect / Herbal Variant", placeholder="e.g. mwarubaini")
        with v3:
            note_in = st.text_input("Botanical / Cultural Note", placeholder="e.g. Neem root used to boil for malaria")

        if st.form_submit_button("Add Medical Variant", type="primary"):
            if term_in.strip() and var_in.strip():
                add_variant(conn, term_in.strip(), var_in.strip(), note_in.strip())
                st.success(f"Added variant: **{term_in.strip()}** ↔ **{var_in.strip()}**")
                st.rerun()
            else:
                st.error("Both Standard Term and Variant are required.")

    # Active Variants List
    st.markdown("##### Active Medical & Dialect Variants")
    cur_v = conn.execute("SELECT id, term, variant, note FROM variants ORDER BY id DESC")
    all_v = cur_v.fetchall()
    if all_v:
        for v in all_v:
            col_vt, col_vd = st.columns([6, 1])
            with col_vt:
                st.markdown(f"**`{v['term']}`** ↔ **`{v['variant']}`** &nbsp; <span style='color: #64748b;'>{v['note'] or ''}</span>", unsafe_allow_html=True)
            with col_vd:
                if st.button("Delete", key=f"del_v_{v['id']}", use_container_width=True):
                    conn.execute("DELETE FROM variants WHERE id = ?", (v['id'],))
                    conn.commit()
                    st.toast("Variant removed.")
                    st.rerun()
    else:
        st.info("No variants added yet. Use the presets above.")

# ==========================================
# TAB 3: ARCHIVE HEALTH & INGESTION
# ==========================================
with tabs[2]:
    st.subheader("Archive Status & Batch Ingestion Pipeline")
    st.caption("Monitor the status of your 300 hours of Kwale elder recordings.")

    # Fetch Metrics
    cur_rec = conn.execute("SELECT COUNT(*) FROM recordings")
    tot_rec = cur_rec.fetchone()[0]

    cur_done = conn.execute("SELECT COUNT(*) FROM recordings WHERE status = 'done'")
    done_rec = cur_done.fetchone()[0]

    cur_seg = conn.execute("SELECT COUNT(*) FROM segments")
    tot_seg = cur_seg.fetchone()[0]

    cur_dur = conn.execute("SELECT SUM(duration_s) FROM recordings WHERE status = 'done'")
    tot_dur = cur_dur.fetchone()[0] or 0.0
    tot_hrs = tot_dur / 3600.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Elder Recordings Indexed", f"{done_rec} / {tot_rec}")
    m2.metric("Total Indexed Duration", f"{tot_hrs:.1f} hours")
    m3.metric("Searchable Speech Segments", f"{tot_seg:,}")
    m4.metric("Offline Security", "100% Local")

    st.write("")

    # Progress towards 300 Hours Collection Goal
    target_hours = 300.0
    prog = min(1.0, max(0.001, tot_hrs / target_hours))
    st.markdown(f"**Fatuma's Thesis Progress:** {tot_hrs:.1f} of {target_hours:.0f} target collection hours ({prog * 100:.1f}%)")
    st.progress(prog)

    st.divider()

    # Ingestion Trigger
    st.markdown("##### Ingest New Field Recordings")
    st.caption(f"Audio directory: `{config.paths.audio_dir}` | Local database: `{config.paths.db_path}`")
    st.write("Place your audio interview files (`.mp3`, `.wav`, `.m4a`, `.flac`) into the audio folder, then click below. Already transcribed files are automatically skipped.")

    if st.button("Run / Resume Batch Ingestion", type="primary", use_container_width=True):
        with st.spinner("Transcribing and indexing elder audio recordings..."):
            stats = run_pipeline(config)
            st.success(f"Batch completed! Processed: {stats['done']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}.")
            st.rerun()
