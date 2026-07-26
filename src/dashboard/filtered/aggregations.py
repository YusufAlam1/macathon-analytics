"""
Filtered dashboard — pandas re-aggregation helpers (isolated feature)
========================================================================
Turns the filtered wide DataFrame back into the small label/value frames
every existing create_* function in visualizations.py already expects.
None of visualizations.py changes — these functions just reproduce, in
pandas, what each SQL file's GROUP BY used to do.
"""
import pandas as pd

from filtered.loaders import (
    FUNNEL_STAGE_ORDER, STAGE_TO_FLAG, SCHOOL_ORDER, ATTRIB_ORDER,
)


def agg_count(fdf, col, value_col, order=None):
    """Generic groupby -> (col, value_col, sort_order) frame, matching the
    shape create_hbar/create_column_chart expect from their SQL-aggregated
    predecessors."""
    g = fdf.groupby(col, dropna=True).size().reset_index(name=value_col)
    if order:
        rank = {v: i for i, v in enumerate(order)}
        g['sort_order'] = g[col].map(rank).fillna(len(order))
    else:
        g['sort_order'] = 0
    return g


def funnel_counts(fdf):
    """Recount the 5 funnel stages from the filtered frame's own is_* flags
    (each stage's independent count, exactly matching funnel_counts.sql's
    semantics)."""
    counts = [int(fdf[STAGE_TO_FLAG[s]].sum()) for s in FUNNEL_STAGE_ORDER]
    return pd.DataFrame({
        'stage': FUNNEL_STAGE_ORDER,
        'count': counts,
        'sort_order': range(len(FUNNEL_STAGE_ORDER)),
    })


def acceptance_counts(fdf):
    """(accepted, rejected) scalars for create_split_bar, from is_accepted."""
    accepted = int(fdf['is_accepted'].sum())
    rejected = len(fdf) - accepted
    return accepted, rejected


def trend_counts(fdf):
    """One row per day -> (date_clean, application_count), matching
    load_date_data's shape for create_trend_chart."""
    d = fdf.dropna(subset=['app_date']).copy()
    daily = d.groupby('app_date').size().reset_index(name='application_count')
    daily = daily.rename(columns={'app_date': 'date_clean'}).sort_values('date_clean')
    return daily


def schools_counts(fdf):
    """School distribution over the FROZEN 10-label school_group column
    (map_school_group). Buckets are fixed to what the full-population
    threshold produced (user decision 2026-07-21) — the filter shrinks the
    counts but never changes the SET of buckets, so chart labels and filter
    options always agree. Includes a sort_order from the frozen SCHOOL_ORDER."""
    g = fdf.groupby('school_group', dropna=True).size().reset_index(name='count')
    rank = {v: i for i, v in enumerate(SCHOOL_ORDER)}
    g['sort_order'] = g['school_group'].map(rank).fillna(len(SCHOOL_ORDER))
    return g.sort_values('sort_order')


def attribution_counts(fdf):
    """Attribution distribution over the FROZEN heard_bucket column (7 labels,
    display-renamed via ATTRIB_RENAME). Same frozen-bucket rationale as
    schools. Ordered by the frozen ATTRIB_ORDER (full-population count desc,
    Other last)."""
    g = fdf.groupby('heard_bucket', dropna=True).size().reset_index(name='attribution_count')
    g.columns = ['source', 'attribution_count']
    rank = {v: i for i, v in enumerate(ATTRIB_ORDER)}
    g['sort_order'] = g['source'].map(rank).fillna(len(ATTRIB_ORDER))
    return g.sort_values('sort_order')
