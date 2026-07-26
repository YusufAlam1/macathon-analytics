"""
Filtered dashboard — filter sidebar + apply_filters (isolated feature)
========================================================================
A declarative registry (FILTER_DIMS) so adding a new filter dimension is
~one line. render_filter_sidebar draws the widgets; apply_filters is a pure
(df, state) -> df function usable without Streamlit (unit-testable).

Semantics: empty selection on a checkbox dimension = no filter (show all).
Cross-dimension = AND. Within a checkbox dimension = OR (.isin). The funnel
dimension is a single-select "reached-at-least" (see loaders.STAGE_TO_FLAG).
The date dimension is an inclusive range.
"""
import streamlit as st

from filtered.loaders import (
    FUNNEL_STAGE_ORDER, STAGE_TO_FLAG, PROGRAM_ORDER, ACADEMIC_ORDER,
    COUNTRY_ORDER, EXPERIENCE_ORDER, SCHOOL_ORDER, ATTRIB_ORDER,
)

# The first funnel stage ('Applied') is the entire applicant pool, so on the
# slider it reads as "Applicants (all)" — the no-filter default. Display-only:
# the underlying state value stays the canonical stage key.
FUNNEL_SLIDER_LABELS = {FUNNEL_STAGE_ORDER[0]: 'Applicants (all)'}

# (wide_df column, sidebar label, value order or None, control type)
# order=None -> sorted() at render time. control types: "single" | "range_slider" | "checkbox"
#
# School and "Heard about us" filter the FROZEN mapped columns (school_group /
# heard_bucket), NOT the raw strings — so the option list is exactly the 10 /
# 7 canonical labels shown on the charts (user decision 2026-07-21). The
# option set is fixed to the full-population buckets and never shifts as other
# filters are applied.
FILTER_DIMS = [
    ("funnel_stage_reached", "Applicant funnel",     FUNNEL_STAGE_ORDER, "single"),
    ("app_date",             "Application date",     None,               "range_slider"),
    ("program_type",         "Program",              PROGRAM_ORDER,      "checkbox"),
    ("academic_year",        "Academic year",        ACADEMIC_ORDER,     "checkbox"),
    ("school_group",         "School",               SCHOOL_ORDER,       "checkbox"),
    ("country_bucket",       "Country/Region",       COUNTRY_ORDER,      "checkbox"),
    ("experience",           "Hackathon experience", EXPERIENCE_ORDER,   "checkbox"),
    ("attended_last_year",   "Returning hacker",     ["Yes", "No"],      "checkbox"),
    ("heard_bucket",         "Heard about us via",   ATTRIB_ORDER,       "checkbox"),
]


def _ordered_unique(series, order):
    """Distinct non-null values, in `order` if given (unlisted values sorted
    to the end), else alphabetically sorted."""
    present = set(series.dropna().unique())
    if order:
        head = [v for v in order if v in present]
        tail = sorted(present - set(head))
        return head + tail
    return sorted(present)


def _active_filter_count(state):
    """How many dimensions currently have a real (non-empty) selection."""
    n = 0
    for col, _, _, kind in FILTER_DIMS:
        picked = state.get(col)
        if kind == "checkbox":
            n += 1 if picked else 0
        else:
            n += 1 if picked is not None else 0
    return n


def render_filter_sidebar(df):
    """Draw the filter widgets in the CURRENT st.sidebar context (caller is
    responsible for the `with st.sidebar:` block, matching the existing
    section-toggle pattern in app.py) and return the filter state dict.

    All checkbox dimensions (incl. School and Heard-about-us) draw their
    options from the fixed order list in FILTER_DIMS, so the option set is the
    frozen canonical labels and stays stable regardless of other filters.
    """
    header_col, reset_col = st.columns([3, 2])
    with header_col:
        st.markdown("### Filters")
    with reset_col:
        if st.button("Reset", key="flt_reset", help="Clear all filters"):
            for key in list(st.session_state.keys()):
                if key.startswith("flt_") and key != "flt_reset":
                    del st.session_state[key]
            st.rerun()
    # st.caption("Empty = show all. Filters apply to every chart below.")

    state = {}

    for col, label, order, kind in FILTER_DIMS:
        if kind == "single":
            # Funnel stage: select_slider reads as depth-into-the-funnel.
            # "reached-at-least" — the leftmost stage ('Applied') is the whole
            # pool (is_applied is trivially true for everyone), so it doubles as
            # the "no filter" default. We label it "Applicants (all)" on the
            # slider (display only) instead of a separate redundant '(all)' stop.
            picked = st.select_slider(
                label, options=order, value=order[0], key=f"flt_{col}",
                format_func=lambda s: FUNNEL_SLIDER_LABELS.get(s, s),
            )
            # First stage == full pool -> treat as no filter (mask short-circuits)
            state[col] = None if picked == order[0] else picked

        elif kind == "range_slider":
            valid_dates = df['app_date'].dropna()
            if valid_dates.empty:
                state[col] = None
                continue
            lo, hi = valid_dates.min().date(), valid_dates.max().date()
            picked = st.slider(
                label, min_value=lo, max_value=hi, value=(lo, hi), key=f"flt_{col}",
            )
            # Full range selected = no filter (matches "empty = all" semantics)
            state[col] = None if picked == (lo, hi) else picked

        else:  # checkbox, grouped under an expander
            opts = _ordered_unique(df[col], order)
            with st.expander(label, expanded=False):
                picked = [o for o in opts if st.checkbox(str(o), value=False, key=f"flt_{col}_{o}")]
            state[col] = picked

    active_n = _active_filter_count(state)
    if active_n:
        st.caption(f"{active_n} filter{'s' if active_n != 1 else ''} active")

    return state


# The funnel dimension's column — filtered separately for the funnel chart so
# it can show the full funnel and gray (not drop) the un-reached stages.
FUNNEL_DIM_COL = FILTER_DIMS[0][0]  # "funnel_stage_reached"


def apply_filters(df, state, exclude=()):
    """Pure (df, state) -> filtered df. No Streamlit dependency — safe to
    unit test directly. `exclude` is an iterable of dim column names to SKIP
    (used to build the funnel chart's population, which applies every filter
    EXCEPT the funnel stage so un-reached stages can be shown grayed)."""
    mask = df.index.to_series().apply(lambda _: True)

    for col, _, _, kind in FILTER_DIMS:
        if col in exclude:
            continue
        picked = state.get(col)
        if picked is None:
            continue  # not set / full range / "(all)" -> no filter

        if kind == "single":
            # "reached-at-least": apply that stage's own is_X flag directly
            # (see loaders.furthest_stage docstring for why NOT a >= compare
            # on funnel_stage_reached).
            flag_col = STAGE_TO_FLAG[picked]
            mask &= df[flag_col]

        elif kind == "range_slider":
            lo, hi = picked
            mask &= df['app_date'].dt.date.between(lo, hi)

        else:  # checkbox: empty list = no filter, else OR via isin
            if picked:
                mask &= df[col].isin(picked)

    return df[mask]
