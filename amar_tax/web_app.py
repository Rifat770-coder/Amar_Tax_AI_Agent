"""Stateful dashboard navigation; tax and provider logic stay in their services."""
import hashlib
import os
import time
from html import escape
from importlib.resources import files

import streamlit as st
from pydantic import ValidationError

from . import api_status, service, settings
from .connection import server_connection
from .dashboard import render_overview, render_analytics, render_calculation, section_heading
from .database import load_database
from .engine import run_offline
from .models import Profile
from .report import render_markdown
from .runner import crew_timeout
from .access import require_access

VIEWS = {"Dashboard":("dashboard","▦"), "Income analytics":("analytics","◴"),
         "Taxpayer profile":("profile","♙"), "Tax report":("report","▤"),
         "Tax calculation":("calculation","▥"), "Documents checklist":("documents","▣")}


def navigate(view):
    st.session_state.current_view = view
    st.query_params["view"] = VIEWS[view][0]


def render_connection(recheck):
    key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("AMAR_TAX_MODEL", "openai/gpt-4o-mini")
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1"
    error = None
    try:
        server_connection()
    except ValueError:
        error = api_status.APIStatus(False, "সার্ভারের .env-এ Base URL, API key ও Model ID সঠিকভাবে সেট করুন।")
    fingerprint = (hashlib.sha256(key.encode()).hexdigest(), model, base)
    previous = st.session_state.get("api_generation_issue")
    if recheck or (previous and previous[0] != fingerprint):
        st.session_state.pop("api_generation_issue", None)
    cached = st.session_state.get("api_connection")
    if recheck or not cached or cached[0] != fingerprint or time.monotonic() - cached[1] >= 60:
        with st.spinner("API connection যাচাই হচ্ছে…"):
            status = error or api_status.check_api_connection(key, model, base)
        st.session_state.api_connection = (fingerprint, time.monotonic(), status)
    else:
        status = cached[2]
    issue = st.session_state.get("api_generation_issue")
    state_class = "connected" if status.connected and not issue else "disconnected"
    label = "AI unavailable" if issue else "API connected" if status.connected else "API not connected"
    detail = issue[1].detail if issue else status.detail
    st.markdown(f'<div class="api-status {state_class}" role="status"><span class="api-light" aria-hidden="true"></span>'
                f'<div><strong>{label}</strong><small>{escape(detail)}</small></div></div>', unsafe_allow_html=True)
    st.caption("সর্বশেষ connection check। Model access ও generation availability এক নাও হতে পারে।")
    if issue and "credits" in issue[1].detail:
        st.markdown("[OpenAI API Billing খুলুন](https://platform.openai.com/settings/organization/billing/)")
    return fingerprint, error


def render_downloads(report):
    a, b = st.columns(2)
    a.download_button("↓ Markdown রিপোর্ট", st.session_state.markdown, file_name="amar-tax-report.md", mime="text/markdown", use_container_width=True)
    b.download_button("↓ JSON রিপোর্ট", report.model_dump_json(indent=2), file_name="amar-tax-report.json", mime="application/json", use_container_width=True)


def render_report(report):
    section_heading("Tax readiness report", "সর্বশেষ তৈরি করা প্রোফাইলের সম্পূর্ণ রিপোর্ট", "tax-report")
    (st.success if report.review.status == "Passed" else st.warning)(
        "✓ Passed · যাচাই সম্পন্ন" if report.review.status == "Passed" else "⚠ Flagged · সতর্কবার্তা দেখুন")
    st.caption("হিসাবের মোড: " + report.mode)
    tabs = st.tabs(["সারসংক্ষেপ", "কাগজপত্র", "সম্পূর্ণ রিপোর্ট"])
    with tabs[0]:
        st.write("**করদাতার শ্রেণি / Category:** " + report.classification.category)
        st.write(f"**করমুক্ত সীমা:** ৳ {report.classification.threshold:,.2f}")
        st.write("**রিটার্ন দাখিল বাধ্যতামূলক:** " + ("হ্যাঁ / Yes" if report.classification.filing_mandatory else "না / No"))
        for finding in report.review.findings:
            st.warning(finding)
        st.markdown("### বাংলা সারসংক্ষেপ")
        st.markdown(st.session_state.markdown.split("## বাংলা সারসংক্ষেপ\n\n")[1])
    with tabs[1]:
        for i, document in enumerate(report.documents.checklist, 1):
            st.write(f"{i}. {document}")
    with tabs[2]:
        st.markdown(st.session_state.markdown)
    render_downloads(report)


def render_documents(report):
    section_heading("Your filing checklist", "Documents tailored to your profile and income sources", "documents")
    a, b = st.columns([1.65, 1], gap="small")
    with a:
        with st.container(border=True):
            st.markdown("**Documents to prepare**")
            for document in report.documents.checklist:
                st.write("◻ " + document)
    with b:
        with st.container(border=True):
            st.markdown("**Filing snapshot**")
            st.write("Category: " + report.classification.category)
            st.write(f"Tax-free threshold: ৳ {report.classification.threshold:,.2f}")
            st.write("Filing mandatory: " + ("Yes" if report.classification.filing_mandatory else "No"))
            st.write("Independent filing: " + ("Allowed" if report.classification.can_file_independently else "Guardian assistance required"))


def render_empty():
    st.info("এখনও রিপোর্ট তৈরি করা হয়নি। প্রথমে আপনার প্রোফাইল পূরণ করে রিপোর্ট তৈরি করুন।")
    st.button("Create your first report →", key="first_report", type="primary", on_click=navigate, args=("Taxpayer profile",))


def render_profile(mode, fingerprint, config_error):
    section_heading("Prepare your tax report", "১. প্রোফাইল পূরণ করুন → ২. রিপোর্ট তৈরি করুন → ৩. Dashboard-এ ফলাফল দেখুন", "profile")
    draft = st.session_state.get("profile_draft", {})
    income_values = {item["kind"]:float(item["amount"]) for item in draft.get("income_sources", [])}
    left, right = st.columns([1.3, 0.8], gap="medium")
    with left:
        st.caption("নিজের তথ্য দিন। উদাহরণের তথ্য দিয়ে শুরু করতে পারেন।")
        with st.form("tax_profile"):
            a, b = st.columns(2)
            age = a.number_input("বয়স / Age", min_value=0, max_value=120, value=draft.get("age",34), step=1)
            genders = ["female","male","other"]
            gender = b.selectbox("লিঙ্গ / Gender", genders, index=genders.index(draft.get("gender","female")),
                                format_func=lambda x:{"female":"নারী / Female","male":"পুরুষ / Male","other":"অন্যান্য / Other"}[x])
            profession = st.text_input("পেশা / Profession", value=draft.get("profession","software engineer"), max_chars=100,
                                       help="ইংরেজিতে পেশা লিখুন, যেমন salaried, freelancer বা business।")
            locations = {"dhaka_chattogram_city":"ঢাকা / চট্টগ্রাম সিটি", "other_city_corporation":"অন্যান্য সিটি করপোরেশন", "rest_of_country":"সিটি করপোরেশনের বাইরে"}
            location = st.selectbox("অবস্থান / Location", list(locations), index=list(locations).index(draft.get("location","dhaka_chattogram_city")), format_func=locations.get)
            st.markdown('<div class="form-section">আয় ও বিনিয়োগ · বাংলাদেশি টাকা (৳)</div>', unsafe_allow_html=True)
            st.caption("পুরো বছরের আয় লিখুন, মাসিক নয়। যে উৎসে আয় নেই, ০ রাখুন। একই আয় দুবার দেবেন না।")
            amounts = {}
            labels = {"salaried":"বেতন / Salary", "freelancer":"ফ্রিল্যান্সিং / Freelance", "business":"ব্যবসা / Business", "landlord":"বাড়িভাড়া / Rent", "investor":"বিনিয়োগ আয় / Investment income", "other":"অন্যান্য / Other income"}
            cols = st.columns(2)
            for i,(kind,label) in enumerate(labels.items()):
                default = 1200000.0 if kind == "salaried" else 300000.0 if kind == "freelancer" else 0.0
                amounts[kind] = cols[i%2].number_input(label,min_value=0.0,max_value=9999999999999.0,
                    value=income_values.get(kind,default),step=1000.0,format="%.2f")
            investment = st.number_input("মোট বিনিয়োগ / Investment (BDT)",min_value=0.0,max_value=9999999999999.0,
                                        value=float(draft.get("investment",200000)),step=1000.0,format="%.2f",help="যেমন DPS ও সঞ্চয়পত্রে বিনিয়োগের মোট পরিমাণ।")
            st.markdown('<div class="form-section">করদাতার অতিরিক্ত তথ্য</div>',unsafe_allow_html=True)
            a,b = st.columns(2)
            has_tin = a.checkbox("আমার TIN আছে",value=draft.get("has_tin",True))
            independent = b.checkbox("নিজে রিটার্ন দাখিল করব",value=draft.get("wants_independent_filing",True))
            disabled = a.checkbox("প্রতিবন্ধী করদাতা",value=draft.get("disabled",False))
            freedom = b.checkbox("মুক্তিযোদ্ধা করদাতা",value=draft.get("freedom_fighter",False))
            claims = st.checkbox("আমার দাবি: রিটার্ন দাখিল বাধ্যতামূলক",value=draft.get("claims_required_to_file",False))
            submitted = st.form_submit_button("রিপোর্ট তৈরি করুন →",type="primary",use_container_width=True)
    with right:
        with st.container(border=True):
            st.markdown("### আপনার পরবর্তী ধাপ")
            st.markdown("1. প্রোফাইল ও বার্ষিক আয়ের তথ্য দিন।\n2. **রিপোর্ট তৈরি করুন** চাপুন।\n3. তৈরি হলে স্বয়ংক্রিয়ভাবে **Dashboard** খুলবে।")
            st.caption("এরপর sidebar থেকে report, analytics, calculation ও documents খুলতে পারবেন।")
            if "report" in st.session_state:
                st.info("আগের রিপোর্ট আছে। নতুন রিপোর্ট তৈরি করলে Dashboard-এর ফলাফল আপডেট হবে।")
    if not submitted:
        return
    data = dict(age=int(age),gender=gender,profession=profession,location=location,has_tin=has_tin,
                income_sources=[{"kind":k,"amount":str(v)} for k,v in amounts.items()],investment=str(investment),
                wants_independent_filing=independent,disabled=disabled,freedom_fighter=freedom,claims_required_to_file=claims)
    st.session_state.profile_draft = data
    st.session_state.pop("report",None)
    st.session_state.pop("markdown",None)
    try:
        profile = Profile.model_validate(data)
        db,source = load_database()
        message = f"AI রিপোর্ট প্রস্তুত হচ্ছে… সর্বোচ্চ {crew_timeout()} সেকেন্ড।" if mode.startswith("CrewAI") else "আপনার রিপোর্ট প্রস্তুত হচ্ছে…"
        with st.spinner(message):
            if mode.startswith("CrewAI"):
                saved_issue = st.session_state.get("api_generation_issue")
                report,issue = service.generate_crew_report(profile,db,source,saved_issue[1] if saved_issue else config_error)
                if issue:
                    st.session_state.api_generation_issue = (fingerprint,issue)
                else:
                    st.session_state.pop("api_generation_issue",None)
            else:
                report = run_offline(profile,db,source)
        st.session_state.report = report
        st.session_state.markdown = render_markdown(report,db)
        navigate("Dashboard")
        st.rerun()
    except ValidationError as exc:
        st.error("প্রোফাইলের তথ্য ঠিক করুন।")
        for error in exc.errors(include_url=False):
            st.warning(f"{'.'.join(str(x) for x in error['loc']) or 'Profile'}: {error['msg']}")
    except Exception:
        st.error("রিপোর্ট তৈরি হয়নি। API configuration পরীক্ষা করুন অথবা Offline mode ব্যবহার করুন।")


def main():
    settings.load_project_env()
    st.set_page_config(page_title="Amar Tax · আপনার কর প্রস্তুতি",page_icon="🧾",layout="wide")
    require_access()
    st.markdown("<style>"+files("amar_tax").joinpath("data/dashboard.css").read_text(encoding="utf-8")+"</style>",unsafe_allow_html=True)
    if "current_view" not in st.session_state:
        query = st.query_params.get("view","dashboard")
        st.session_state.current_view = next((name for name,(slug,_) in VIEWS.items() if slug == query),"Dashboard")
    view = st.session_state.current_view
    if view not in VIEWS:
        view = st.session_state.current_view = "Dashboard"
    with st.sidebar:
        st.markdown('<div class="sidebar-profile"><div class="avatar">AT</div><div><strong>Amar Tax<span class="profile-badge">2026</span></strong><small>Personal tax workspace</small></div></div><div class="nav-label">WORKSPACE</div>',unsafe_allow_html=True)
        with st.container(key="workspace_navigation"):
            for name,(slug,icon) in VIEWS.items():
                st.button(icon+"  "+name,key="nav_"+slug,type="primary" if view == name else "secondary",
                          use_container_width=True,on_click=navigate,args=(name,))
        st.divider()
        st.markdown('<div class="nav-label">CALCULATION MODE</div>',unsafe_allow_html=True)
        mode = st.radio("হিসাবের মোড",["Offline · Local DB","CrewAI · AI agents"],key="calculation_mode")
        recheck = False
        if mode.startswith("CrewAI"):
            st.caption("API settings: Server / .env")
            st.info("রিপোর্ট তৈরির সময় প্রোফাইল নির্বাচিত API provider-এর কাছে পাঠানো হবে।")
            recheck = st.button("↻ API আবার যাচাই করুন",use_container_width=True)
        else:
            st.caption("API key ছাড়াই স্থানীয় নিয়ম অনুযায়ী হিসাব।")
        st.markdown('<div class="side-note"><strong>Prepare → Generate → Review</strong><p>প্রথমে প্রোফাইল পূরণ করুন। তৈরি করা রিপোর্টের ফলাফল Dashboard-এ দেখুন।</p></div>',unsafe_allow_html=True)
    with st.container(key="page_header"):
        title_column, action_column = st.columns([5,1], vertical_alignment="center", gap="medium")
        with title_column:
            st.markdown(f'<div class="topbar"><div><p class="breadcrumb">WORKSPACE / PERSONAL TAX</p><h1>{escape(view)}</h1></div></div>',unsafe_allow_html=True)
        with action_column:
            if view == "Taxpayer profile":
                st.button("← Dashboard",key="header_dashboard",on_click=navigate,args=("Dashboard",),use_container_width=True)
            else:
                st.button("Create report ↗",key="create_report",type="primary",on_click=navigate,args=("Taxpayer profile",),use_container_width=True)
    fingerprint,config_error = render_connection(recheck) if mode.startswith("CrewAI") else (None,None)
    report = st.session_state.get("report")
    if view == "Taxpayer profile":
        render_profile(mode,fingerprint,config_error)
    elif view == "Dashboard":
        render_overview(report,navigate)
        if report is None:
            render_empty()
        else:
            (st.success if report.review.status == "Passed" else st.warning)(
                "✓ Report ready · Passed" if report.review.status == "Passed" else "⚠ Report ready · Flagged — সতর্কবার্তা দেখুন")
            st.caption("সর্বশেষ তৈরি করা রিপোর্ট · " + report.mode)
            render_analytics(report,navigate)
            a,b = st.columns(2)
            a.button("সম্পূর্ণ রিপোর্ট দেখুন →",key="open_full_report",on_click=navigate,args=("Tax report",),use_container_width=True)
            b.button("প্রোফাইল পরিবর্তন করুন",key="edit_profile",on_click=navigate,args=("Taxpayer profile",),use_container_width=True)
            render_downloads(report)
    elif report is None:
        render_empty()
    elif view == "Income analytics":
        render_analytics(report,navigate)
    elif view == "Tax report":
        render_report(report)
    elif view == "Tax calculation":
        render_calculation(report)
    elif view == "Documents checklist":
        render_documents(report)
