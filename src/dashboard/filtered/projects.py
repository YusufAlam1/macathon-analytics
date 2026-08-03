"""
Filtered dashboard — Devpost project counting (isolated feature)
========================================================================
The "Projects completed" KPI counts PROJECTS (teams), not people. That is a
different number from applications_wide.is_completed, which counts the
individual hackers who finished — teams run 1-4 people, so 179 completers
produced far fewer projects.

Devpost lives in its own two tables, keyed by project title, with no foreign
key to applications_wide:

  devpost         one row per project (title, status, table number, ...)
  devpost_people  one row per team MEMBER (title, first/last name, email)

So the only bridge back to an applicant is the member's EMAIL, matched against
the three email columns an applicant may have filled in. devpost_remap patches
the handful of people whose Devpost email differs from the one they applied
with (private table — see memory `funnel-pii-in-db-table`).

TWO COUNTS, deliberately:

  * TOTAL_SUBMITTED (64) — distinct submitted titles, straight from devpost.
    No join, so nothing is lost. This is the headline shown when no filter is
    active, and it is the number in the sponsorship package.

  * project_count(fdf) — distinct submitted titles with >= 1 team member who
    survived the sidebar filter. Only 60 of the 64 have any matchable member
    (77.8% person-level join coverage), so this is <= 60 and steps DOWN from
    64 the moment a filter is applied. That discontinuity is accepted: the
    unfiltered headline stays true, and the filtered number stays meaningful.

Filtered project counts do NOT sum across filter values: a 4-person team split
across two schools counts once under each school's filter. Counting teams by
member attributes is inherently like that.
"""
import pandas as pd
import streamlit as st

from db import get_db_connection

# Devpost marks abandoned drafts "Draft" and real entries "Submitted
# (Gallery/Visible)" / "Submitted (Hidden)". Only the latter are projects.
SUBMITTED_PREFIX = 'Submitted'

# The applicant email columns, in match priority order. A hacker may have
# applied with a personal address and signed up to Devpost with a school one
# (or vice versa), so all three are candidate keys.
APP_EMAIL_COLS = [
    'Email Address',
    'Preferred Email',
    'McMaster Email (if you are a McMaster student)',
]


def _lower(s):
    """Trimmed, casefolded string series — emails are compared normalized."""
    return s.astype('string').str.strip().str.lower()


@st.cache_data(hash_funcs={dict: lambda d: len(d)})
def load_project_members(app_emails_by_index):
    """Return (members_df, total_submitted).

    members_df has one row per (project title, applicant index) pair that we
    could resolve, so a filtered frame's index is all that's needed to count
    projects downstream. total_submitted is the unjoined 64.

    `app_emails_by_index` is passed in (rather than read from
    applications_wide here) so this stays a pure function of its argument —
    it is a dict of {normalized email: applicant index}. dicts aren't hashable,
    and the lookup is derived from the single cached applications_wide frame
    (so its size is a sufficient cache key).
    """
    conn = get_db_connection()
    try:
        dp = pd.read_sql_query('SELECT * FROM devpost', conn)
        dpp = pd.read_sql_query('SELECT * FROM devpost_people', conn)
        # Private table: absent from a fresh clone that has no PII. The join
        # still works without it, just at a slightly lower match rate, so a
        # missing table degrades the KPI instead of crashing the dashboard.
        try:
            remap = pd.read_sql_query('SELECT * FROM devpost_remap', conn)
        except Exception:
            remap = pd.DataFrame(columns=['devpost_email', 'app_email'])
    finally:
        conn.close()

    submitted = dp.loc[
        dp['Project Status'].astype('string').str.startswith(SUBMITTED_PREFIX, na=False),
        'Project Title',
    ]
    submitted_titles = set(submitted.dropna().unique())
    total_submitted = len(submitted_titles)

    members = dpp[dpp['Project Title'].isin(submitted_titles)].copy()
    email = _lower(members['email'])

    # Patch the known Devpost->application email mismatches before lookup.
    if len(remap):
        patch = dict(zip(_lower(remap['devpost_email']), _lower(remap['app_email'])))
        email = email.map(lambda e: patch.get(e, e))

    members['applicant_index'] = email.map(app_emails_by_index)
    members = members.dropna(subset=['applicant_index'])
    members['applicant_index'] = members['applicant_index'].astype(int)

    return members[['Project Title', 'applicant_index']], total_submitted


def applicant_email_index(df):
    """{normalized email: row index} over every email column an applicant may
    have filled in. First column wins on collision (APP_EMAIL_COLS order)."""
    lookup = {}
    for col in APP_EMAIL_COLS:
        if col not in df.columns:
            continue
        for idx, val in _lower(df[col]).items():
            if pd.notna(val) and val:
                lookup.setdefault(val, idx)
    return lookup


def project_count(members, total_submitted, fdf, filters_active):
    """Projects to display: the true 64 while unfiltered, else the number of
    submitted projects with at least one team member left in `fdf`."""
    if not filters_active:
        return total_submitted
    if not len(fdf) or not len(members):
        return 0
    hit = members['applicant_index'].isin(fdf.index)
    return int(members.loc[hit, 'Project Title'].nunique())
