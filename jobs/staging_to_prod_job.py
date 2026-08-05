"""
STAGING -> PROD — publish the local SQLite database to hosted Turso.
=========================================================================
The deploy step for this project's data. The public repo ships code only; the
live Streamlit app reads its data from Turso at runtime. This job takes the
local staging database and replaces the remote tables with it.

Replaces the old manual workflow (`sqlite3 .dump` into a .sql text file, then
feeding it to `turso db shell` by hand). It reads db/applications_turso.db
directly and replays it over libsql, so there is no intermediate dump file that
can silently go stale, and no dependency on the turso CLI being installed.

Usage, from the repo root:
    python jobs/staging_to_prod_job.py --dry-run   # show what would happen
    python jobs/staging_to_prod_job.py             # actually publish

Credentials come from src/dashboard/.streamlit/secrets.toml (gitignored, and
the same file the dashboard reads), or from TURSO_DATABASE_URL /
TURSO_AUTH_TOKEN env vars, which take precedence. This file is committed, so
it must never contain the credentials themselves.

Pipeline order — the staging DB is the source of truth for what goes live, so
rebuild it before publishing:
    1. rebuild applications_wide   (src/analysis/queries/filtered/build_applications_wide.sql)
    2. python jobs/staging_to_prod_job.py --dry-run
    3. python jobs/staging_to_prod_job.py

NOTE: this REPLACES the remote tables, and is not atomic — tables are dropped
and refilled one at a time, so a mid-run network failure leaves prod partially
populated. Re-running the job fixes that. Avoid publishing while the dashboard
is being demoed.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_DB = REPO_ROOT / 'db' / 'applications_turso.db'
SECRETS = REPO_ROOT / 'src' / 'dashboard' / '.streamlit' / 'secrets.toml'

# Rows per executescript batch. Turso is a network hop, so we batch rather than
# sending 845 individual round-trips.
BATCH = 200


def load_credentials():
    """Env vars win; otherwise parse the same secrets.toml the dashboard reads."""
    url = os.environ.get('TURSO_DATABASE_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    if url and token:
        return url, token

    if not SECRETS.exists():
        sys.exit(f'No credentials: set env vars or create {SECRETS}')

    try:
        import tomllib  # py3.11+
        data = tomllib.loads(SECRETS.read_text(encoding='utf-8'))
    except ModuleNotFoundError:
        data = {}
        for line in SECRETS.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip().strip('"').strip("'")

    url = url or data.get('TURSO_DATABASE_URL')
    token = token or data.get('TURSO_AUTH_TOKEN')
    if not url or not token:
        sys.exit(f'TURSO_DATABASE_URL / TURSO_AUTH_TOKEN missing from {SECRETS}')
    return url, token


def quote(identifier):
    """Quote a table/column name for SQL.

    Some survey-export columns contain literal double quotes (e.g. the devpost
    column named '"Try it out" Links'). SQLite escapes an embedded " inside a
    quoted identifier by doubling it, so naive f'"{name}"' produces a syntax
    error. Always route identifiers through here.
    """
    return '"' + identifier.replace('"', '""') + '"'


def read_schema(conn):
    """(name, create_sql) for every user table, in dependency-free order."""
    return conn.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


def push(dry_run=False):
    if not STAGING_DB.exists():
        sys.exit(f'Staging DB not found: {STAGING_DB}')

    local = sqlite3.connect(f'file:{STAGING_DB}?mode=ro', uri=True)
    tables = read_schema(local)
    if not tables:
        sys.exit('Staging DB has no tables — refusing to push an empty database.')

    print(f'Staging: {STAGING_DB}')
    counts = {}
    for name, _ in tables:
        counts[name] = local.execute(f'SELECT COUNT(*) FROM {quote(name)}').fetchone()[0]
        print(f'  {name:<20} {counts[name]:>6} rows')
    total = sum(counts.values())

    url, token = load_credentials()
    # Never print the token; the URL alone identifies the target.
    print(f'\nTarget:  {url}')

    if dry_run:
        print(f'\n[dry run] would replace {len(tables)} tables / {total} rows. Nothing sent.')
        local.close()
        return

    import libsql
    remote = libsql.connect(database=url, auth_token=token)

    for name, create_sql in tables:
        print(f'\n{name}')
        remote.execute(f'DROP TABLE IF EXISTS {quote(name)}')
        remote.execute(create_sql)

        cols = [c[1] for c in local.execute(f'PRAGMA table_info({quote(name)})')]
        placeholders = ','.join('?' * len(cols))
        collist = ','.join(quote(c) for c in cols)
        insert = f'INSERT INTO {quote(name)} ({collist}) VALUES ({placeholders})'

        sent = 0
        cur = local.execute(f'SELECT {collist} FROM {quote(name)}')
        while True:
            rows = cur.fetchmany(BATCH)
            if not rows:
                break
            remote.executemany(insert, rows)
            sent += len(rows)
            print(f'\r  {sent}/{counts[name]}', end='', flush=True)
        remote.commit()
        print(f'\r  {sent}/{counts[name]} done')

    print('\nVerifying remote row counts...')
    ok = True
    for name, _ in tables:
        n = remote.execute(f'SELECT COUNT(*) FROM {quote(name)}').fetchone()[0]
        flag = '' if n == counts[name] else '  <-- MISMATCH'
        if n != counts[name]:
            ok = False
        print(f'  {name:<20} {n:>6} (local {counts[name]}){flag}')

    remote.close()
    local.close()
    print('\nPush complete.' if ok else '\nPush finished WITH MISMATCHES — investigate before trusting prod.')
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Publish the local staging SQLite database to hosted Turso (prod).')
    ap.add_argument('--dry-run', action='store_true',
                    help='show tables/rows and the target, send nothing')
    push(**vars(ap.parse_args()))