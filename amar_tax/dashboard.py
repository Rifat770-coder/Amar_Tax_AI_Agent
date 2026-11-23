"""Presentation-only components for the tax dashboard."""
from html import escape

import streamlit as st


def section_heading(title, subtitle="", anchor=""):
    st.markdown(f'<div class="section-heading" id="{escape(anchor)}"><div><h2>{escape(title)}</h2>'
                f'<p>{escape(subtitle)}</p></div></div>', unsafe_allow_html=True)


def render_overview(report, navigate=None):
    section_heading("Your tax overview", "Annual tax summary · 2026–27", "overview")
    fields = [("Net payable tax", "net_tax", "After rebate & minimum tax"),
              ("Gross tax", "gross_tax", "Calculated from tax slabs"),
              ("Investment rebate", "rebate", "Eligible investment benefit"),
              ("Total annual income", "total_income", "All income sources combined")]
    with st.container(key="overview_metrics"):
        cols = st.columns(4, gap="small")
    for column, (label, attribute, description) in zip(cols, fields):
        with column:
            with st.container(border=True, key="kpi_" + attribute):
                value = f"৳ {getattr(report.calculation, attribute):,.2f}" if report else "—"
                st.metric(label, value)
                st.caption(description)
                if report:
                    st.button("View report", key="view_report_"+attribute, icon=":material/arrow_forward:",
                              use_container_width=True, on_click=navigate, args=("Tax report",) if navigate else None)


def render_analytics(report, navigate=None):
    section_heading("Income and tax breakdown", "Figures from your latest report", "analytics")
    a, b = st.columns([1, 2], gap="medium")
    with a:
        with st.container(border=True, key="tax_gauge"):
            st.markdown('<div class="panel-title">Net tax as a share of gross tax</div>', unsafe_allow_html=True)
            gross = report.calculation.gross_tax if report else 0
            net = report.calculation.net_tax if report else 0
            if gross:
                ratio = float(net / gross * 100)
                st.markdown(f'<div class="tax-ratio"><strong>{ratio:,.0f}%</strong>'
                            f'<meter aria-hidden="true" min="0" max="{max(100, ratio)}" value="{ratio}"></meter></div>',
                            unsafe_allow_html=True)
            else:
                st.caption("Share unavailable because gross slab tax is zero")
            st.caption("Net tax may include a location-based minimum.")
            st.button("Review your profile →", key="review_profile", use_container_width=True,
                      on_click=navigate, args=("Taxpayer profile",) if navigate else None)
    with b:
        with st.container(border=True, key="income_chart"):
            st.markdown('<div class="panel-title">Income breakdown · BDT per year</div>', unsafe_allow_html=True)
            kinds = [("salaried","Salary"),("freelancer","Freelance"),("business","Business"),
                     ("landlord","Rent"),("investor","Investment"),("other","Other")]
            values = {kind:0 for kind,_ in kinds}
            if report:
                for source in report.profile.income_sources:
                    values[source.kind] += float(source.amount)
            maximum = max(values.values()) or 1
            entries = []
            for kind, title in kinds:
                width = values[kind] / maximum * 100
                amount = f"৳ {values[kind]:,.2f}"
                entries.append(
                    f'<div class="income-entry" title="{title}: ৳ {values[kind]:,.0f}">'
                    f'<span>{title}</span><span class="income-amount">{amount}</span>'
                    f'<span class="income-track" aria-hidden="true"><span class="income-fill" '
                    f'style="width:{width:.6f}%"></span></span></div>'
                )
            st.markdown('<div class="income-chart">' + "".join(entries) + '</div>', unsafe_allow_html=True)
            st.caption("Bars are scaled to the largest income source.")


def render_calculation(report):
    section_heading("Income tax slabs", "Taxable income and tax charged at each rate", "calculation")
    with st.container(border=True, key="slab_panel"):
        if not report:
            st.caption("Generate a report to see the slab amounts, applicable rates and tax.")
            return
        render_slab_table(report)
        st.caption(f"Location minimum: ৳ {report.classification.minimum_tax:,.2f} · Applied minimum: ৳ {report.calculation.minimum_tax_applied:,.2f}")


def render_slab_table(report):
    rows = "".join(f'<tr><td>Slab {i}</td><td>৳&nbsp;{slab.amount:,.2f}</td>'
                   f'<td>{(slab.rate * 100).normalize():f}%</td><td>৳&nbsp;{slab.tax:,.2f}</td></tr>'
                   for i, slab in enumerate(report.calculation.slabs, 1))
    if not rows:
        rows = '<tr><td colspan="4">No income above the tax-free threshold.</td></tr>'
    st.markdown('<div class="slab-scroll" tabindex="0" role="region" aria-label="Income tax slabs">'
                '<table class="slab-table"><thead><tr><th scope="col">Income band</th>'
                '<th scope="col">Taxable portion</th><th scope="col">Rate</th>'
                '<th scope="col">Tax amount</th></tr></thead><tbody>'
                + rows + '</tbody></table></div>', unsafe_allow_html=True)
