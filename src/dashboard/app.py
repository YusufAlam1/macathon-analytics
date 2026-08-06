"""
Main Dashboard Orchestrator
Handles layout, UI, and coordinates between data layer (queries) and visualization layer
"""
import base64
import html
import os
from contextlib import nullcontext

import streamlit as st
from PIL import Image
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
from filtered.filters import (
    render_filter_sidebar, apply_filters, trio_population, FUNNEL_DIM_COL,
    _active_filter_items, gender_available, GENDER_DIM_COL,
)
from filtered.projects import (
    load_project_members, applicant_email_index, project_count,
)
from filtered.schools_distinct import distinct_school_count
from filtered.aggregations import (
    agg_count, funnel_counts, acceptance_counts, trend_counts,
    schools_counts, attribution_counts, gender_counts,
)

# Page configuration
# page_icon needs decoded pixels, so it takes the rasterized PNG rather than the
# SVG that st.image() renders elsewhere. Path is absolute so the app can be
# launched from any working directory.
_ICON_PATH = os.path.join(os.path.dirname(__file__), 'images', 'Mac-a-Thon-LOGO.png')

st.set_page_config(
    page_title="Mac-a-Thon Applications",
    page_icon=Image.open(_ICON_PATH) if os.path.exists(_ICON_PATH) else "📊",
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
        position: relative;
        flex: 1 1 0;
        min-height: 96px;
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1rem 1.25rem;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }}
    /* --- KPI cards carrying a measurement caveat --------------------------
       The note hangs off a "?" icon pinned to the card's top-right corner,
       mirroring the tooltip Streamlit puts next to a heading's help text (same
       Lucide help-circle glyph). Previously the caveat lived in a title="" on
       the whole card, which gave no visible affordance and rendered as the
       OS-gray native box; the icon makes the qualifier discoverable and keeps
       the panel in the dashboard's own chrome. */
    .kpi-help {{
        position: absolute;
        top: 0.6rem;
        right: 0.7rem;
        width: 15px;
        height: 15px;
        color: {COLORS['ink_3']};
        cursor: help;
        transition: color 140ms ease-out;
    }}
    .kpi-help:hover, .kpi-help:focus-visible {{
        color: {COLORS['blue']};
        outline: none;
    }}
    .kpi-help svg {{ display: block; width: 100%; height: 100%; }}
    /* Panel: same white card + hairline border + soft shadow vocabulary as the
       cards themselves. Hidden with opacity+visibility (not display) so it can
       fade in rather than pop. Right-anchored so it can't overflow the page on
       the rightmost card. */
    .kpi-tip {{
        position: absolute;
        top: calc(100% + 8px);
        right: -6px;
        z-index: 1000;
        width: max-content;
        max-width: 260px;
        padding: 0.55rem 0.7rem;
        background: #ffffff;
        color: {COLORS['ink_2']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        box-shadow: 0 4px 16px rgba(32, 33, 36, 0.13);
        font-size: 0.78rem;
        font-weight: 400;
        line-height: 1.45;
        letter-spacing: 0;
        text-align: left;
        white-space: normal;
        opacity: 0;
        visibility: hidden;
        transform: translateY(-3px);
        transition: opacity 150ms ease-out, transform 150ms ease-out,
                    visibility 0s linear 150ms;
    }}
    .kpi-help:hover .kpi-tip, .kpi-help:focus-visible .kpi-tip {{
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
        transition: opacity 150ms ease-out, transform 150ms ease-out,
                    visibility 0s;
    }}
    /* Pointer notch, drawn from the panel's own border so the two read as one
       continuous surface. */
    .kpi-tip::before {{
        content: "";
        position: absolute;
        top: -5px;
        right: 10px;
        width: 8px;
        height: 8px;
        background: #ffffff;
        border-left: 1px solid {COLORS['border']};
        border-top: 1px solid {COLORS['border']};
        transform: rotate(45deg);
    }}
    .kpi-label {{
        color: {COLORS['ink_2']};
        font-size: 0.82rem;
        font-weight: 500;
        margin-bottom: 0.35rem;
        /* leave room for the "?" so a long label never runs under it */
        padding-right: 1.1rem;
    }}
    .kpi-value {{
        color: {COLORS['ink']};
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        line-height: 1.1;
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

    /* --- Filter header controls ---------------------------------------------
       "Filters  [⌄⌄] [⌃⌃]   [Reset]" on one row. Streamlit stamps every keyed
       widget's wrapper with `st-key-<key>`, so these rules reach only the three
       filter-header buttons and leave the rest of the page's buttons alone.
       The row's own top margin is trimmed because the `### Filters` h3 already
       carries block spacing. */
    [data-testid="stSidebar"] .st-key-flt_expand_all button,
    [data-testid="stSidebar"] .st-key-flt_collapse_all button,
    [data-testid="stSidebar"] .st-key-flt_reset button {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        color: {COLORS['ink_2']};
        font-size: 0.8rem;
        font-weight: 500;
        /* All three share one fixed height so the row reads as a single
           cluster; Streamlit otherwise pads the icon-only buttons taller than
           the text one. */
        height: 38px;
        min-height: 38px;
        padding: 0 0.9rem;
        display: flex;
        align-items: center;
        justify-content: center;
        /* The label must never wrap — a squeezed column previously broke
           "Reset" across two lines and ballooned the button. */
        white-space: nowrap;
        transition: border-color 140ms ease-out, color 140ms ease-out,
                    background-color 140ms ease-out;
    }}
    /* Icon buttons carry their padding as width rather than around a label.
       min-width keeps them comfortably rectangular: below ~40px the fixed
       height turns them into pills. */
    [data-testid="stSidebar"] .st-key-flt_expand_all button,
    [data-testid="stSidebar"] .st-key-flt_collapse_all button {{
        padding: 0 0.5rem;
        min-width: 44px;
    }}
    /* Reset holds its word on one line with room to breathe around it. */
    [data-testid="stSidebar"] .st-key-flt_reset button {{
        min-width: 76px;
    }}
    [data-testid="stSidebar"] .st-key-flt_expand_all button p,
    [data-testid="stSidebar"] .st-key-flt_collapse_all button p,
    [data-testid="stSidebar"] .st-key-flt_expand_all button span,
    [data-testid="stSidebar"] .st-key-flt_collapse_all button span {{
        font-size: 1.1rem;
        line-height: 1;
        margin: 0;
    }}
    [data-testid="stSidebar"] .st-key-flt_expand_all button:hover,
    [data-testid="stSidebar"] .st-key-flt_collapse_all button:hover {{
        border-color: {COLORS['blue']};
        color: {COLORS['blue']};
    }}
    /* Reset is the one destructive control here, so it (and only it) goes red
       on hover — the affordance that says "this throws your selections away". */
    [data-testid="stSidebar"] .st-key-flt_reset button:hover {{
        border-color: {COLORS['red']};
        color: {COLORS['red']};
        background-color: rgba(234, 67, 53, 0.06);
    }}
    [data-testid="stSidebar"] .st-key-flt_reset button:active,
    [data-testid="stSidebar"] .st-key-flt_reset button:focus:not(:active) {{
        border-color: {COLORS['red']} !important;
        color: {COLORS['red']} !important;
    }}

    /* --- Slider value/tick labels ------------------------------------------
       Streamlit renders the slider's current value (the thumb bubble) and the
       min/max tick labels in a monospace numeric font, which reads as "techy"
       and clashes with the rest of the sidebar. Force the normal sans font. */
    [data-testid="stSliderThumbValue"],
    [data-testid="stSliderTickBarMin"],
    [data-testid="stSliderTickBarMax"] {{
        font-family: {FONT_FAMILY} !important;
        font-feature-settings: normal !important;
    }}

    /* --- Active-filters summary box ---------------------------------------- */
    .flt-active-box {{
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 0.5rem 0.6rem;
        background: #ffffff;
        margin-top: 0.35rem;
    }}
    .flt-active-row {{
        display: flex;
        justify-content: space-between;
        gap: 0.6rem;
        padding: 0.2rem 0;
        font-size: 0.82rem;
        line-height: 1.3;
    }}
    .flt-active-row + .flt-active-row {{
        border-top: 1px solid #f0f1f3;
    }}
    .flt-active-label {{
        color: {COLORS['ink_2']};
        font-weight: 500;
        white-space: nowrap;
    }}
    .flt-active-val {{
        color: {COLORS['ink']};
        font-weight: 600;
        text-align: right;
    }}

    /* Charts flush inside their columns */
    [data-testid="stPlotlyChart"] {{
        padding: 0 !important;
        margin: 0 !important;
    }}

    </style>
""", unsafe_allow_html=True)


# Lucide "help-circle" — the same glyph Streamlit renders next to a heading's
# help text, inlined here because the KPI row is hand-built HTML (one markdown
# block) and so can't use st.*'s `help=` argument.
_HELP_ICON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"></circle>'
    '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>'
    '<line x1="12" y1="17" x2="12.01" y2="17"></line>'
    '</svg>'
)


def kpi_row(cards):
    """Render KPI cards as one flex container so every card is the same fixed
    height and the row sits flush inside a single wrapping rectangle.

    Each card is (label, value) or (label, value, note). `note` is a caveat
    about how the number is measured; it hangs off a "?" icon in the card's
    top-right corner and stays hidden until hover/focus, so a reader who
    doesn't care never sees a qualifier while one who does has a visible
    affordance to reach for."""
    items = []
    for card in cards:
        label, value = card[0], card[1]
        note = card[2] if len(card) > 2 else None
        help_el = ''
        if note:
            # html.escape: the note is prose with apostrophes/quotes going into
            # markup, so it must not break out of the surrounding element.
            # tabindex makes the tooltip keyboard-reachable, not hover-only.
            help_el = (f'<span class="kpi-help" tabindex="0" role="note">'
                       f'{_HELP_ICON_SVG}'
                       f'<span class="kpi-tip">{html.escape(str(note))}</span>'
                       f'</span>')
        items.append(
            f'<div class="kpi-card">'
            f'{help_el}'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="kpi-row">{"".join(items)}</div>', unsafe_allow_html=True)


def section_header(text, note=None, muted=False):
    """A section header matching the "### ..." headers used everywhere else,
    optionally carrying a tooltip.

    Uses st.subheader rather than st.markdown("### ...") because subheader
    takes a `help` argument — Streamlit's own tooltip component, which already
    matches the dashboard's chrome — while still emitting the native heading
    anchor (the small link icon) that every other section header has. Hand-
    rolling the tooltip in a raw <div> loses that anchor and makes this one
    header the odd one out.

    `note` is GitHub-flavored Markdown (NOT html — `**bold**`, not `<b>`).
    `muted` grays the title to match a frozen chart beneath it."""
    if muted:
        # Streamlit has no color argument for headings, so the muted variant
        # goes through markdown's :gray[...] color directive, which subheader
        # accepts as part of its body. The anchor is left ON either way, so the
        # link icon is present in both states like every other section header.
        text = f":gray[{text}]"
    st.subheader(text, help=note)


def main():
    # ---------- Header ----------
    # Mac-a-Thon left, title center, GDG right. The two logos are sized to the
    # same rendered HEIGHT (~47px) rather than the same width, since their aspect
    # ratios differ (Mac-a-Thon 1080x900, GDG 382x232) and matching widths would
    # leave the GDG mark looking undersized.
    col_logo, col_title, col_gdg = st.columns([1, 12, 2], vertical_alignment="center")
    with col_logo:
        logo_path_mac = os.path.join(os.path.dirname(__file__), 'images', 'Mac-a-Thon-LOGO.svg')
        if os.path.exists(logo_path_mac):
            st.image(logo_path_mac, width=56)
    with col_title:
        st.markdown('<p class="header-title">Mac-a-Thon Applicant Analytics</p>', unsafe_allow_html=True)
        st.markdown('<p class="header-sub">Google Developer Groups · McMaster University</p>',
                    unsafe_allow_html=True)
    with col_gdg:
        # st.image() has no alignment option, so the right-hand logo goes through
        # a flex-end div with the SVG inlined as a data URI.
        logo_path_gdg = os.path.join(os.path.dirname(__file__), 'images', 'GDG OFFICIAL LOGO.svg')
        if os.path.exists(logo_path_gdg):
            with open(logo_path_gdg, 'rb') as fh:
                gdg_b64 = base64.b64encode(fh.read()).decode('ascii')
            st.markdown(
                '<div style="display:flex;justify-content:flex-end;align-items:center;">'
                f'<img src="data:image/svg+xml;base64,{gdg_b64}" width="78"/>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ---------- FILTERED FEATURE: load the wide table before the sidebar,
    # since the filter widgets need it to populate their option lists ----------
    wide_df = load_applicants_wide()

    # ---------- Sidebar ----------
    with st.sidebar:
        st.markdown("### View")
        st.caption("Toggle dashboard sections")
        show_app_info = st.checkbox("Applicants", value=True)
        show_demographics = st.checkbox("Demographics", value=True)
        show_attributions = st.checkbox("Attributions", value=True)
        st.markdown("---")

        # FILTERED FEATURE: global filter sidebar, below the section toggles
        filter_state = render_filter_sidebar(wide_df)

        # st.markdown("---")
        # st.caption("Mac-a-Thon 2026 · Build with AI edition")

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
            # count-descending order). program_type is in the HS trio ->
            # trio_population (HS grays/unions, never drops bars).
            programs_df = agg_count(trio_population(wide_df, filter_state, 'program_type'),
                                    'program_type', 'program_count', PROGRAM_ORDER)

            age_df = agg_count(trio_population(wide_df, filter_state, 'academic_year'),
                               'academic_year', 'count', ACADEMIC_ORDER) \
                .rename(columns={'academic_year': 'category'})

            # schools_counts / attribution_counts already carry the frozen
            # sort_order (SCHOOL_ORDER / ATTRIB_ORDER) — no post-hoc reorder.
            # school_group is in the HS trio -> trio_population.
            schools_df = schools_counts(trio_population(wide_df, filter_state, 'school_group'))
            attribution_df = attribution_counts(sdf('heard_bucket'))

            # Fully-filtered variants for the metric tiles under the charts
            # (Canada/International split, STEM %) — these must reflect the
            # ACTIVE country/program filter, not the self-dimmed distribution.
            country_df_f = agg_count(fdf, 'country_bucket', 'country_count', COUNTRY_ORDER) \
                .rename(columns={'country_bucket': 'Country of Residence'})
            programs_df_f = agg_count(fdf, 'program_type', 'program_count', PROGRAM_ORDER)
            schools_df_f = schools_counts(fdf)

            df_about = fdf[['about_length']].dropna()
            df_project = fdf[['project_length']].dropna()
            df_combined = fdf[['response_length']].dropna()

            prev_hacker_df = agg_count(sdf('attended_last_year'), 'attended_last_year', 'count', ['Yes', 'No'])

            # --- Gender: live only past the RSVP gate ------------------------
            # gender exists solely for RSVPed+ applicants (loaders.GENDER_COL),
            # so the chart has two modes:
            #   LIVE  (funnel >= RSVPed) — self-dims on its own dim like every
            #         other filterable chart: full Male/Female split, selected
            #         side coloured, other muted, rest of the dashboard filtered.
            #   FROZEN(funnel <  RSVPed) — a fixed snapshot of the ENTIRE RSVP
            #         population, ignoring all filters (user decision: frozen
            #         means frozen, not "live minus the funnel"). Rendered gray
            #         with a tooltip saying why and how to unfreeze.
            gender_live = gender_available(filter_state)
            if gender_live:
                male_count, female_count = gender_counts(sdf(GENDER_DIM_COL))
            else:
                # Unfiltered wide_df restricted to RSVPed — the frozen snapshot.
                male_count, female_count = gender_counts(wide_df[wide_df['is_rsvped']])

        if len(fdf) == 0:
            st.warning("No applicants match the current filters. Adjust or clear a filter in the sidebar.")
            return

        if not (show_app_info or show_attributions or show_demographics):
            st.warning("Please select at least one category to display.")
            return

        # ---------- KPI hero row ----------
        # Mirrors the sponsorship package's four headline stats (applications,
        # hackers, schools, projects) rather than restating charts further down:
        # acceptance rate was the funnel's 2nd bar (and pinned to 100% whenever
        # a post-acceptance stage was filtered), and peak day was the trend
        # chart's apex.
        total_apps = int(date_df['application_count'].sum()) if len(date_df) else 0
        attended = int(fdf['is_attended'].sum()) if len(fdf) else 0

        # Projects: the true submitted count while unfiltered, else the
        # email-joined count. See filtered/projects.py for why the two differ.
        proj_members, proj_total = load_project_members(applicant_email_index(wide_df))
        filters_active = bool(_active_filter_items(filter_state))
        projects = project_count(proj_members, proj_total, fdf, filters_active)

        # Schools: distinct institutions with >= 2 applicants, taken from the RAW
        # free-text column (NOT the frozen school_group buckets) with spelling
        # variants normalized first — see filtered/schools_distinct.py.
        schools = distinct_school_count(fdf)

        kpi_row([
            ("Applications Received", f"{total_apps:,}"),
            ("Hackers Engaged", f"{attended:,}",
             "Note: Value only accounts for physically checked-in hackers"
             ", true attendance count expected to have been higher."),
            ("Schools Represented", f"{schools:,}",
             "Note: Only schools with at least two applicants are considered in count."),
            #  ". Single-applicant schools are excluded."),
            ("Projects Completed", f"{projects:,}"),
        ])

        st.markdown('<hr style="height: 3px; background-color: dark-gray; border: none;">', unsafe_allow_html=True)

        # ---------- Applications ----------
        if show_app_info:
            st.markdown("## Applicants")

            # ---------- Applicant retention funnel ----------
            st.markdown("### Applicant funnel")
            st.caption("From application to a completed project — each stage is a subset of the one before it.")
            st.plotly_chart(
                create_funnel_chart(funnel_df, 'stage', 'count',
                                    highlight_stage=funnel_highlight),
                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                key="funnel_chart")

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
                st.caption("Attended Mac-a-Thon last year (Feb. 2025)")
                st.plotly_chart(create_pie_chart(prev_hacker_df, 'attended_last_year', 'count',
                                                 colors=[COLORS['red'], COLORS['green']],
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

            # --- Canadian vs. international: one proportional bar (binary split).
            # Canada wears the brand red; International is the neutral remainder.
            st.markdown("### Country (Canadian vs. international)")
            total_country = country_df_f['country_count'].sum()
            canada = country_df_f.loc[country_df_f['Country of Residence'] == 'Canada', 'country_count']
            canada_count = int(canada.values[0]) if len(canada) else 0
            intl_count = total_country - canada_count
            st.plotly_chart(create_split_bar("Canada", "International",
                                             canada_count, intl_count,
                                             left_color=COLORS['red']),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="country_split")

            # --- Schools + Programs side by side. Schools has 10 bars, Programs
            # 7. row_height on each is set so BOTH figures are EXACTLY 372px
            # (64 + row_height*n): Programs 64+44*7, Schools 64+30.8*10. Equal
            # height + identical symmetric t/b margins + same bargap ⇒ the last
            # (bottom) bar lands at the same pixel in both, so their bottoms are
            # flush.
            c1, c2 = st.columns(2, gap="large")
            with c1:
                section_header(
                    "Schools",
                    note="Canadian schools with proportionally less applicants are grouped into "
                         "**Other Canada**")
                # st.caption("Smaller schools grouped by region; College and High School kept separate")
                st.plotly_chart(create_hbar(schools_df, 'school_group', 'count', sort_col='sort_order',
                                            color=COLORS['blue'], highlight=hl('school_group'),
                                            row_height=30.8),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="schools_chart")

            with c2:
                st.markdown("### Programs")
                # st.caption("Undergraduate students only")
                st.plotly_chart(create_hbar(programs_df, 'program_type', 'program_count', sort_col='sort_order',
                                            color=COLORS['green'], highlight=hl('program_type'),
                                            row_height=44),
                                use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                                key="programs_chart")

            # All four KPI tiles in ONE full-width row (not nested inside the
            # chart columns) so they align as a single band regardless of any
            # height difference above. Left pair = Schools (McMaster share),
            # right pair = Programs (STEM share). Whitespace between the pairs
            # is acceptable per the design. All values use the fully-filtered
            # frames, not the self-dimmed chart frames.
            total_schools = schools_df_f['count'].sum()
            mac = schools_df_f.loc[schools_df_f['school_group'] == 'McMaster University', 'count']
            mac_count = int(mac.values[0]) if len(mac) else 0

            stem_types = {'Software', 'Engineering', 'Math', 'Technology'}
            total_undergrad = programs_df_f['program_count'].sum()
            stem_count = int(programs_df_f.loc[
                programs_df_f['program_type'].isin(stem_types), 'program_count'].sum())

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("McMaster", f"{mac_count / total_schools * 100:.1f}%")
            k2.metric("Other schools", f"{(total_schools - mac_count) / total_schools * 100:.1f}%")
            k3.metric("In STEM", f"{stem_count / total_undergrad * 100:.1f}%")
            k4.metric("Not in STEM", f"{(total_undergrad - stem_count) / total_undergrad * 100:.1f}%")

            st.markdown("### Academic year")
            st.plotly_chart(create_column_chart(age_df, 'category', 'count', sort_col='sort_order',
                                                color=COLORS['amber'], highlight=hl('academic_year')),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="age_chart")

            # --- Gender: binary split, Male blue / Female red. Both sides are
            # identities (not "the rest"), so both carry a hue and both percents
            # sit inside their own segment. When the funnel filter is below
            # RSVPed the whole figure renders muted and static — see the
            # gender_live block above for the two modes.
            if gender_live:
                section_header("Gender")
            else:
                section_header(
                    "Gender", muted=True,
                    note="Gender was only collected in the RSVP survey, so it "
                         "exists for **RSVPed applicants only**.\n\n"
                         "This chart is frozen: it shows the full RSVP "
                         "population and ignores any filters."
                         "\t\tTo see gender respond to your filters, set "
                         "**Applicant funnel** to **RSVPed** or beyond.")
            st.plotly_chart(create_split_bar("Male", "Female",
                                             male_count, female_count,
                                             left_color=COLORS['blue'],
                                             right_color=COLORS['red'],
                                             right_inside_pct=True,
                                             muted=not gender_live,
                                             highlight=hl(GENDER_DIM_COL) if gender_live else None),
                            use_container_width=True, theme=None, config=PLOTLY_CONFIG,
                            key="gender_split")

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
            m2.metric("Top source", top_source['source'])

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
