import streamlit as st
import hmac

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

    # パスワード入力フォーム
    st.title("🔐 ログイン")
    st.markdown("### 非上場会社向けオプション評価システム")
    st.text_input(
        "パスワードを入力してください",
        type="password",
        on_change=password_entered,
        key="password"
    )

    if "password_correct" in st.session_state:
        st.error("❌ パスワードが違います")

    return False
