"""
app.py - メインエントリポイント v0.3.3
"""
import streamlit as st

st.set_page_config(
    page_title="オプション評価システム",
    page_icon="📊",
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
    "🏠 ホーム":     home,
    "📊 新規評価":   new_valuation,
    "📋 ケース一覧": case_list,
    "⚙️ 設定":       None,
}

PAGE_KEYS = list(PAGES.keys())

# 初期化
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "🏠 ホーム"

# current_pageが不正な値なら初期化
if st.session_state["current_page"] not in PAGES:
    st.session_state["current_page"] = "🏠 ホーム"

_current = st.session_state["current_page"]

try:
    _radio_index = PAGE_KEYS.index(_current)
except ValueError:
    _radio_index = 0

# ─── サイドバー ───────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding:0.5rem 0 1rem;">
            <h2 style="margin:0;font-size:1.3rem;">📊 オプション評価</h2>
            <p style="margin:0;font-size:0.78rem;color:#888;">
                非上場企業向け公正価値算定システム
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    sel = st.radio(
        "メニュー",
        PAGE_KEYS,
        index=_radio_index,
        label_visibility="collapsed",
    )

    # サイドバー操作時のみ更新（ボタン遷移を上書きしない）
    if sel != _current:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()

    st.divider()
    st.caption("v0.3.3 | Python 3.12")

# ─── ページ描画 ───────────────────────────────────────
page_module = PAGES[st.session_state["current_page"]]

if page_module is None:
    st.title(st.session_state["current_page"])
    st.info("🚧 このページは準備中です")
elif hasattr(page_module, "render"):
    page_module.render()
else:
    st.error("ページモジュールに render() が見つかりません")
