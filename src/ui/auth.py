import streamlit as st
import hmac
from pathlib import Path


def check_password():
    """パスワード認証を行う。認証済みの場合はTrueを返す"""

    def password_entered():
        input_pw = st.session_state["password"].encode("utf-8")
        correct_pw = st.secrets["auth"]["password"].encode("utf-8")

        if hmac.compare_digest(input_pw, correct_pw):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # 既に認証済みの場合
    if st.session_state.get("password_correct", False):
        return True

    # サイドバーにロゴ表示
    with st.sidebar:
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)
        st.markdown(
            '<div style="padding:0.5rem 0 1rem;">'
            '<h2 style="margin:0;font-size:1.3rem;">&#128202; オプション評価</h2>'
            '<p style="margin:0;font-size:0.78rem;color:#888;">'
            '非上場企業向け公正価値算定システム</p></div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("(c) 風間会計事務所")
        st.caption("v0.3.3 | Python 3.12")

    # メインエリア：ログインフォーム
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)
        st.markdown(
            "<h2 style='text-align:center;'>&#128274; ログイン</h2>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center;color:#888;'>非上場企業向けオプション評価システム</p>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.text_input(
            "パスワードを入力してください",
            type="password",
            on_change=password_entered,
            key="password"
        )
        if "password_correct" in st.session_state:
            if not st.session_state["password_correct"]:
                st.error("パスワードが違います")

    return False
