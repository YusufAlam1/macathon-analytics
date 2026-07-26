"""
Main Dashboard Orchestrator
Handles layout, UI, and coordinates between data layer (queries) and visualization layer
"""
import os
from contextlib import nullcontext

import streamlit as st
from queries import (
    load_attribution_data,
    load_country_data,
    load_date_data,
    load_programs_data,
    load_age_data,
    load_acceptance_data,
    load_response_length_data,
    load_experience_data,
    load_prev_hacker_data,
    load_schools_data,
    load_funnel_data,
)
from visualizations import (
    COLORS,
    FONT_FAMILY,
    PLOTLY_CONFIG,
    create_trend_chart,
    create_split_bar,
    create_hbar,
    create_column_chart,
    create_pie_chart,
    create_funnel_chart,
    create_response_hist,
)

# ---------------------------------------------------------------------------
# Filtered-dashboard feature (isolated under filtered/ — see the plan at
# .claude/plans/partitioned-wobbling-sun.md). Fully separable: removing this
# import block + the two sections marked "FILTERED FEATURE" below reverts
# the dashboard to its pre-filter state with zero other changes needed.
# ---------------------------------------------------------------------------
from filtered.loaders import (
    load_applicants_wide, EXPERIENCE_ORDER, ACADEMIC_ORDER,
    COUNTRY_ORDER, PROGRAM_ORDER,
)
from filtered.filters import render_filter_sidebar, apply_filters, FUNNEL_DIM_COL
from filtered.aggregations import (
    agg_count, funnel_counts, acceptance_counts, trend_counts,
    schools_counts, attribution_counts,
)

# Page configuration
st.set_page_config(
    page_title="Mac-a-Thon Applications",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light, Google-style chrome
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Hide default Streamlit elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* --- Rerun-flash dampening (feature A3) ---------------------------------
       On every widget interaction Streamlit reruns the whole page. By default
       it shows a top "running" status widget and fades stale content while the
       new content renders — that's the pause+dim flash on each filter change.
       We hide the status widget and keep content at full opacity mid-rerun, and
       soften what remains with a short cross-fade so charts swap gently rather
       than snapping. (This does NOT tween the bars — that would be a separate
       change — it just removes the jarring page-level flash.) */
    [data-testid="stStatusWidget"] {{ display: none !important; }}
    /* Streamlit dims stale elements with reduced opacity during a rerun; pin
       it back to full so there's no gray-out. */
    [data-stale="true"] {{ opacity: 1 !important; }}
    /* Gentle fade-in for freshly rendered blocks (esp. Plotly charts) so the
       swap reads as a soft transition instead of a hard snap. */
    [data-testid="stPlotlyChart"], [data-testid="stMetric"] {{
        animation: flt-fade 220ms ease-out;
    }}
    @keyframes flt-fade {{ from {{ opacity: 0.55; }} to {{ opacity: 1; }} }}

    html, body, [class*="css"] {{
        font-family: {FONT_FAMILY};
    }}

    .main .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Header */
    .header-title {{
        font-size: 1.9rem;
        font-weight: 700;
        color: {COLORS['ink']};
        letter-spacing: -0.4px;
        margin: 0;
        line-height: 1.2;
    }}
    .header-sub {{
        font-size: 0.95rem;
        color: {COLORS['ink_2']};
        margin: 0.15rem 0 0 0;
    }}

    /* Section headers */
    h2 {{
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: {COLORS['ink']} !important;
        letter-spacing: -0.2px;
        padding-bottom: 0.25rem;
    }}
    h3 {{
        font-size: 1.0rem !important;
        font-weight: 600 !important;
        color: {COLORS['ink']} !important;
    }}

    /* KPI hero row: fixed-size cards inside one flush wrapping rectangle */
    .kpi-row {{
        display: flex;
        gap: 1rem;
        width: 100%;
        margin: 0.5rem 0 0.5rem 0;
    }}
    .kpi-card {{
        flex: 1 1 0;
        min-height: 118px;
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1rem 1.25rem;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }}
    .kpi-label {{
        color: {COLORS['ink_2']};
        font-size: 0.82rem;
        font-weight: 500;
        margin-bottom: 0.35rem;
    }}
    .kpi-value {{
        color: {COLORS['ink']};
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        line-height: 1.1;
    }}
    .kpi-sub {{
        color: {COLORS['ink_2']};
        font-size: 0.85rem;
        margin-top: 0.4rem;
    }}

    /* Metric cards: flat white card, hairline border */
    [data-testid="stMetric"] {{
        background-color: #ffffff;
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }}
    [data-testid="stMetric"] label {{
        color: {COLORS['ink_2']};
        font-size: 0.82rem;
        font-weight: 500;
    }}
    [data-testid="stMetricValue"] {{
        color: {COLORS['ink']};
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    [data-testid="stMetricDelta"] {{
        color: {COLORS['ink_2']};
        font-size: 0.85rem;
    }}

    /* Dividers: hairline, quiet */
    hr {{
        border-color: #eceef1 !important;
        margin: 1.75rem 0 !important;
    }}

    /* Download buttons: ghost style */
    [data-testid="stDownloadButton"] button {{
        background: transparent;
        color: {COLORS['ink_2']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        font-size: 0.8rem;
        padding: 0.25rem 0.75rem;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        border-color: {COLORS['blue']};
        color: {COLORS['blue']};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        border-right: 1px solid #eceef1;
    }}

    /* Charts flush inside their columns */
    [data-testid="stPlotlyChart"] {{
        padding: 0 !important;
        margin: 0 !important;
    }}
    </style>
""", unsafe_allow_html=True)


def kpi_row(cards):
    """Render KPI cards as one flex container so every card is the same fixed
    height and the row sits flush inside a single wrapping rectangle.
    Each card is (label, value, sub) - sub may be None."""
    items = []
    for label, value, sub in cards:
        sub_html = f'<div class="kpi-sub">↑ {sub}</div>' if sub else '<div class="kpi-sub">&nbsp;</div>'
        items.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'{sub_html}'
            f'</div>'
        )
    st.markdown(f'<div class="kpi-row">{"".join(items)}</div>', unsafe_allow_html=True)


def main():
    # ---------- Header ----------
    col_logo, col_title = st.columns([1, 14])
    with col_logo:
        logo_path = os.path.join(os.path.dirname(__file__), 'images', 'GDG OFFICIAL LOGO.svg')
        if os.path.exists(logo_path):
            st.image(logo_path, width=56)
    with col_title:
        st.markdown('<p class="header-title">Mac-a-Thon Applications</p>', unsafe_allow_html=True)
        st.markdown('<p class="header-sub">GDG on Campus · McMaster University — applicant analytics</p>',
                    unsafe_allow_html=True)

    # ---------- FILTERED FEATURE: load the wide table before the sidebar,
    # since the filter widgets need it to populate their option lists ----------
    wide_df = load_applicants_wide()

    # ---------- Sidebar ----------
    with st.sidebar:
        st.markdown("### View")
        st.caption("Toggle dashboard sections")
        show_app_info = st.checkbox("Applications", value=True)
        show_demographics = st.checkbox("Demographics", value=True)
        show_attributions = st.checkbox("Attributions", value=True)
        st.markdown("---")

        # FILTERED FEATURE: global filter sidebar, below the section toggles
        filter_state = render_filter_sidebar(wide_df)

        st.markdown("---")
        st.caption("Mac-a-Thon 2026 · Build with AI edition")

    try:
        # No st.spinner here: the aggregation is fast pandas, and the spinner's
        # overlay is part of the "pause + dim" flash we're reducing on rerun.
        with nullcontext():
            # FILTERED FEATURE: apply the sidebar's filter state once, then
            # every chart below re-aggregates from this single filtered frame
            # instead of calling the old per-chart SQL loaders.
            fdf = apply_filters(wide_df, filter_state)

            date_df = trend_counts(fdf)
            accepted, rejected = acceptance_counts(fdf)

            # Funnel chart shows the FULL funnel (every stage's count) with the
            # other filters applied but NOT the funnel-stage filter, so the
            # un-reached stages can be shown grayed rather than dropped. The
            # selected stage (if any) is the highlight cutoff.
            funnel_fdf = apply_filters(wide_df, filter_state, exclude=(FUNNEL_DIM_COL,))
            funnel_df = funnel_counts(funnel_fdf)
            funnel_highlight = filter_state.get(FUNNEL_DIM_COL)

            # SELF-DIM: a categorical chart ignores its OWN filter (shows the
            # full distribution) but honors every other filter, highlighting the
            # bars its filter selected and graying the rest — same idea as the
            # funnel's grayed stages. `sdf(dim)` is that chart's population
            # (all filters except `dim`); `hl(dim)` is its selected values (the
            # highlight). Metrics below the charts still read the FULLY filtered
            # frames (country_df_f / programs_df_f) so their numbers match the
            # active filter.
            def sdf(dim):
                return apply_filters(wide_df, filter_state, exclude=(dim,))

            def hl(dim):
                picked = filter_state.get(dim)
                return picked or None  # [] / None -> no highlight (all colour)

            experience_df = agg_count(sdf('experience'), 'experience', 'count', EXPERIENCE_ORDER)

            # STEM-first order (problem #2 — deliberately different from the
            # live dashboard's Programs chart, which stays on its own
            # count-descending order)
            programs_df = agg_count(sdf('program_type'), 'program_type', 'program_count', PROGRAM_ORDER)

            age_df = agg_count(sdf('academic_year'), 'academic_year', 'count', ACADEMIC_ORDER) \
                .rename(columns={'academic_year': 'category'})

            country_df = agg_count(sdf('country_bucket'), 'country_bucket', 'country_count', COUNTRY_ORDER) \
                .rename(columns={'country_bucket': 'Country of Residence'})

            # schools_counts / attribution_counts already carry the frozen
            # sort_order (SCHOOL_ORDER / ATTRIB_ORDER) — no post-hoc reorder.
            schools_df = schools_counts(sdf('school_group'))
            attribution_df = attribution_counts(sdf('heard_bucket'))

            # Fully-filtered variants for the metric tiles under the charts
            # (Canada/International split, STEM %) — these must reflect the
            # ACTIVE country/program filter, not the self-dimmed distribution.
            country_df_f = agg_count(fdf, 'country_bucket', 'country_count', COUNTRY_ORDER) \
                .rename(columns={'country_bucket': 'Country of Residence'})
            programs_df_f = agg_count(fdf, 'program_type', 'program_count', PROGRAM_ORDER)

            df_about = fdf[['about_length']].dropna()
            df_project = fdf[['project_length']].dropna()
            df_combined = fdf[['response_length']].dropna()

            prev_hacker_df = agg_count(sdf('attended_last_year'), 'attended_last_year', 'count', ['Yes', 'No'])

        if len(fdf) == 0:
            st.warning("No applicants match the current filters. Adjust or clear a filter in the sidebar.")
            return

        if not (show_app_info or show_attributions or show_demographics):
            st.warning("Please select at least one category to display.")
            return

        # ---------- KPI hero row ----------
        total_apps = int(date_df['application_count'].sum()) if len(date_df) else 0
        avg_apps = date_df['application_count'].mean() if len(date_df) else 0
        peak = date_df.loc[date_df['application_count'].idxmax()] if len(date_df) else None
        acceptance_rate = accepted / (accepted + rejected) * 100 if (accepted + rejected) else 0

        kpi_row([
            ("Total applications", f"{total_apps:,}", None),
            ("Acceptance rate", f"{acceptance_rate:.1f}%", f"{accepted:,} accepted"),
            ("Average per day", f"{avg_apps:.1f}", None),
            ("Peak day", f"{int(peak['application_count']):,}", f"{peak['date_clean']:%b %d}"),
        ])

        st.markdown("---")

        # ---------- Applicant retention funnel ----------
        st.markdown("## Applicant Funnel")
        st.caption("From application to a completed project — each stage is a subset of the one before it.")
        st.plotly_chart(
            create_funnel_chart(funnel_df, 'stage', 'count',
                                highlight_stage=funnel_highlight),
            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            key="funnel_chart")

        st.markdown("---")

        # ---------- Applications ----------
        if show_app_info:
            st.markdown("## Applications")

            st.markdown("### Applications per day")
            st.plotly_chart(create_trend_chart(date_df),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="trend_chart")

            # st.markdown("### Acceptance")
            # st.plotly_chart(create_split_bar("Accepted", "Rejected", accepted, rejected),
            #                 use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            #                 key="acceptance_split")

            exp_col, ret_col = st.columns(2, gap="large")
            with exp_col:
                st.markdown("### Hackathon experience")
                st.caption("Hackathons attended before applying")
                st.plotly_chart(create_column_chart(experience_df, 'experience', 'count',
                                                    sort_col='sort_order', color=COLORS['blue'],
                                                    highlight=hl('experience')),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="experience_chart")

            with ret_col:
                st.markdown("### Returning hackers")
                st.caption("Attended Mac-a-Thon last year (Jan. 2025)")
                st.plotly_chart(create_pie_chart(prev_hacker_df, 'attended_last_year', 'count',
                                                 colors=[COLORS['green'], COLORS['gray_track']],
                                                 highlight=hl('attended_last_year')),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="prev_hacker_chart")

            # st.markdown("### Response depth")
            # st.caption("Length of short-answer responses, in characters, with a normal-fit reference.")
            # c1, c2, c3 = st.columns(3, gap="small")
            # with c1:
            #     st.markdown("**“About yourself”**")
            #     st.plotly_chart(create_response_hist(df_about, 'about_length', COLORS['blue']),
            #                     use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            #                     key="hist_about")
            # with c2:
            #     st.markdown("**“Recent project”**")
            #     st.plotly_chart(create_response_hist(df_project, 'project_length', COLORS['green']),
            #                     use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            #                     key="hist_project")
            # with c3:
            #     st.markdown("**Combined**")
            #     st.plotly_chart(create_response_hist(df_combined, 'response_length', COLORS['amber']),
            #                     use_container_width=True, theme=None, config=PLOTLY_CONFIG,
            #                     key="hist_combined")

            # st.markdown("---")

        # ---------- Demographics ----------
        if show_demographics:
            st.markdown("## Demographics")

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("### Countries & Continents of Residence")
                st.caption("Key couuntries pulled out of continent grouping")
                st.plotly_chart(create_hbar(country_df, 'Country of Residence', 'country_count', sort_col='sort_order',
                                            color=COLORS['blue'], highlight=hl('country_bucket')),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="country_chart")

                total_country = country_df_f['country_count'].sum()
                canada = country_df_f.loc[country_df_f['Country of Residence'] == 'Canada', 'country_count']
                canada_count = int(canada.values[0]) if len(canada) else 0
                m1, m2 = st.columns(2)
                m1.metric("Canada", f"{canada_count:,}",
                          f"{canada_count / total_country * 100:.1f}%", delta_color="off")
                m2.metric("International", f"{total_country - canada_count:,}",
                          f"{(total_country - canada_count) / total_country * 100:.1f}%", delta_color="off")

            with c2:
                st.markdown("### Programs")
                # st.caption("Undergraduate students only")
                st.plotly_chart(create_hbar(programs_df, 'program_type', 'program_count', sort_col='sort_order',
                                            color=COLORS['green'], highlight=hl('program_type')),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="programs_chart")

                # STEM metrics reflect the ACTIVE filter (fully-filtered frame),
                # not the self-dimmed chart distribution.
                stem_types = {'Software', 'Engineering', 'Math', 'Technology'}
                total_undergrad = programs_df_f['program_count'].sum()
                stem_count = int(programs_df_f.loc[
                    programs_df_f['program_type'].isin(stem_types), 'program_count'].sum())
                m1, m2 = st.columns(2)
                m1.metric("In STEM", f"{stem_count / total_undergrad * 100:.1f}%")
                m2.metric("Not in STEM", f"{(total_undergrad - stem_count) / total_undergrad * 100:.1f}%")

            st.markdown("### Academic year")
            st.plotly_chart(create_column_chart(age_df, 'category', 'count', sort_col='sort_order',
                                                color=COLORS['amber'], highlight=hl('academic_year')),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="age_chart")

            st.markdown("### Schools")
            st.caption("Smaller schools grouped by region; College and High School kept separate")
            st.plotly_chart(create_hbar(schools_df, 'school_group', 'count', sort_col='sort_order',
                                        color=COLORS['blue'], highlight=hl('school_group')),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="schools_chart")

            st.markdown("---")

        # ---------- Attributions ----------
        if show_attributions:
            st.markdown("## Attributions")
            st.caption("How applicants heard about the event.")

            st.plotly_chart(create_hbar(attribution_df, 'source', 'attribution_count',
                                        sort_col='sort_order', color=COLORS['blue'],
                                        highlight=hl('heard_bucket')),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="attribution_chart")

            # Attribution metrics reflect the ACTIVE filter, not the self-dim chart
            attribution_df_f = attribution_counts(fdf)
            total_attr = attribution_df_f['attribution_count'].sum()
            top_source = attribution_df_f.loc[attribution_df_f['attribution_count'].idxmax()]
            m1, m2 = st.columns(2)
            m1.metric("Responses", f"{total_attr:,}")
            m2.metric("Top source", top_source['source'],
                      f"{top_source['attribution_count'] / total_attr * 100:.1f}% of applicants",
                      delta_color="off")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
