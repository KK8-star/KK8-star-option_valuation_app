# fix_pages.py
app_content = """\
\"\"\"
app.py - メインエントリポイント v0.3.3
\"\"\"
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
        key="nav_radio",
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
"""

home_content = """\
\"\"\"
src/ui/pages/home.py - ホームページ
\"\"\"
from __future__ import annotations
import streamlit as st
from sqlalchemy import func, select
from src.data.database import get_session
from src.data.models import ValuationCase, ComparableTicker

def render() -> None:
    st.title("非上場会社向けオプション評価システム")

    try:
        with get_session() as session:
            total_cases = session.scalar(select(func.count(ValuationCase.id))) or 0
            total_tickers = session.scalar(select(func.count(ComparableTicker.id))) or 0
            recent_rows = session.execute(
                select(ValuationCase.id, ValuationCase.case_name, ValuationCase.created_at)
                .order_by(ValuationCase.created_at.desc())
                .limit(5)
            ).all()
            recent_data = [
                {"id": r.id, "case_name": r.case_name, "created_at": r.created_at}
                for r in recent_rows
            ]
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("評価ケース数", total_cases)
    col2.metric("比較ティッカー数", total_tickers)
    col3.metric("アクティブ", total_cases)
    st.divider()

    st.subheader("クイックアクション")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("新規評価を開始", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "新規評価"
            st.rerun()
    with c2:
        if st.button("ケース一覧を見る", use_container_width=True):
            st.session_state["current_page"] = "ケース一覧"
            st.rerun()

    st.divider()
    st.subheader("最近の評価ケース（最新5件）")

    if not recent_data:
        st.info("まだ評価ケースがありません。新規評価から開始してください。")
        return

    for item in recent_data:
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 3, 1])
            col_a.markdown(f"**{item['case_name']}**")
            if item["created_at"]:
                col_b.caption(f"作成日: {item['created_at'].strftime('%Y-%m-%d %H:%M')}")
            else:
                col_b.caption("作成日: -")
            with col_c:
                if st.button("詳細", key=f"home_detail_{item['id']}"):
                    st.session_state["current_page"] = "ケース一覧"
                    st.session_state["selected_case_id"] = item["id"]
                    st.rerun()
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)
print("app.py 完了")

with open("src/ui/pages/home.py", "w", encoding="utf-8") as f:
    f.write(home_content)
print("home.py 完了")
