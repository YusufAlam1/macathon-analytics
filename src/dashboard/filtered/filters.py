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


def _hs_key(dim):
    """Session-state key for the 'High School' checkbox of a trio dimension."""
    return f"flt_{dim}_{HS_VALUE}"


def _sync_hs(changed_dim):
    """on_change for a trio 'High School' checkbox: mirror its new value onto
    the other two trio dimensions' HS checkboxes so ticking/unticking High
    School anywhere ticks/unticks it in all three (Program / Academic year /
    School). Runs before the ensuing rerun re-instantiates those widgets, so
    the mirrored value is what they render with."""
    val = st.session_state.get(_hs_key(changed_dim), False)
    for d in HS_TRIO:
        if d != changed_dim:
            st.session_state[_hs_key(d)] = val


def _active_filter_items(state):
    """Human-readable (label, value_text) pairs for every dimension that has a
    real selection — used to render the "active filters" summary so the user
    can see exactly what's on without opening each expander.

    The three High-School-trio 'High School' selections are one synced cohort,
    so they collapse into a single "High School" line instead of appearing
    under Program, Academic year and School separately."""
    items = []
    hs_shown = False
    for col, label, _, kind in FILTER_DIMS:
        picked = state.get(col)
        if kind == "single":
            if picked is not None:
                items.append((label, FUNNEL_SLIDER_LABELS.get(picked, picked)))
        elif kind == "range_slider":
            if picked is not None:
                lo, hi = picked
                items.append((label, f"{lo:%b %d} – {hi:%b %d}"))
        else:  # checkbox
            if not picked:
                continue
            vals = list(picked)
            if col in HS_TRIO and HS_VALUE in vals:
                vals = [v for v in vals if v != HS_VALUE]
                if not hs_shown:
                    items.append(("High School", "Yes"))
                    hs_shown = True
            if vals:
                items.append((label, ", ".join(str(v) for v in vals)))
    return items


def _do_reset():
    """Clear every filter widget's session_state key. Wired as the Reset
    button's on_click callback: Streamlit runs on_click callbacks BEFORE the
    widgets are re-instantiated in the ensuing rerun, so deleting a widget's key
    here reliably snaps it back to its default — including checkboxes inside a
    collapsed expander. (Deleting a key only resets a widget that hasn't been
    instantiated yet this run; a manual st.rerun() after the click races with
    the button's own auto-rerun and left widgets visually stuck.)"""
    for key in list(st.session_state.keys()):
        if key.startswith("flt_") and key not in ("flt_reset", "flt_expanded_all"):
            del st.session_state[key]


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
        # on_click runs _do_reset BEFORE the filter widgets are instantiated in
        # this same rerun, so every checkbox/slider clears (see _do_reset).
        st.button("Reset", key="flt_reset", help="Clear all filters",
                  on_click=_do_reset)

    # Expand / collapse every filter menu at once. The shared flag drives the
    # `expanded=` of each checkbox expander below.
    st.session_state.setdefault("flt_expanded_all", False)
    exp_col, col_col = st.columns(2)
    with exp_col:
        if st.button("Expand all", key="flt_expand_all", use_container_width=True):
            st.session_state["flt_expanded_all"] = True
            st.rerun()
    with col_col:
        if st.button("Collapse all", key="flt_collapse_all", use_container_width=True):
            st.session_state["flt_expanded_all"] = False
            st.rerun()
    expanded_all = st.session_state["flt_expanded_all"]

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
            in_trio = col in HS_TRIO
            with st.expander(label, expanded=expanded_all):
                picked = []
                for o in opts:
                    # The 'High School' checkbox in a trio dimension mirrors its
                    # state to the other two trio dims (Program/Academic/School)
                    # via _sync_hs, so ticking HS anywhere ticks it everywhere.
                    cb_kwargs = {}
                    if in_trio and str(o) == HS_VALUE:
                        cb_kwargs = dict(on_change=_sync_hs, args=(col,))
                    if st.checkbox(str(o), value=False, key=f"flt_{col}_{o}", **cb_kwargs):
                        picked.append(o)
            state[col] = picked

    # --- Active-filters summary -------------------------------------------
    # A plain list of what's currently on, so the user never has to reopen each
    # expander to remember which boxes they ticked.
    items = _active_filter_items(state)
    st.markdown("---")
    if items:
        # Count the visible rows, not raw dimensions, so the header matches what
        # the user sees (the HS trio collapses to a single "High School" line).
        st.markdown(f"**Active filters ({len(items)})**")
        rows = "".join(
            f'<div class="flt-active-row">'
            f'<span class="flt-active-label">{label}</span>'
            f'<span class="flt-active-val">{val}</span>'
            f'</div>'
            for label, val in items
        )
        st.markdown(f'<div class="flt-active-box">{rows}</div>', unsafe_allow_html=True)
    else:
        st.caption("No filters active — showing all applicants.")

    return state


# The funnel dimension's column — filtered separately for the funnel chart so
# it can show the full funnel and gray (not drop) the un-reached stages.
FUNNEL_DIM_COL = FILTER_DIMS[0][0]  # "funnel_stage_reached"

# "High School" is one real cohort (the same 44 people) that surfaces as a bar
# in THREE different dimensions — Program, Academic year, and School. Selecting
# it is a single synchronized toggle (see render_filter_sidebar).
#
# The ONLY special case is "High School is the SOLE trio selection". Then:
#   - the three trio charts show their FULL distribution with just the HS bar
#     highlighted (gray-not-drop), and
#   - the whole dashboard filters to the 44 High-Schoolers.
# The moment ANY other trio value is also picked (e.g. Software + High School),
# behavior reverts to normal: HS is just one selected value among others, the
# whole dashboard filters on the union (Software OR High School = 614), and the
# trio charts self-dim normally. All of this flows from _trio_keep_mask().
HS_TRIO = ('program_type', 'academic_year', 'school_group')
HS_VALUE = 'High School'


def _trio_keep_mask(df, state, exclude_dim=None):
    """Boolean Series: which rows the THREE trio dims (program/academic/school)
    keep, as a unit, under the special High-School rule. `exclude_dim` (a trio
    column or None) is self-dim-excluded from the picks — a chart passes its own
    dim so it doesn't filter itself; the fully-filtered frame passes None so all
    three participate.

    Because HS is one synced cohort spread across three columns, AND-ing its
    per-column equality would wrongly collapse combined selections (Software +
    HS -> empty, since a Software applicant's academic/school != HS). So HS is
    handled as a single cohort predicate `is_hs`, combined thus:
      - other (non-HS) trio picks filter normally: AND across dims, OR within.
      - HS is the SOLE trio pick  -> restrict to is_hs  (whole dashboard = the 44)
        …but a chart (exclude_dim set) shows ALL its bars in that case (HS is
        drawn highlighted, not filtered), so it keeps everyone.
      - HS + other picks          -> (other picks) OR is_hs  (union HS back in).
      - no HS                     -> just the other picks (fully normal)."""
    idx_true = df.index.to_series().apply(lambda _: True)
    participating = [d for d in HS_TRIO if d != exclude_dim]

    hs_selected = any(HS_VALUE in (state.get(d) or ()) for d in HS_TRIO)
    # The HS cohort is identical across all three columns; pick any participating
    # trio column to identify it (fall back to the full trio if dim excluded).
    id_col = participating[0] if participating else HS_TRIO[0]
    is_hs = df[id_col] == HS_VALUE

    picks_mask = idx_true.copy()
    any_other_pick = False
    for d in participating:
        non_hs = [v for v in (state.get(d) or ()) if v != HS_VALUE]
        if non_hs:
            any_other_pick = True
            picks_mask &= df[d].isin(non_hs)

    if hs_selected and any_other_pick:
        return picks_mask | is_hs                       # union HS back in (normal)
    if hs_selected:  # HS is the sole trio selection
        # A chart shows every bar (HS highlighted, not filtered); the fully-
        # filtered frame restricts to the HS cohort.
        return idx_true if exclude_dim is not None else is_hs
    return picks_mask  # no HS: normal (all-True if no picks either)


def apply_filters(df, state, exclude=()):
    """Pure (df, state) -> filtered df. No Streamlit dependency — safe to
    unit test directly. `exclude` is an iterable of dim column names to SKIP
    entirely (used to build a chart's self-dim population — every filter EXCEPT
    that chart's own dimension, so its bars are grayed not dropped).

    The three High-School-trio dims are handled together via _trio_keep_mask
    (see it for the sole-HS special case); every other dim filters plainly."""
    mask = df.index.to_series().apply(lambda _: True)

    for col, _, _, kind in FILTER_DIMS:
        if col in exclude or col in HS_TRIO:
            continue  # trio dims handled as a unit below
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

    # Trio dims: any trio dim NOT excluded participates. If ALL three are
    # excluded (e.g. exclude=HS_TRIO to build a non-trio base), skip entirely.
    if any(d not in exclude for d in HS_TRIO):
        # exclude_dim: honor per-chart self-dim only when exactly one trio dim is
        # excluded; the multi-exclude/base cases pass None (nothing to self-dim).
        excluded_trio = [d for d in HS_TRIO if d in exclude]
        exclude_dim = excluded_trio[0] if len(excluded_trio) == 1 else None
        mask &= _trio_keep_mask(df, state, exclude_dim=exclude_dim)

    return df[mask]


def trio_population(df, state, dim):
    """Population for one High-School-trio chart (`dim` in HS_TRIO). Just
    apply_filters excluding that chart's own dim — the trio's special HS rule is
    baked into apply_filters via _trio_keep_mask, so:
      - HS is the sole trio pick -> full distribution, HS bar highlighted.
      - HS + other picks / no HS -> normal self-dim (Software narrows it, etc.).
    Kept as a named helper so the call sites read intentionally."""
    return apply_filters(df, state, exclude=(dim,))
