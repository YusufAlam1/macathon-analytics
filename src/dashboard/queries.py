"""
Data Layer - All SQL queries and data loading logic
"""
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit as st

# Database connection
DB_PATH = '../../db/applications.db'
QUERY_PATH = '../analysis/queries/applications/'
FUNNEL_QUERY_PATH = '../analysis/queries/funnel/'

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

@st.cache_data
def load_attribution_data():
    """Load attribution data with renamed source values"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'attribution.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        # Rename source values (not columns)
        rename_map = {
            'Friend/Colleague': 'WOM',
            'Another Discord Server (MLH, HackCanada, etc.)': 'Discord (External)',
            "GDG McMasterU's Discord Server": 'GDG Discord (Internal)'
        }
        df['source'] = df['source'].replace(rename_map)
        return df
    finally:
        conn.close()

@st.cache_data
def load_country_data():
    """Load country data with USA renamed"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'country.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        # Rename United States of America to USA
        df['Country of Residence'] = df['Country of Residence'].replace('United States of America', 'USA')
        return df
    finally:
        conn.close()

@st.cache_data
def load_date_data():
    """Load date frequency data"""
    conn = get_db_connection()
    try:
        query = "SELECT Timestamp FROM applications"
        df = pd.read_sql_query(query, conn)
        
        def clean_timestamp(timestamp):
            if pd.isna(timestamp):
                return None
            date_part = timestamp.split(' ')[0] if ' ' in str(timestamp) else str(timestamp)
            date_part = date_part.replace('-', '/')
            try:
                return datetime.strptime(date_part, '%m/%d/%Y')
            except:
                return None
        
        df['date_clean'] = df['Timestamp'].apply(clean_timestamp)
        df_clean = df[df['date_clean'].notna()].copy()
        daily_counts = df_clean.groupby('date_clean').size().reset_index(name='application_count')
        daily_counts = daily_counts.sort_values('date_clean')
        return daily_counts
    finally:
        conn.close()

@st.cache_data
def load_stem_data():
    """Load STEM distribution data"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'stem.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_programs_data():
    """Load programs distribution data"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'programs.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_age_data():
    """Load age frequency data with renamed categories"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'years.sql', 'r') as f:
            # only the first statement is the chart query; the rest are analysis notes
            query = f.read().split(';')[0]
        df = pd.read_sql_query(query, conn)
        # Rename academic levels
        rename_map = {
            'Freshman': 'Level I',
            'Sophomore': 'Level II',
            'Junior': 'Level III',
            'Senior': 'Level IV',
            'Student+': 'Level V+',
            'Post-Graduate': 'Graduate'
        }
        df['category'] = df['category'].replace(rename_map)
        return df
    finally:
        conn.close()

@st.cache_data
def load_funnel_data():
    """Load the applicant retention funnel (one row per stage)"""
    conn = get_db_connection()
    try:
        with open(FUNNEL_QUERY_PATH + 'funnel_counts.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_experience_data():
    """Load prior hackathon experience distribution"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'experience.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_prev_hacker_data():
    """Load returning-hacker distribution (Jan. 2025)"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'prev_hacker.sql', 'r') as f:
            query = f.read()
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_schools_data():
    """Load school/university distribution"""
    conn = get_db_connection()
    try:
        with open(QUERY_PATH + 'schools.sql', 'r') as f:
            # only the first statement matters; the rest are commented analysis notes
            query = f.read().split('-- Extra')[0]
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def load_acceptance_data():
    """Load acceptance counts for ALL applicants (stem.sql excludes high school,
    so the headline acceptance numbers come straight from applications)"""
    conn = get_db_connection()
    try:
        query = """
            SELECT
                SUM(CASE WHEN "Accepted" = 'Y' THEN 1 ELSE 0 END) AS accepted,
                SUM(CASE WHEN "Accepted" = 'N' THEN 1 ELSE 0 END) AS rejected
            FROM applications
        """
        df = pd.read_sql_query(query, conn)
        return int(df['accepted'][0]), int(df['rejected'][0])
    finally:
        conn.close()

@st.cache_data
def load_response_length_data():
    """Load response length data"""
    conn = get_db_connection()
    
    try:
        with open(QUERY_PATH + 'responses.sql', 'r') as f:
            content = f.read()
        # Split on '--' separator and filter out empty strings
        queries = [q.strip() for q in content.split('--') if q.strip()]
        df_about = pd.read_sql_query(queries[0], conn)
        df_project = pd.read_sql_query(queries[1], conn)
        df_combined = pd.read_sql_query(queries[2], conn)
        return df_about, df_project, df_combined
    finally:
        conn.close()