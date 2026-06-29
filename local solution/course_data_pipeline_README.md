# 🎓 Course Data Pipeline for Recommendation Engines

[![Airflow](https://img.shields.io/badge/Airflow-2.9.3-017CEE?style=flat&logo=Apache%20Airflow)](https://airflow.apache.org/)
[![dbt](https://img.shields.io/badge/dbt-1.11.11-FF694B?style=flat&logo=dbt)](https://www.getdbt.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.10.1-FFF000?style=flat&logo=DuckDB)](https://duckdb.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=Docker)](https://www.docker.com/)

A robust, orchestrated data pipeline that unifies online course data from disparate educational platforms (**Coursera**, **Udemy**, and **Udacity**) into a clean, standardized **Star Schema**. 

This pipeline acts as the foundational data infrastructure feeding into our **Course Recommendation System**, ensuring that the machine learning models receive high-quality, perfectly structured, and uniform data.

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Importance for the Recommendation System](#-importance-for-the-recommendation-system)
3. [System Architecture](#-system-architecture)
4. [Data Engineering & Transformation (dbt)](#-data-engineering--transformation-dbt)
5. [Orchestration (Airflow)](#-orchestration-airflow)
6. [Database & Storage (DuckDB)](#-database--storage-duckdb)
7. [How to Run the Project](#-how-to-run-the-project)

---

## 🎯 Project Overview

When aggregating educational content across the internet, data comes in vastly different formats. Udemy structures its courses differently than Coursera, and Udacity uses entirely different naming conventions. 

This project solves the "Data Babel" problem. It takes raw course data from these platforms and utilizes **dbt (data build tool)** to execute a series of transformations:
1. **Cleaning:** Handling nulls, removing duplicates.
2. **Standardizing:** Unifying price formats, durations, levels, and languages across platforms.
3. **Structuring:** Building a Kimbal-style Dimensional Data Warehouse (Star Schema) consisting of 8 dimension tables and 1 central fact table.
4. **Tracking History:** Using Slowly Changing Dimensions (SCD Type 2) to track when courses change titles, descriptions, or URLs over time.

All of this is scheduled and orchestrated automatically using **Apache Airflow** running inside **Docker**.

---

## 🧠 Importance for the Recommendation System

A recommendation system (whether Collaborative Filtering, Content-Based, or Hybrid) operates under the principle of **"Garbage In, Garbage Out."** This data pipeline is absolutely critical for the recommendation engine for several reasons:

1. **Cross-Platform Uniformity**: Without standardization, a model cannot compare a "Beginner" Coursera course with a "Level 1" Udacity course. The pipeline standardizes `level`, `duration`, and `price`, allowing the recommendation algorithm to accurately cluster and suggest courses across different platforms.
2. **Feature Engineering Foundation**: By breaking data into specific dimensions (e.g., `dim_instructor`, `dim_domain`, `dim_language`), the recommendation engine can easily extract distinct user-item interaction features.
3. **Temporal Tracking (SCD Type 2)**: Courses evolve—prices change, titles are updated, and content is refreshed. The implemented `dbt snapshot` tracks historical changes. If a user was recommended a course based on an old syllabus, the system retains that historical context rather than overwriting it, preventing algorithm decay.
4. **Data Trust & Quality**: With 73+ automated data quality tests running on every pipeline execution, the recommendation engine is protected from crashing due to null IDs or broken referential integrity.

---

## 🏗 System Architecture

The project leverages a modern, local-first data stack:

*   **Extraction & Loading (EL)**: Assumed to be completed. Raw data is loaded into `dbt_local.duckdb`.
*   **Transformation (T)**: **dbt-duckdb** transforms the raw data through Staging, Intermediate, and Mart layers.
*   **Database**: **DuckDB**, an ultra-fast, in-process analytical SQL database.
*   **Orchestration**: **Apache Airflow**, containerized via Docker Compose, manages the execution and dependencies of the dbt models.

---

## 🔄 Data Engineering & Transformation (dbt)

The dbt project is structured in layers following best practices:

### 1. Staging (`staging`)
Extracts raw data from `coursera_final_data`, `udemy_final_data`, and `udacity_final_data`. Renames columns to a common standard, casts data types, and applies base filtering.

### 2. Intermediate (`intermediate`)
*   `int_courses_combined`: Unions all three staging tables into a single master table.
*   `int_courses_standardized`: Applies complex business logic to standardize text categories. (e.g., standardizing duration into 'Short', 'Medium', 'Long', and normalizing language strings).

### 3. Snapshots (`snapshots`)
*   `offering_snapshot`: Implements SCD Type 2 tracking on course attributes. It monitors `title`, `description`, `skills`, and `url`. If any of these change, a new record is created with valid `dbt_valid_from` and `dbt_valid_to` timestamps, while keeping the old record for historical analysis.

### 4. Marts / Data Warehouse (`marts`)
Transforms the standardized data into a **Star Schema** optimized for BI tools and ML ingestion.
*   **Dimensions**: 
    *   `dim_date`: Temporal reference.
    *   `dim_domain`: Course subject/domain.
    *   `dim_instructor`: Standardized instructor details.
    *   `dim_language`: Course languages.
    *   `dim_level`: Standardized difficulty levels.
    *   `dim_offering_type`: Format of the offering.
    *   `dim_platform`: Platform details (Coursera/Udemy/Udacity).
    *   `dim_offering`: The core course dimension, built on top of the SCD Type 2 snapshot to include surrogate keys and historical validity.
*   **Fact**: 
    *   `fact_offerings`: The central fact table connecting all dimensions via foreign keys, containing numeric metrics like `price`, `rating`, and `number_of_reviews`.

### 5. Testing
The pipeline executes **73 data quality tests** utilizing the `dbt_utils` package. This includes:
*   `not_null` and `unique` constraints.
*   `accepted_values` for categorical consistency.
*   `relationships` ensuring absolute referential integrity between the Fact table and all Dimension tables.

---

## ⏱ Orchestration (Airflow)

Airflow is used to automate and orchestrate the pipeline. We identified and resolved several architectural challenges to create a robust DAG (`course_data_pipeline`):

### The DAG Execution Flow
The DAG runs under `LocalExecutor` using a specialized Docker environment mapping volume paths seamlessly. It consists of two highly optimized steps:

1. **`dbt_deps`**: Dynamically `cd`s into the dbt project and installs required packages (like `dbt_utils`) to ensure dependencies are present.
2. **`dbt_build`**: A unified execution command that automatically calculates the mathematical Directed Acyclic Graph of the dbt project. 
   * *Why `build` over `run/test`?* Because `offering_snapshot` relies on `int_courses_standardized`. Traditional sequencing (`snapshot` -> `run`) creates a dependency cycle that fails on a fresh database. `dbt build` intelligently sequences staging models, then snapshots, then dimensions, and tests everything simultaneously.

---

## 🗄 Database & Storage (DuckDB)

The entire data warehouse is contained within a single file: `dbt_local.duckdb`.
*   **Why DuckDB?** It allows for lightning-fast OLAP (Online Analytical Processing) queries locally without the overhead of maintaining a remote Postgres or Snowflake instance. 
*   **Integration**: Airflow mounts the DuckDB file and the dbt `profiles.yml` natively resolves the path, meaning the database is accessible to both the Dockerized Airflow scheduler and the local developer.

---

## 🚀 How to Run the Project

### Prerequisites
*   [Docker](https://www.docker.com/) and Docker Compose installed.
*   Ensure `dbt_local.duckdb` is populated with the raw ingestion tables (`coursera_final_data`, `udacity_final_data`, `udemy_final_data`). Without these, `dbt build` will gracefully fail, stating the raw tables are missing.

### Execution Steps
1. **Unzip the Project**: Navigate to the `airflow_home` directory.
2. **Start the Environment**:
   ```bash
   docker compose up -d
   ```
   *This will initialize the database, apply migrations, and start the Webserver and Scheduler. We implemented a custom `airflow-init` container logic to prevent race conditions during boot.*
3. **Access Airflow**:
   Open [http://localhost:8080](http://localhost:8080) in your browser. (Default credentials: `airflow` / `airflow`).
4. **Trigger the Pipeline**:
   *   Locate the `course_data_pipeline` DAG.
   *   Unpause the DAG using the toggle switch.
   *   Click the **"Play"** button to trigger a manual run.
5. **Monitor Logs**: Click on the running tasks (`dbt_deps` or `dbt_build`) to view the live logs as dbt compiles the data warehouse.
6. **Teardown**:
   ```bash
   docker compose down -v
   ```

---
*Built meticulously for robust data aggregation and machine learning readiness.*
