"""
Course Data Pipeline DAG
========================
Orchestrates the dbt pipeline for course data from Coursera, Udemy, and Udacity.

Pipeline steps:
    1. dbt deps      – Install dbt packages (dbt_utils)
    2. dbt seed      – Load CSV seed data into DuckDB
    3. dbt snapshot  – Capture SCD Type 2 snapshots (offering_snapshot)
    4. dbt run       – Build all models (staging → intermediate → marts → semantic)
    5. dbt test      – Run all data quality tests

Trigger: Manual only (schedule_interval=None)

Works with both:
  - Local Airflow: set AIRFLOW_HOME env var (defaults to /opt/airflow)
  - Docker Compose: paths set via env vars in docker-compose.yml
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# ──────────────────────────────────────────────────────────────────────────────
# Path Configuration
# ──────────────────────────────────────────────────────────────────────────────
# Docker: env vars are set in docker-compose.yml
# Local:  env vars should be exported before starting Airflow, or the defaults
#         below will be used (they assume the repo is inside AIRFLOW_HOME).

AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME", "/opt/airflow")

# Where the dbt project lives (contains dbt_project.yml, models/, etc.)
DBT_PROJECT_DIR = os.environ.get(
    "DBT_PROJECT_DIR",
    os.path.join(AIRFLOW_HOME, "course-data-pipeline", "dbt_project"),
)

# Where profiles.yml lives (dbt connection config). We keep it inside dbt_project/
# so the whole project is self-contained and portable.
DBT_PROFILES_DIR = os.environ.get(
    "DBT_PROFILES_DIR",
    os.path.join(AIRFLOW_HOME, "course-data-pipeline", "dbt_project"),
)

# dbt executable — on PATH in Docker; locally may need full path.
DBT_EXECUTABLE = os.environ.get("DBT_EXECUTABLE", "dbt")


def dbt_command(subcommand: str) -> str:
    """Build a dbt CLI command string.

    Adds a trailing space so BashOperator doesn't append a temp filename
    to the last argument (this is a known Airflow BashOperator behavior).
    """
    return (
        f"cd {DBT_PROJECT_DIR} && "
        f"{DBT_EXECUTABLE} {subcommand} "
        f"--project-dir {DBT_PROJECT_DIR} "
        f"--profiles-dir {DBT_PROFILES_DIR} "
    )


# ──────────────────────────────────────────────────────────────────────────────
# Default Arguments
# ──────────────────────────────────────────────────────────────────────────────

default_args = {
    "owner": "course_data_team",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

# ──────────────────────────────────────────────────────────────────────────────
# DAG Definition
# ──────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="course_data_pipeline",
    default_args=default_args,
    description=(
        "End-to-end dbt pipeline for course data from Coursera, Udemy, and Udacity. "
        "Runs: dbt deps → dbt seed → dbt snapshot → dbt run → dbt test."
    ),
    schedule_interval=None,   # Manual trigger only
    catchup=False,
    tags=["dbt", "duckdb", "courses", "etl", "semantic"],
    doc_md=__doc__,
) as dag:

    # ── 1. Install dbt packages ──────────────────────────────────────────────
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=dbt_command("deps"),
        doc_md="Install dbt packages (dbt_utils 1.4.0). Must run first.",
    )

    # ── 2. Seed CSV data into DuckDB ─────────────────────────────────────────
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=dbt_command("seed"),
        doc_md=(
            "Load CSV seed files (coursera_final_data, udacity_final_data, "
            "udemy_final_data) into the DuckDB database. "
            "Must complete before staging models can reference source tables."
        ),
    )

    # ── 3. Snapshot (SCD Type 2) ─────────────────────────────────────────────
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=dbt_command("snapshot"),
        doc_md=(
            "Run the offering_snapshot to capture SCD Type 2 changes. "
            "Must run after seed (needs int_courses_standardized view) "
            "and before dim_offering (which reads the snapshot table)."
        ),
    )

    # ── 4. Build all dbt models ──────────────────────────────────────────────
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=dbt_command("run"),
        doc_md=(
            "Build all dbt models in DAG order: "
            "staging → intermediate → marts (dimensions + facts) → semantic. "
            "The snapshot must exist before this step (dim_offering reads it)."
        ),
    )

    # ── 5. Run all data quality tests ────────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=dbt_command("test"),
        doc_md=(
            "Run all data quality tests: uniqueness, not_null, "
            "accepted_values, relationships, accepted_range. "
            "Runs after all models are built."
        ),
    )

    # ── Task Dependencies ────────────────────────────────────────────────────
    # Linear pipeline: deps → seed → snapshot → run → test
    # This avoids race conditions that occur with `dbt build` where seeds,
    # models, and snapshots run concurrently.
    dbt_deps >> dbt_seed >> dbt_snapshot >> dbt_run >> dbt_test
