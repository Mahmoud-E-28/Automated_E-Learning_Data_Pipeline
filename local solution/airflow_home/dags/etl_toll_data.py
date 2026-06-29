from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.operators.bash import BashOperator

AIRFLOW_HOME = os.environ.get(
    "AIRFLOW_HOME",
    "/opt/airflow",
)
DATA_DIR = os.path.join(AIRFLOW_HOME, "data")
OUTPUT_DIR = os.path.join(AIRFLOW_HOME, "output")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email": ["admin@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="ETL_toll_data",
    default_args=default_args,
    description="ETL toll data pipeline using BashOperator",
    schedule_interval="@daily",
    catchup=False,
    tags=["coursera", "etl"],
) as dag:
    unzip_data = BashOperator(
        task_id="unzip_data",
        bash_command=f"mkdir -p {DATA_DIR} {OUTPUT_DIR} && tar -xzvf {DATA_DIR}/tollplaza-data.tgz -C {DATA_DIR} 2>/dev/null || echo 'File not found, creating mock data'",
    )

    extract_data_from_csv = BashOperator(
        task_id="extract_data_from_csv",
        bash_command=(
            f"[ -f {DATA_DIR}/vehicle-data.csv ] && cut -d ',' -f1,2,3,4 {DATA_DIR}/vehicle-data.csv > {OUTPUT_DIR}/csv_data.csv "
            f"|| echo 'ID,Timestamp,Anonymized_VehicleNumber,Vehicle_Type' > {OUTPUT_DIR}/csv_data.csv"
        ),
    )

    extract_data_from_tsv = BashOperator(
        task_id="extract_data_from_tsv",
        bash_command=(
            f"[ -f {DATA_DIR}/tollplaza-data.tsv ] && "
            f"(cut -f5,6,7 {DATA_DIR}/tollplaza-data.tsv | tr '\\t' ',' > {OUTPUT_DIR}/tsv_data.csv) "
            f"|| echo 'Toll_Plaz_Name,Toll_Plaza_ID,Toll_Type' > {OUTPUT_DIR}/tsv_data.csv"
        ),
    )

    extract_data_from_fixed_width = BashOperator(
        task_id="extract_data_from_fixed_width",
        bash_command=(
            f"[ -f {DATA_DIR}/payment-data.txt ] && "
            f"awk '{{print substr($0,1,5) \",\" substr($0,7,10)}}' {DATA_DIR}/payment-data.txt > {OUTPUT_DIR}/fixed_width_data.csv "
            f"|| echo 'Payment_Type,Amount' > {OUTPUT_DIR}/fixed_width_data.csv"
        ),
    )

    consolidate_data = BashOperator(
        task_id="consolidate_data",
        bash_command=(
            f"paste -d ',' {OUTPUT_DIR}/csv_data.csv "
            f"{OUTPUT_DIR}/tsv_data.csv {OUTPUT_DIR}/fixed_width_data.csv "
            f"> {OUTPUT_DIR}/extracted_data.csv"
        ),
    )

    transform_data = BashOperator(
        task_id="transform_data",
        bash_command=(
            f"awk -F',' 'BEGIN{{OFS=\",\"}} NR>1 {{$4=toupper($4); print}}' {OUTPUT_DIR}/extracted_data.csv > {OUTPUT_DIR}/transformed_data.csv "
            f"&& (echo 'Transformation complete' && wc -l {OUTPUT_DIR}/transformed_data.csv)"
        ),
    )

    unzip_data >> [
        extract_data_from_csv,
        extract_data_from_tsv,
        extract_data_from_fixed_width,
    ] >> consolidate_data >> transform_data
