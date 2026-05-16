"""
app.py - メインエントリポイント v0.3.3
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="オプション評価システム",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.data.database import get_db_manager
from src.ui.auth import check_password

@st.cache_resource
def _init_db():
    db = get_db_manager()
    db.create_tables()
    return db

_init_db()

if not check_password():
    st.stop()

from src.ui.pages import home, new_valuation, case_list

PAGES = {
    "ホーム":      home,
    "新規評価":    new_valuation,
    "ケース一覧":  case_list,
    "設定":        None,
}

PAGE_KEYS = list(PAGES.keys())

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "ホーム"
if st.session_state["current_page"] not in PAGES:
    st.session_state["current_page"] = "ホーム"

with st.sidebar:
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    st.markdown(
        '<div style="padding:0.5rem 0 1rem;">'
        '<h2 style="margin:0;font-size:1.3rem;">オプション評価</h2>'
        '<p style="margin:0;font-size:0.78rem;color:#888;">非上場企業向け公正価値算定システム</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("風間会計事務所")
    st.divider()

    try:
        radio_index = PAGE_KEYS.index(st.session_state["current_page"])
    except ValueError:
        radio_index = 0

    sel = st.radio(
        "メニュー",
        PAGE_KEYS,
        index=radio_index,
        key=f"nav_radio_{st.session_state['current_page']}",
        label_visibility="collapsed",
    )

    if sel != st.session_state["current_page"]:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()

    st.divider()
    st.caption("v0.3.3")
    st.caption("(c) 風間会計事務所")

page_module = PAGES[st.session_state["current_page"]]

if page_module is None:
    st.title(st.session_state["current_page"])
    st.info("このページは準備中です")
elif hasattr(page_module, "render"):
    page_module.render()
else:
    st.error("ページモジュールに render() が見つかりません")
