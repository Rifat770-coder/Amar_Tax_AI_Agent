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
    cols = st.columns(4, gap="small")
    for column, (label, attribute, description) in zip(cols, fields):
        with column:
            with st.container(border=True, key="kpi_" + attribute):
                value = f"৳ {getattr(report.calculation, attribute):,.2f}" if report else "—"
                st.metric(label, value)
                st.caption(description if report else "Generate a report to see your result")
                st.button("View report ↗", key="view_report_"+attribute, disabled=report is None,
                          use_container_width=True, on_click=navigate, args=("Tax report",) if navigate else None)


def render_analytics(report, navigate=None):
    section_heading("Tax report analytics", "A clear view of your income and tax", "analytics")
    a, b = st.columns([0.85, 1.65], gap="small")
    with a:
        with st.container(border=True, key="tax_gauge"):
            st.markdown('<div class="panel-title">Tax after rebate <span>◌</span></div>', unsafe_allow_html=True)
            gross = report.calculation.gross_tax if report else 0
            net = report.calculation.net_tax if report else 0
            ratio = min(100, float(net / gross * 100)) if gross else 0
            label = f"{float(net / gross * 100):.0f}%" if gross else "0%" if report else "—"
            gauge = f'''<div class="gauge-wrap"><svg viewBox="0 0 240 145" role="img" aria-label="Net tax as percentage of gross tax">
<path d="M 26 119 A 94 94 0 0 1 214 119" fill="none" stroke="#edf1fa" stroke-width="29"/>
<path d="M 26 119 A 94 94 0 0 1 214 119" fill="none" stroke="#2764ef" stroke-width="29" pathLength="100" stroke-dasharray="{ratio} 100"/>
<path d="M 47 119 A 73 73 0 0 1 193 119" fill="none" stroke="#b9cdfb" stroke-width="2" stroke-dasharray="1 2"/>
<text x="120" y="103" text-anchor="middle" font-size="31" font-weight="700" fill="#172337">{label}</text>
<text x="120" y="123" text-anchor="middle" font-size="10" fill="#7c8798">of gross tax payable</text></svg></div>'''
            st.markdown(gauge, unsafe_allow_html=True)
            st.markdown("**Your tax, at a glance**" if report else "**Your report starts here**")
            st.caption("Net tax compared with gross slab tax. The minimum-tax rule may apply." if report else
                       "আপনার তথ্য পূরণ করে রিপোর্ট তৈরি করুন। ফলাফল ও হিসাব এখানে দেখাবে।")
            st.button("Review your profile →", key="review_profile", use_container_width=True,
                      on_click=navigate, args=("Taxpayer profile",) if navigate else None)
    with b:
        with st.container(border=True, key="income_chart"):
            st.markdown('<div class="panel-title">Income breakdown <span class="chart-legend"><i></i> Annual income · BDT</span></div>', unsafe_allow_html=True)
            kinds = [("salaried","Salary"),("freelancer","Freelance"),("business","Business"),
                     ("landlord","Rent"),("investor","Investment"),("other","Other")]
            values = {kind:0 for kind,_ in kinds}
            if report:
                for source in report.profile.income_sources:
                    values[source.kind] += float(source.amount)
            maximum = max(values.values()) or 1
            columns = []
            for kind, title in kinds:
                height = round(values[kind] / maximum * 14)
                cells = "".join(f'<span class="income-cell{" filled" if row < height else ""}"></span>' for row in reversed(range(14)))
                amount = f"৳ {values[kind]:,.0f}" if report else "—"
                columns.append(f'<div class="income-column" title="{title}: {amount}"><div class="income-cells">{cells}</div><strong>{title}</strong><small>{amount}</small></div>')
            st.markdown('<div class="income-chart">' + "".join(columns) + '</div>', unsafe_allow_html=True)
            st.caption("প্রতিটি উৎসের বার্ষিক আয়। রিপোর্টের তথ্য থেকেই চার্ট তৈরি হয়।" if report else
                       "Your income sources will appear after you generate a report.")


def render_calculation(report):
    section_heading("Calculation details", "Transparent, slab-by-slab calculation", "calculation")
    with st.container(border=True, key="slab_panel"):
        if not report:
            st.caption("Generate a report to see the slab amounts, applicable rates and tax.")
            return
        rows = "".join(f'<tr><td>Slab {i}</td><td>৳ {s.amount:,.2f}</td><td>{s.rate * 100:g}%</td><td>৳ {s.tax:,.2f}</td></tr>'
                       for i,s in enumerate(report.calculation.slabs,1))
        if not rows:
            rows = '<tr><td colspan="4">No income above the tax-free threshold.</td></tr>'
        st.markdown('<table class="slab-table"><thead><tr><th>Income band</th><th>Taxable portion</th><th>Rate</th><th>Tax amount</th></tr></thead><tbody>'
                    + rows + '</tbody></table>', unsafe_allow_html=True)
        st.caption(f"Location minimum: ৳ {report.classification.minimum_tax:,.2f} · Applied minimum: ৳ {report.calculation.minimum_tax_applied:,.2f}")
