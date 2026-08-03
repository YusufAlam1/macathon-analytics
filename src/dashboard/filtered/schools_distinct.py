"""
Filtered dashboard — distinct-school counting for the "Schools represented" KPI
==============================================================================
This is NOT the frozen 10-bucket `school_group` mapping in loaders.py. That one
exists to keep chart labels and filter options in permanent agreement, so it
folds everything small into "Other Canada" / "Other International" — buckets,
not schools. Counting distinct values of it would be meaningless here.

This module answers a different question: how many REAL institutions are in the
data? It works off the raw free-text school column, because that column is the
only place the actual institution names survive.

The raw column is user-entered, so the same school arrives spelled many ways:

    University of Waterloo / university of waterloo / University Of Waterloo / Waterloo
    Sheridan College / Sheridan college / Sheridan College Institute of Technology...
    Western University / University of Western Ontario
    University of Toronto - Downtown / - Mississauga / - Scarborough / Scarborough

Counting raw distinct values therefore OVERSTATES reach (164 distinct values for
~80 real schools, Waterloo counted 4 times). Normalizing first, THEN applying a
">1 applicant" threshold, means the threshold removes genuine one-off schools
rather than deleting real schools that happen to be misspelled.

The rules below are deliberately mechanical (casefold, strip campus suffixes,
unify a few known synonyms). They are not exhaustive — a handful of stragglers
like "humber" vs "humber college" stay split — but they need no maintenance as
new data arrives, which a hand-written alias list would.
"""
import re

import pandas as pd

# The raw free-text school question. Long, but it is the literal column name.
SCHOOL_RAW_COL = (
    "Which school/college/university are you currently enrolled in? "
    "(If your school/institution is not in the list below, use this list to "
    "find a school/institution and paste it in 'Other')"
)

# Campus qualifiers: U of T's three campuses are one university for a
# "how many schools" count. Matched at the end of the string only.
_CAMPUS_SUFFIX = re.compile(r'\s*[-,]?\s*(downtown|mississauga|scarborough|st\.? george)\s*$')

# Institutions that renamed or that people write out in full/short form.
_SYNONYMS = [
    (re.compile(r'\binstitute of technology and advanced learning\b'), ''),
    (re.compile(r'\bpolytechnic\b'), 'college'),
    (re.compile(r'university of western ontario'), 'western university'),
]

# Bare campus-town / short names that unambiguously mean one institution.
_BARE = {
    'waterloo': 'university of waterloo',
    'mcmaster': 'mcmaster university',
    'humber': 'humber college',
    'seneca': 'seneca college',
    'sheridan': 'sheridan college',
}


def normalize_school(value):
    """Raw free-text school -> a canonical comparison key (or None).

    Casefolds, drops punctuation, strips campus suffixes and applies the
    synonym rules, so all the spellings of one institution collapse to a
    single key. The result is a MATCHING key, not a display label — it is
    lowercase and punctuation-free by design.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().lower()
    if not s:
        return None

    s = _CAMPUS_SUFFIX.sub('', s)
    for pattern, repl in _SYNONYMS:
        s = pattern.sub(repl, s)

    # Strip punctuation last so "st. george" / "queen's" match above first.
    s = re.sub(r'[^a-z ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    return _BARE.get(s, s) or None


def distinct_school_count(fdf, min_applicants=2):
    """Number of distinct schools in `fdf` with at least `min_applicants` rows.

    The threshold drops true one-offs (a single applicant from a school we
    otherwise have no presence at) — the normalization above is what keeps it
    from silently deleting real schools over a typo.
    """
    if SCHOOL_RAW_COL not in fdf.columns or not len(fdf):
        return 0
    keys = fdf[SCHOOL_RAW_COL].map(normalize_school).dropna()
    if not len(keys):
        return 0
    counts = keys.value_counts()
    return int((counts >= min_applicants).sum())
