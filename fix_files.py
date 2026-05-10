# -*- coding: utf-8 -*-
"""全ファイルをUTF-8で書き直す修復スクリプト"""
import pathlib

# ========== app.py ==========
app_content = """\
\"\"\"
app.py - メインエントリポイント v0.3.2
\"\"\"
import streamlit as st

st.set_page_config(
    page_title="株式報酬向けオプション評価システム",
    page_icon="\U0001f4b9",
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

from src.ui.pages import home, new_valuation, case_list, case_detail

PAGES = {
    "\U0001f3e0 ホーム":     home,
    "\U0001f4b9 新規評価":   new_valuation,
    "\U0001f4cb 評価一覧":   case_list,
    "\U0001f4cb 評価詳細":   case_detail,
    "\u2699\ufe0f 設定":     None,
}

PAGE_KEYS    = list(PAGES.keys())
SIDEBAR_KEYS = [k for k in PAGE_KEYS if k != "\U0001f4cb 評価詳細"]

if "current_page" not in st.session_state:
    st.session_state["current_page"] = PAGE_KEYS[0]

if st.session_state["current_page"] not in PAGES:
    st.session_state["current_page"] = PAGE_KEYS[0]

_current = st.session_state["current_page"]
_sidebar_current = _current if _current in SIDEBAR_KEYS else "\U0001f4cb 評価一覧"

try:
    _radio_index = SIDEBAR_KEYS.index(_sidebar_current)
except ValueError:
    _radio_index = 0

with st.sidebar:
    st.markdown(
        \"\"\"
        <div style="padding:0.5rem 0 1rem;">
            <h2 style="margin:0;font-size:1.3rem;">\U0001f4b9 オプション評価</h2>
            <p style="margin:0;font-size:0.78rem;color:#888;">
                株式報酬向けオプション評価システム
            </p>
        </div>
        \"\"\",
        unsafe_allow_html=True,
    )
    st.divider()

    sel = st.radio(
        "メニュー",
        SIDEBAR_KEYS,
        index=_radio_index,
        label_visibility="collapsed",
    )

    if sel != _sidebar_current:
        st.session_state["current_page"] = sel
        st.session_state.pop("selected_case_id", None)
        st.rerun()

    st.divider()
    st.caption("v0.3.2 | Python 3.12")

page_module = PAGES[st.session_state["current_page"]]

if page_module is None:
    st.title(st.session_state["current_page"])
    st.info("\U0001f6a7 このページは準備中です。")
elif hasattr(page_module, "render"):
    page_module.render()
else:
    st.error("ページモジュールに render() が見つかりません。")
"""

# ========== ファイル書き込み ==========
files = {
    "app.py": app_content,
}

for filename, content in files.items():
    path = pathlib.Path(filename)
    path.write_text(content, encoding="utf-8")
    print(f"✅ {filename} を UTF-8 で書き直しました")

# ========== 他のファイルの文字化け確認 ==========
print("\n--- 文字化けチェック ---")
check_files = [
    "src/ui/pages/case_list.py",
    "src/ui/pages/case_detail.py",
    "src/ui/pages/home.py",
    "src/ui/pages/new_valuation.py",
]
for f in check_files:
    p = pathlib.Path(f)
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="replace")
        has_mojibake = "繝" in text or "縺" in text
        status = "⚠️  文字化けあり" if has_mojibake else "✅ 正常"
        print(f"{f}: {status}")
    else:
        print(f"{f}: ファイルなし")
