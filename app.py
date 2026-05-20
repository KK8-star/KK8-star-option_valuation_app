# app.py  ── 全文
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from pathlib import Path


def main() -> None:
    st.set_page_config(
        page_title="オプション評価アプリ",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── DB初期化（初回のみ） ───────────────────────────────────────────
    if "db_initialized" not in st.session_state:
        from src.data.database import get_db_manager
        get_db_manager()
        st.session_state["db_initialized"] = True

    # ── セッション初期化 ───────────────────────────────────────────────
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"
    if "detail_case_id" not in st.session_state:
        st.session_state["detail_case_id"] = None

    # ── サイドバー ─────────────────────────────────────────────────────
    with st.sidebar:

        # ロゴ
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)
        else:
            st.markdown("## 📊 オプション評価")

        st.markdown("---")

        # ナビゲーション
        nav_items = {
            "🏠 ホーム":     "home",
            "➕ 新規評価":   "new_valuation",
            "📋 ケース一覧": "case_list",
        }

        for label, page_key in nav_items.items():
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                if page_key != "case_detail":
                    st.session_state["detail_case_id"] = None
                st.session_state["current_page"] = page_key
                st.rerun()

        st.markdown("---")

        page_labels = {
            "home":          "🏠 ホーム",
            "new_valuation": "➕ 新規評価",
            "case_list":     "📋 ケース一覧",
            "case_detail":   "🔍 ケース詳細",
        }
        current = st.session_state["current_page"]
        st.caption(f"現在: {page_labels.get(current, current)}")

        st.markdown("---")
        st.caption("v0.8 · SQLite WAL")

        # コピーライト（最下部に固定）
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
            © kazama.cpa office &amp; Marleight LLC,<br>All Rights Reserved
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── ページルーティング ─────────────────────────────────────────────
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
        st.error(f"不明なページ: {page}")
        st.session_state["current_page"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()
