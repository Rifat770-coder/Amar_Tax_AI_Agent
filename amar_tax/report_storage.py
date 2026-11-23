"""Restore the latest report from the current browser tab after a refresh."""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

from .database import load_database
from .models import Report
from .report import render_markdown

_storage = components.declare_component(
    "amar_tax_report_storage",
    path=str(Path(__file__).parent / "data" / "report_storage"),
)


def sync_browser_report():
    session = st.session_state
    report = session.get("report")
    write = session.get("report_storage_initialized", False) or report is not None
    access_scope = "protected" if session.get("access_granted") else "public"
    result = _storage(
        storage_key=f"amar-tax:report:v1:{access_scope}",
        write=write,
        report=report.model_dump(mode="json") if report is not None else None,
        key="browser_report_storage",
    )
    if not isinstance(result, dict):
        return
    if result.get("unavailable"):
        if report is not None:
            st.caption("এই ব্রাউজারে রিপোর্ট সংরক্ষণ করা যায়নি। রিফ্রেশের আগে রিপোর্ট ডাউনলোড করুন।")
        return
    if write:
        return

    session.report_storage_initialized = True
    saved = result.get("report")
    if saved is None:
        return
    try:
        restored = Report.model_validate(saved)
    except ValidationError:
        return
    db, _ = load_database()
    session.markdown = render_markdown(restored, db)
    session.profile_draft = restored.profile.model_dump(mode="json")
    session.report = restored
    st.rerun()
