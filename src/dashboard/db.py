"""
Database connection — single source of truth.
================================================
Both the pre-filter path (queries.py) and the filtered path (filtered/loaders.py)
get their connection from here, so there is ONE place that decides where the data
comes from.

TWO MODES, chosen automatically at runtime:

  * Turso (remote libSQL) — used when TURSO_DATABASE_URL + TURSO_AUTH_TOKEN are
    present (in Streamlit secrets or env vars). This is the DEPLOYED path: the
    public repo ships no data, and the live app reads the database over the
    network using a token that lives only in Streamlit's Secrets box, never in
    the repo. See the plan and memory `streamlit-deploy-data-delivery`.

  * Local SQLite file — the fallback when no creds are present. This is PLAIN
    LOCAL DEV: it opens ../../db/applications.db exactly as before, so working on
    your machine needs zero setup and cannot accidentally hit the network.

libSQL's connection is DB-API compatible (cursor/execute/fetchall), so the
existing pd.read_sql_query(sql, conn) calls work unchanged in both modes.

To exercise the Turso path locally, put the two values in
src/dashboard/.streamlit/secrets.toml (gitignored) — see secrets.toml.example.
"""
import os

# Local-dev fallback DB. Relative to the Streamlit working dir (src/dashboard/),
# this resolves to the repo-root db/applications.db — same path used before.
LOCAL_DB_PATH = '../../db/applications.db'


def _get_secret(name):
    """Read a secret from Streamlit secrets first, then env vars.

    st.secrets raises (not returns None) when no secrets.toml exists at all —
    the normal plain-local-dev case — so we swallow that and fall through to
    env vars, and ultimately to the local-file fallback.
    """
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


def get_db_connection():
    """Return a DB connection: Turso if creds are present, else the local file."""
    url = _get_secret('TURSO_DATABASE_URL')
    token = _get_secret('TURSO_AUTH_TOKEN')

    if url and token:
        import libsql
        return libsql.connect(database=url, auth_token=token)

    import sqlite3
    return sqlite3.connect(LOCAL_DB_PATH)
