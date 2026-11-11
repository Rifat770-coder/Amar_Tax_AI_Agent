"""Optional access code; an unset password allows public access."""
import hashlib
import hmac
import os

import streamlit as st


def require_access():
    password = os.getenv("AMAR_TAX_APP_PASSWORD", "")
    if not password:
        return
    fingerprint = hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get("access_granted") == fingerprint:
        return

    def check_password():
        entered = st.session_state.pop("access_password", "")
        if hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state.access_granted = fingerprint
            st.session_state.pop("access_failed", None)
        else:
            st.session_state.access_failed = True

    st.title("Amar Tax")
    st.caption("Enter the app access code shared by the project owner. This is not your API key.")
    with st.form("app_access"):
        st.text_input("App access code", type="password", key="access_password")
        st.form_submit_button("Open dashboard", on_click=check_password, type="primary")
    if st.session_state.get("access_failed"):
        st.error("Incorrect access code.")
    st.stop()
