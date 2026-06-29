"""
Scrape & Transform Pipeline DAG
================================
End-to-end pipeline that scrapes Udemy course data, aligns the CSV output
to the dbt seed schema, and runs the full dbt pipeline.

Pipeline steps:
    1. validate_cookie   – Check if the Udemy cookie is still valid
    2. scrape_udemy      – Run the Udemy scraper (main.py)
    3. align_and_copy    – Rename/reorder columns, copy CSV to dbt seeds/
    4. dbt_deps          – Install dbt packages
    5. dbt_seed          – Load CSV seed data into DuckDB
    6. dbt_snapshot      – Capture SCD Type 2 snapshots
    7. dbt_run           – Build all models (staging → intermediate → marts → semantic)
    8. dbt_test          – Run all data quality tests

Trigger: Manual only (schedule_interval=None)
"""

import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Path Configuration
# ──────────────────────────────────────────────────────────────────────────────

AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME", "/opt/airflow")

# Udemy Scraper paths
UDEMY_SCRAPER_DIR = os.path.join(AIRFLOW_HOME, "udemy_scraper", "udemy_scraper")
UDEMY_OUTPUT_CSV = os.path.join(UDEMY_SCRAPER_DIR, "data", "udemy_courses.csv")

# Udacity Scraper paths
UDACITY_SCRAPER_DIR = os.path.join(AIRFLOW_HOME, "udacity_scraper")
UDACITY_OUTPUT_CSV = os.path.join(UDACITY_SCRAPER_DIR, "udacity_courses_complete.csv")

# Coursera Scraper paths
COURSERA_SCRAPER_DIR = os.path.join(AIRFLOW_HOME, "coursera_scraper")
COURSERA_OUTPUT_CSV = os.path.join(COURSERA_SCRAPER_DIR, "output", "coursera_courses.csv")

# dbt paths
DBT_PROJECT_DIR = os.environ.get(
    "DBT_PROJECT_DIR",
    os.path.join(AIRFLOW_HOME, "course-data-pipeline", "dbt_project"),
)
DBT_PROFILES_DIR = os.environ.get(
    "DBT_PROFILES_DIR",
    os.path.join(AIRFLOW_HOME, "course-data-pipeline", "dbt_project"),
)
DBT_SEED_DIR = os.path.join(DBT_PROJECT_DIR, "seeds")
DBT_EXECUTABLE = os.environ.get("DBT_EXECUTABLE", "dbt")

UDEMY_SEED_CSV = os.path.join(DBT_SEED_DIR, "udemy_final_data.csv")
UDACITY_SEED_CSV = os.path.join(DBT_SEED_DIR, "udacity_final_data.csv")
COURSERA_SEED_CSV = os.path.join(DBT_SEED_DIR, "coursera_final_data.csv")


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def dbt_command(subcommand: str) -> str:
    """Build a dbt CLI command string."""
    return (
        f"cd {DBT_PROJECT_DIR} && "
        f"{DBT_EXECUTABLE} {subcommand} "
        f"--project-dir {DBT_PROJECT_DIR} "
        f"--profiles-dir {DBT_PROFILES_DIR} "
    )


def align_and_copy_csv(**context):
    """
    Read the scraper output CSV, align columns to match the dbt seed schema,
    and copy it to the dbt seeds directory.

    Scraper outputs:
        course_id, Course_Title, Course_URL, Platform, Language, Description,
        Skills, Level, Price, No_of_Reviews, No_of_Students_enrolled,
        Programming_Instructor, Last_Update, Type_of_Course, Duration

    dbt seed expects:
        course_id, Course_Title, Course_URL, Platform, Language, Description,
        Skills, Level, Price, No_of_Reviews, No_of_Students,
        Programming_Instructor, Last_Update, Type_of_Course, Duration,
        offering_Type, rate, price model
    """
    # --- Process Udemy ---
    if os.path.exists(UDEMY_OUTPUT_CSV):
        logger.info(f"Reading Udemy output: {UDEMY_OUTPUT_CSV}")
        df_udemy = pd.read_csv(UDEMY_OUTPUT_CSV, encoding="utf-8-sig")
        unnamed = [c for c in df_udemy.columns if c.startswith("Unnamed")]
        if unnamed: df_udemy = df_udemy.drop(columns=unnamed)
        df_udemy = df_udemy.rename(columns={"No_of_Students_enrolled": "No_of_Students"})
        if "offering_Type" not in df_udemy.columns: df_udemy["offering_Type"] = "Course"
        if "rate" not in df_udemy.columns: df_udemy["rate"] = ""
        if "price model" not in df_udemy.columns:
            df_udemy["price model"] = df_udemy["Price"].apply(
                lambda p: "Free" if str(p).strip().lower() in ("free", "0", "") else "One Time"
            )
        if "course_id" in df_udemy.columns:
            df_udemy = df_udemy.drop_duplicates(subset=["course_id"], keep="last")
        os.makedirs(DBT_SEED_DIR, exist_ok=True)
        df_udemy.to_csv(UDEMY_SEED_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df_udemy)} Udemy rows to {UDEMY_SEED_CSV}")
    else:
        logger.warning("Udemy output CSV not found. Skipping Udemy alignment.")

    # --- Process Udacity ---
    if os.path.exists(UDACITY_OUTPUT_CSV):
        logger.info(f"Reading Udacity output: {UDACITY_OUTPUT_CSV}")
        df_udacity = pd.read_csv(UDACITY_OUTPUT_CSV, encoding="utf-8-sig")
        unnamed = [c for c in df_udacity.columns if c.startswith("Unnamed")]
        if unnamed: df_udacity = df_udacity.drop(columns=unnamed)
        
        # Add required dbt seed columns for Udacity if missing
        if "monthly_price" not in df_udacity.columns: df_udacity["monthly_price"] = ""
        if "offering_type" not in df_udacity.columns: df_udacity["offering_type"] = "Course"
        if "Avg_Rating" not in df_udacity.columns: df_udacity["Avg_Rating"] = ""
        if "Review_Count" not in df_udacity.columns: df_udacity["Review_Count"] = ""
        if "Best_Category" not in df_udacity.columns: df_udacity["Best_Category"] = ""
        
        # Rename to match Udacity seed schema
        rename_map = {
            "No. of Reviews / Ratings": "Review_Count",
            "No. of Students enrolled": "enrolled_students",
            "Type of Course": "offering_type",
            "Duration": "Duration_Hours",
            "Price": "Price_Model"
        }
        df_udacity = df_udacity.rename(columns=rename_map)
        
        if "course_id" in df_udacity.columns:
            df_udacity = df_udacity.drop_duplicates(subset=["course_id"], keep="last")
        df_udacity.to_csv(UDACITY_SEED_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df_udacity)} Udacity rows to {UDACITY_SEED_CSV}")
    else:
        logger.warning("Udacity output CSV not found. Skipping Udacity alignment.")

    # --- Process Coursera ---
    if os.path.exists(COURSERA_OUTPUT_CSV):
        logger.info(f"Reading Coursera output: {COURSERA_OUTPUT_CSV}")
        df_coursera = pd.read_csv(COURSERA_OUTPUT_CSV, encoding="utf-8-sig")
        unnamed = [c for c in df_coursera.columns if c.startswith("Unnamed")]
        if unnamed: df_coursera = df_coursera.drop(columns=unnamed)
        
        # Add required dbt seed columns for Coursera if missing
        if "monthly_price" not in df_coursera.columns: df_coursera["monthly_price"] = ""
        if "offering_type" not in df_coursera.columns: df_coursera["offering_type"] = "Course"
        if "Best_Category" not in df_coursera.columns: df_coursera["Best_Category"] = ""
        
        # Rename to match Coursera seed schema
        rename_map = {
            "No. of Reviews / Ratings": "Review_Count",
            "No. of Students enrolled": "enrolled_students",
            "Type_of_Course": "offering_type",
            "Duration": "Duration_Hours",
            "Price": "Price_Model"
        }
        df_coursera = df_coursera.rename(columns=rename_map)
        
        if "course_id" in df_coursera.columns:
            df_coursera = df_coursera.drop_duplicates(subset=["course_id"], keep="last")
        df_coursera.to_csv(COURSERA_SEED_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df_coursera)} Coursera rows to {COURSERA_SEED_CSV}")
    else:
        logger.warning("Coursera output CSV not found. Skipping Coursera alignment.")

    # Push stats to XCom for downstream visibility
    context["ti"].xcom_push(key="udemy_rows", value=len(df_udemy) if 'df_udemy' in locals() else 0)
    context["ti"].xcom_push(key="udacity_rows", value=len(df_udacity) if 'df_udacity' in locals() else 0)
    context["ti"].xcom_push(key="coursera_rows", value=len(df_coursera) if 'df_coursera' in locals() else 0)


# ──────────────────────────────────────────────────────────────────────────────
# Default Arguments
# ──────────────────────────────────────────────────────────────────────────────

default_args = {
    "owner": "course_data_team",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,          # Scraping is long; don't auto-retry the whole thing
    "retry_delay": timedelta(minutes=5),
}

# ──────────────────────────────────────────────────────────────────────────────
# DAG Definition
# ──────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="scrape_and_transform",
    default_args=default_args,
    description=(
        "End-to-end pipeline: scrape Udemy → align CSV → "
        "dbt seed → snapshot → run → test."
    ),
    schedule_interval=None,   # Manual trigger only
    catchup=False,
    tags=["scraper", "dbt", "duckdb", "udemy", "etl", "full-pipeline"],
    doc_md=__doc__,
) as dag:

    # ── 1. Validate cookie ───────────────────────────────────────────────────
    validate_cookie = BashOperator(
        task_id="validate_cookie",
        bash_command=(
            f'cd {UDEMY_SCRAPER_DIR} && '
            'python3 -c "'
            'from config import HEADERS; '
            'from curl_cffi import requests as r; '
            'resp = r.get('
            '    \\"https://www.udemy.com/api-2.0/courses/1565838/\\", '
            '    headers=HEADERS, '
            '    impersonate=\\"chrome120\\", '
            '    timeout=15'
            '); '
            'print(f\\"Status: {resp.status_code}\\"); '
            'assert resp.status_code == 200, '
            'f\\"Cookie expired or invalid! Status: {resp.status_code}. '
            'Please refresh cookie.txt\\"; '
            'print(\\"✅ Cookie is valid\\")'
            '" '
        ),
        doc_md=(
            "Quick HTTP request to Udemy API to verify the cookie.txt is still "
            "valid. Fails immediately with a clear message if the cookie has "
            "expired, saving you from a long scrape that would fail mid-way."
        ),
    )

    # ── 2. Scrape Udemy ──────────────────────────────────────────────────────
    scrape_udemy = BashOperator(
        task_id="scrape_udemy",
        bash_command=(
            f"cd {UDEMY_SCRAPER_DIR} && "
            "python3 main.py "
        ),
        execution_timeout=timedelta(hours=8),  # Scraping can take hours
        doc_md=(
            "Runs the Udemy scraper (main.py). Iterates over all 13 Udemy "
            "categories, fetching course data via GraphQL and REST APIs. "
            "Supports resume from checkpoint (state.json). "
            "Output: data/udemy_courses.csv"
        ),
    )

    # ── 2.5 Scrape Udacity ───────────────────────────────────────────────────
    scrape_udacity = BashOperator(
        task_id="scrape_udacity",
        bash_command=(
            f"cd {UDACITY_SCRAPER_DIR} && "
            "python3 main.py "
        ),
        execution_timeout=timedelta(hours=8),
        doc_md="Runs the Udacity scraper (main.py) with 10 threads.",
    )

    # ── 2.6 Scrape Coursera ──────────────────────────────────────────────────
    scrape_coursera = BashOperator(
        task_id="scrape_coursera",
        bash_command=(
            f"cd {COURSERA_SCRAPER_DIR} && "
            "pip install cloudscraper beautifulsoup4 && "
            "python3 main.py "
        ),
        execution_timeout=timedelta(hours=8),
        doc_md="Runs the Coursera scraper (main.py).",
    )

    # ── 3. Align & copy CSVs to seeds ────────────────────────────────────────
    align_and_copy = PythonOperator(
        task_id="align_and_copy_csvs",
        python_callable=align_and_copy_csv,
        doc_md=(
            "Reads Udemy, Udacity, and Coursera output CSVs, aligns schemas to match "
            "dbt expectations, deduplicates, and copies to seeds/."
        ),
    )

    # ── 4. dbt deps ──────────────────────────────────────────────────────────
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=dbt_command("deps"),
        doc_md="Install dbt packages (dbt_utils).",
    )

    # ── 5. dbt seed ──────────────────────────────────────────────────────────
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=dbt_command("seed"),
        doc_md="Load CSV seed files into DuckDB.",
    )

    # ── 6. dbt snapshot ──────────────────────────────────────────────────────
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=dbt_command("snapshot"),
        doc_md="Run the offering_snapshot (SCD Type 2).",
    )

    # ── 7. dbt run ───────────────────────────────────────────────────────────
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=dbt_command("run"),
        doc_md="Build all dbt models: staging → intermediate → marts → semantic.",
    )

    # ── 8. dbt test ──────────────────────────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=dbt_command("test"),
        doc_md="Run all data quality tests.",
    )

    # ── Task Dependencies ────────────────────────────────────────────────────
    # Scrapers (in parallel) → align_and_copy → dbt chain
    validate_cookie >> scrape_udemy
    [scrape_udemy, scrape_udacity, scrape_coursera] >> align_and_copy >> dbt_deps >> dbt_seed >> dbt_snapshot >> dbt_run >> dbt_test
