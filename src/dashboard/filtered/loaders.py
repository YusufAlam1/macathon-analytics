"""
Filtered dashboard — data layer (isolated feature)
====================================================
Reads the ONE BIG TABLE `applications_wide` (raw applications + funnel flags +
gdg survey columns — see src/analysis/queries/filtered/build_applications_wide.sql)
and adds the mapped bucket columns in pandas.

ARCHITECTURE (user-decided 2026-07-21):
  * applications_wide holds RAW values only (no buckets/mappings/thresholds).
  * Filtering = pandas WHERE clauses on raw columns (filters.py).
  * Mappings are PORTED to pandas here for runtime speed, but the SQL CASE
    blocks in src/analysis/queries/applications/*.sql are the CANONICAL spec.
    Each map_* function below mirrors one .sql file — keep them in lockstep;
    if you change the .sql, change the mirror (and vice-versa). Doc-links on
    each function name the source file.
  * Thresholds (schools <20, attribution >5) depend on the FILTERED
    population's counts, so they run post-filter (see aggregations.py), never
    as a per-row column here.

Nothing here is imported by the pre-filter dashboard path; the whole package
can be removed to revert.
"""
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# Shared connection helper: Turso when deployed (creds in secrets), local
# ../../db/applications.db for local dev. Single source of truth — see db.py.
from db import get_db_connection


# ---------------------------------------------------------------------------
# Timestamp parsing — mirrors queries.py load_date_data's clean_timestamp.
# ---------------------------------------------------------------------------
def clean_timestamp(timestamp):
    if pd.isna(timestamp):
        return None
    date_part = timestamp.split(' ')[0] if ' ' in str(timestamp) else str(timestamp)
    date_part = date_part.replace('-', '/')
    try:
        return datetime.strptime(date_part, '%m/%d/%Y')
    except Exception:
        return None


# ===========================================================================
# PANDAS MAPPINGS — each mirrors one canonical .sql file. Column names are the
# raw applications_wide columns. Keep in lockstep with the source .sql.
# ===========================================================================

# Raw column name constants (verbatim applications headers)
_COL_PROGRAM = "Which of the following best describes your program?"
_COL_LEVEL = "This hackathon is open to students only. What is your level of study?"
_COL_SCHOOL = ("Which school/college/university are you currently enrolled in? "
               "(If your school/institution is not in the list below, use this "
               "list to find a school/institution and paste it in 'Other')")
_COL_COUNTRY = "Country of Residence"
_COL_AGE = "Age (ex. 20)"


def map_program_type(df):
    """Mirrors src/analysis/queries/applications/programs.sql `clean` CTE.
    Keep in lockstep with that file's CASE. NOTE: SQLite LIKE is
    case-INSENSITIVE, so every match here uses case=False to match."""
    program = df[_COL_PROGRAM].fillna('')
    level = df[_COL_LEVEL].fillna('')
    out = pd.Series('Other', index=df.index)
    # applied last-WHEN-first so the earliest SQL WHEN wins (mask overwrites)
    out = out.mask(program.str.contains('Technology', case=False, na=False), 'Technology')
    out = out.mask(program.str.contains('^Business', case=False, na=False, regex=True), 'Business')
    out = out.mask(program.str.contains('^Math', case=False, na=False, regex=True), 'Math')
    out = out.mask(program.str.contains('Engineering', case=False, na=False), 'Engineering')
    out = out.mask(program.str.contains('Computer Science', case=False, na=False), 'Software')
    out = out.mask(level == 'Secondary/High School', 'High School')
    return out


# programs.sql sort_order
PROGRAM_ORDER = ['Software', 'Engineering', 'Math', 'Business', 'Technology', 'Other', 'High School']


def map_academic_year(df):
    """Mirrors src/analysis/queries/applications/years.sql `clean` CTE.
    Age column is text; compare with str ops as the SQL LIKE does."""
    level = df[_COL_LEVEL].fillna('')
    age = df[_COL_AGE].astype('string').fillna('')
    age_num = pd.to_numeric(df[_COL_AGE], errors='coerce')

    out = pd.Series('Other', index=df.index)
    # order mirrors the SQL WHEN chain, applied last-wins so put the FIRST
    # SQL WHEN last here
    out = out.mask((age_num >= 23) & level.str.startswith('Undergraduate'), 'Student+')
    out = out.mask(age_num.between(21, 22), 'Senior')
    out = out.mask(age_num == 20, 'Junior')
    out = out.mask(age_num == 19, 'Sophomore')
    out = out.mask(age.str.startswith('18') | (age_num == 17), 'Freshman')
    out = out.mask(
        level.str.startswith('Grad') | level.str.contains('grad ', na=False)
        | level.str.startswith('Master') | level.str.contains('lenovo', case=False, na=False),
        'Post-Graduate')
    out = out.mask(level == 'Secondary/High School', 'Highschool')
    return out


# years.sql category order (raw names). Student+ (Level V+) sits before
# Post-Graduate (Graduate) so the chart reads ... Level IV, Level V+, Graduate.
ACADEMIC_ORDER_RAW = ['Highschool', 'Freshman', 'Sophomore', 'Junior', 'Senior',
                      'Senior (co-op)', 'Student+', 'Post-Graduate', 'Other']
# Display renames applied for the chart labels (mirrors load_age_data in queries.py)
ACADEMIC_RENAME = {
    'Freshman': 'Level I', 'Sophomore': 'Level II', 'Junior': 'Level III',
    'Senior': 'Level IV', 'Student+': 'Level V+', 'Post-Graduate': 'Graduate',
    'Highschool': 'High School',
}
ACADEMIC_ORDER = [ACADEMIC_RENAME.get(c, c) for c in ACADEMIC_ORDER_RAW]


def map_country_bucket(df):
    """Mirrors src/analysis/queries/applications/country.sql `mapped` CTE
    (currently the 2-level Canada / International split)."""
    country = df[_COL_COUNTRY].fillna('')
    return np.where(country.str.lower() == 'canada', 'Canada', 'International')


COUNTRY_ORDER = ['Canada', 'International']


# The six schools that clear the 20-count threshold on the FULL 845 (see
# schools.sql output). This set is FROZEN — a fact of the complete applicant
# pool, NOT recomputed per filtered view (user decision 2026-07-21: hard-coded
# count thresholds don't hold under granular filters, so bake the buckets the
# full-population threshold produces and keep them fixed). Schools that match a
# LIKE clause but fall UNDER 20 (Laurier 14, Ontario Tech 8, Carleton 9) are
# NOT here — they fold into Other Canada, exactly as schools.sql rolls them up.
NAMED_SCHOOLS_KEPT = {
    'McMaster University', 'University of Waterloo', 'University of Toronto',
    'York University', 'University of Guelph', 'Western University',
}

# Frozen 10-label school order — mirrors schools.sql's output ordering:
# named schools by full-population count (desc), then College, High School,
# Other Canada, Other International.
SCHOOL_ORDER = [
    'McMaster University', 'University of Waterloo', 'University of Toronto',
    'York University', 'University of Guelph', 'Western University',
    'College', 'High School', 'Other Canada', 'Other International',
]


def map_school_group(df):
    """Frozen school bucket, one of the 10 SCHOOL_ORDER labels. Mirrors
    src/analysis/queries/applications/schools.sql END-TO-END (the per-row
    `school_mapping` CASE **and** the <20 tail rollup), but with the rollup
    FROZEN to the full-population result instead of recomputed per filtered
    view. Concretely: run the same LIKE-normalization SQL does (so York's
    'Yorku'/'York university' variants collapse to the 28-count 'York
    University' group, etc.), then any normalized value NOT in
    NAMED_SCHOOLS_KEPT (and not College/High School) becomes Other Canada /
    Other International by country of residence. High School / College are
    never folded.

    Why frozen and not a filtered recompute: the 20 threshold is a hard-coded
    number that stops being meaningful once a filter shrinks the population
    (every school would collapse to Other). Freezing to what the full pool
    produces keeps the filter option list and chart labels stable and
    identical. As a consequence the in-view counts still move with the filter,
    but the SET of buckets never does."""
    school = df[_COL_SCHOOL].fillna('')
    level = df[_COL_LEVEL].fillna('')
    country = df[_COL_COUNTRY].fillna('')

    # --- Step 1: SQL school_mapping CASE, verbatim (name-normalization only).
    # SQLite LIKE is case-INSENSITIVE -> case=False everywhere. Masks applied
    # last-WHEN-first so the earliest SQL WHEN wins on overlaps.
    mapped = school.copy()  # ELSE school (raw string, e.g. 'University of Guelph')
    is_college = ((school.str.contains('college', case=False, na=False)
                   | school.str.contains('polytechnic', case=False, na=False))
                  & (country == 'Canada'))
    mapped = mapped.mask(is_college, 'College')
    mapped = mapped.mask(school.str.contains('Carleton', case=False, na=False), 'Carleton University')
    mapped = mapped.mask(school.str.contains('Ontario', case=False, na=False)
                         & school.str.contains('Tech', case=False, na=False), 'Ontario Tech University')
    mapped = mapped.mask(school.str.contains('York', case=False, na=False), 'York University')
    mapped = mapped.mask(school.str.contains('Western', case=False, na=False), 'Western University')
    mapped = mapped.mask(school.str.contains('laurier', case=False, na=False), 'Wilfrid Laurier University')
    mapped = mapped.mask(school.str.contains('Waterloo', case=False, na=False), 'University of Waterloo')
    mapped = mapped.mask(school.str.contains('University of Toronto', case=False, na=False), 'University of Toronto')
    mapped = mapped.mask(school.str.contains('McMaster', case=False, na=False), 'McMaster University')
    mapped = mapped.mask(level == 'Secondary/High School', 'High School')

    # --- Step 2: frozen tail-fold.
    # schools.sql thresholds per (mapped_school, RAW country) pair. Every named
    # group that clears 20 is the CANADA group (verified on the full pool), so
    # the frozen rule is: a NAMED_SCHOOLS_KEPT label survives only for
    # Canada-resident applicants; its international stragglers (e.g. the 3
    # McMaster-International, 1 Waterloo-International) fold to Other
    # International — matching schools.sql's 308/168 exactly. College is
    # already Canada-only by its mapping. High School is level-based and never
    # folds (stays 'High School' regardless of country).
    is_canada = country.str.strip().str.lower() == 'canada'
    keep = (mapped.isin(NAMED_SCHOOLS_KEPT) & is_canada) | mapped.isin(['College', 'High School'])
    fallback = np.where(is_canada.values, 'Other Canada', 'Other International')
    return pd.Series(np.where(keep.values, mapped.values, fallback), index=df.index)


# ---------------------------------------------------------------------------
# Attribution ("How did you hear about us?") — frozen buckets.
# ---------------------------------------------------------------------------
# The sources that clear the >5 threshold on the FULL 845 (see attribution.sql
# output). FROZEN for the same reason as schools: the >5 cutoff is a fixed
# number that would swallow real sources into Other under a small filter. So
# the KEPT set is decided once on the full pool and never recomputed.
ATTRIB_SOURCES_KEPT = [
    'Instagram',
    'Friend/Colleague',
    'MLH Website',
    'Another Discord Server (MLH, HackCanada, etc.)',
    "GDG McMasterU's Discord Server",
    'LinkedIn',
]

# Display-only relabel, applied to BOTH the chart and the filter options
# (user decision 2026-07-21) so the two always agree. This is cosmetic on top
# of the canonical buckets — the underlying value stays the raw SQL string.
ATTRIB_RENAME = {
    'Friend/Colleague': 'WOM',
    'Another Discord Server (MLH, HackCanada, etc.)': 'Discord (External)',
    "GDG McMasterU's Discord Server": 'GDG Discord (Internal)',
}

# Frozen attribution order (raw canonical values, count-desc on the full pool),
# with Other last. Display labels are ATTRIB_RENAME.get(v, v).
ATTRIB_ORDER_RAW = ATTRIB_SOURCES_KEPT + ['Other']
ATTRIB_ORDER = [ATTRIB_RENAME.get(v, v) for v in ATTRIB_ORDER_RAW]


def map_heard_source(df):
    """Frozen attribution bucket: one of the 6 kept sources (display-renamed)
    or 'Other'. Mirrors src/analysis/queries/applications/attribution.sql, but
    with the >5 rollup FROZEN to the full-population result rather than the
    filtered view. Any raw source not in ATTRIB_SOURCES_KEPT -> 'Other'; then
    ATTRIB_RENAME is applied so the value matches the chart label."""
    src = df["How did you hear about us?"]
    folded = src.where(src.isin(ATTRIB_SOURCES_KEPT), 'Other')
    return folded.replace(ATTRIB_RENAME)


EXPERIENCE_ORDER = ['None', '1', '2 - 3', '4+']

FUNNEL_STAGE_ORDER = ['Applied', 'Accepted', 'RSVPed', 'Attended', 'Completed Project']
# "Reached-at-least stage X" = the row's is_X flag directly. The funnel is 5
# INDEPENDENT counts (proof-of-presence can skip a tracked stage), so this is
# NOT a monotone chain — filter on the flag, not on a synthesized depth.
STAGE_TO_FLAG = {
    'Applied': 'is_applied',
    'Accepted': 'is_accepted',
    'RSVPed': 'is_rsvped',
    'Attended': 'is_attended',
    'Completed Project': 'is_completed',
}


@st.cache_data
def load_applicants_wide():
    """Load the raw applications_wide table and add derived + mapped columns.
    No filter args — caches the single unfiltered frame; filtering happens on
    a copy downstream (filters.py)."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query('SELECT * FROM applications_wide', conn)
    finally:
        conn.close()

    # is_applied is trivially true for every applicant; the other flags come
    # straight from the table as 0/1 ints -> booleans for pandas convenience
    df['is_applied'] = True
    for c in ['is_accepted', 'is_rsvped', 'is_attended', 'is_completed']:
        df[c] = df[c].astype(bool)

    # derived date
    df['app_date'] = df['Timestamp'].apply(clean_timestamp)

    # mapped bucket columns (pandas mirrors of the .sql CASE blocks).
    # school_group and heard_bucket are FROZEN canonical labels (10 / 7) that
    # filters AND charts share — see map_school_group / map_heard_source.
    df['program_type'] = map_program_type(df)
    df['academic_year'] = pd.Series(map_academic_year(df)).replace(ACADEMIC_RENAME)
    df['country_bucket'] = map_country_bucket(df)
    df['school_group'] = map_school_group(df)
    df['heard_bucket'] = map_heard_source(df)

    # raw dimensions used directly by filters/charts
    df['experience'] = df["How many hackathons have you attended in the past?"]
    df['attended_last_year'] = df["Were you a hacker at Mac-a-Thon last time (Jan. 2025)?"]
    df['heard_source'] = df["How did you hear about us?"]  # raw, pre-fold (kept for reference)

    # response lengths for the histograms
    about = ("Answer this short answer question in 5 sentences or less: "
             "Tell us about yourself, and why you would like to attend the Mac-a-Thon.")
    proj = ("Answer this short answer question in 5 sentences or less: "
            "What is a project that you recently worked on? This does not have "
            "to be related to computer science or software.")
    df['about_length'] = df[about].astype('string').str.len()
    df['project_length'] = df[proj].astype('string').str.len()
    df['response_length'] = df['about_length'].fillna(0) + df['project_length'].fillna(0)

    # furthest funnel stage touched — DISPLAY ONLY (see STAGE_TO_FLAG note)
    stage_flags = ['is_applied', 'is_accepted', 'is_rsvped', 'is_attended', 'is_completed']

    def furthest(row):
        depth = 0
        for i, f in enumerate(stage_flags):
            if row[f]:
                depth = i
        return FUNNEL_STAGE_ORDER[depth]

    df['funnel_stage_reached'] = df[stage_flags].apply(furthest, axis=1)

    return df


def school_order(df=None):
    """The frozen 10-label school order (SCHOOL_ORDER). Takes an optional df
    for call-site compatibility, but the order no longer depends on the data —
    it's fixed to the full-population ranking baked into SCHOOL_ORDER."""
    return list(SCHOOL_ORDER)
