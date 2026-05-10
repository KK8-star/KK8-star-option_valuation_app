"""
app.py - メインエントリポイント v0.3.3
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="非上場企業向けオプション評価システム",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.data.database import get_db_manager

@st.cache_resource
def _init_db():
    db = get_db_manager()
    db.create_tables()
    return db

_init_db()

from src.ui.pages import home, new_valuation, case_list

PAGES = {
    "🏠 ホーム":   home,
    "📈 新規評価": new_valuation,
    "📋 評価一覧": case_list,
    "⚙️ 設定":     None,
}

PAGE_KEYS = list(PAGES.keys())

if "current_page" not in st.session_state:
    st.session_state["current_page"] = PAGE_KEYS[0]

if st.session_state["current_page"] not in PAGES:
    st.session_state["current_page"] = PAGE_KEYS[0]

_current = st.session_state["current_page"]

try:
    _radio_index = PAGE_KEYS.index(_current)
except ValueError:
    _radio_index = 0

# ─── サイドバー ───────────────────────────────────────
with st.sidebar:

    # ロゴ画像
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=200)
        st.divider()


    st.divider()

    # ナビゲーション
    sel = st.radio(
        "メニュー",
        PAGE_KEYS,
        index=_radio_index,
        label_visibility="collapsed",
    )

    if sel != _current:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()

    st.divider()
    st.caption("v0.3.3 | Python 3.12")
    st.caption("© 2026 KAZAMA CPA OFFICE/Marleight.LLC")
    st.caption("All Rights Reserved.")

# ─── ページ描画 ───────────────────────────────────────
page_module = PAGES[st.session_state["current_page"]]

if page_module is None:
    st.title(st.session_state["current_page"])
    st.info("🚧 このページは準備中です。")
elif hasattr(page_module, "render"):
    page_module.render()
else:
    st.error("ページモジュールに render() が見つかりません。")
