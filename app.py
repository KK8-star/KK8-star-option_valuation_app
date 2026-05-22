# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from pathlib import Path


# ====================================================
# ログイン設定
# ====================================================
LOGIN_USERS = dict(st.secrets.get("users", {}))


def show_login_page() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown("... オプション評価")

        st.markdown("### ログイン")
        st.markdown("---")

        username = st.text_input("ユーザー名", placeholder="ユーザー名を入力")
        password = st.text_input("パスワード", type="password", placeholder="パスワードを入力")

        if st.button("ログイン", use_container_width=True, type="primary"):
            if username in LOGIN_USERS and LOGIN_USERS[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません")

        st.markdown("---")
        st.caption("© kazama.cpa office & Marleight LLC.,All Rights Reserved.")


def main() -> None:

    # ====================================================
    # ログインチェック
    # ====================================================
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.set_page_config(
            page_title="オプション評価アプリ - ログイン",
            page_icon="📊",
            layout="centered",
        )
        show_login_page()
        return

    st.set_page_config(
        page_title="オプション評価アプリ",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ====================================================
    # DB初期化（初回のみ）
    # ====================================================
    if "db_initialized" not in st.session_state:
        from src.data.database import get_db_manager
        get_db_manager()
        st.session_state["db_initialized"] = True

    # ====================================================
    # セッション初期化
    # ====================================================
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"
    if "detail_case_id" not in st.session_state:
        st.session_state["detail_case_id"] = None

    # ====================================================
    # サイドバー
    # ====================================================
    with st.sidebar:

        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown("... オプション評価")

        st.markdown("---")

        nav_items = {
            "ホーム":       "home",
            "新規評価":     "new_valuation",
            "ケース一覧":   "case_list",
        }

        for label, page_key in nav_items.items():
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                if page_key != "case_detail":
                    st.session_state["detail_case_id"] = None
                st.session_state["current_page"] = page_key
                st.rerun()

        st.markdown("---")

        page_labels = {
            "home":          "ホーム",
            "new_valuation": "新規評価",
            "case_list":     "ケース一覧",
            "case_detail":   "ケース詳細",
        }
        current = st.session_state["current_page"]
        st.caption(f"現在: {page_labels.get(current, current)}")

        st.markdown("---")

        username = st.session_state.get("username", "")
        st.caption(f"ユーザー: {username}")
        if st.button("ログアウト", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.rerun()

        st.markdown("---")
        st.caption("v1.0")

        st.markdown(
            """
            <div style='
                position: fixed;
                bottom: 1rem;
                left: 0;
                width: 18rem;
                padding: 0 1rem;
                font-size: 0.65rem;
                color: #888;
                line-height: 1.4;
            '>
            © kazama.cpa office &amp; Marleight LLC.,All Rights Reserved.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ====================================================
    # ページルーティング
    # ====================================================
    page = st.session_state["current_page"]

    if page == "home":
        from src.ui.pages.home import show
        show()

    elif page == "new_valuation":
        from src.ui.pages.new_valuation import show
        show()

    elif page == "case_list":
        from src.ui.pages.case_list import show
        show()

    elif page == "case_detail":
        if st.session_state.get("detail_case_id") is None:
            st.session_state["current_page"] = "case_list"
            st.rerun()
        from src.ui.pages.case_detail import show
        show()

    else:
        st.warning(f"不明なページ: {page}")
        st.session_state["current_page"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()


