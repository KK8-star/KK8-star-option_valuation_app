import streamlit as st
import hmac


def check_password():
    def password_entered():
        input_pw = st.session_state["password"].encode("utf-8")
        correct_pw = st.secrets["auth"]["password"].encode("utf-8")
        if hmac.compare_digest(input_pw, correct_pw):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    with st.sidebar:
        st.markdown("Option Valuation System")
        st.divider()
        st.caption("(C) kazama.cpaoffice & Marleight LLC, All Rights Reserved")
        st.caption("v0.8 | Python 3.12")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Login")
        st.text_input("Enter password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            if not st.session_state["password_correct"]:
                st.error("Incorrect password")

    return False
