
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

MAG_ENV    = 'set -a && source /opt/airflow/.env.mag && set +a'
BAK_ENV    = 'set -a && source /opt/airflow/.env.bak && set +a'
MAG_PYTHON = 'PYTHONPATH=/opt/airflow/etl_mag_modular python'
BAK_PYTHON = 'PYTHONPATH=/opt/airflow/etl_bak_modular python'
MAG_MAIN   = '/opt/airflow/etl_mag_modular/main.py'
BAK_MAIN   = '/opt/airflow/etl_bak_modular/main.py'

def mag_cmd(script: str) -> str:
    return f'{MAG_ENV} && {MAG_PYTHON} {script}'

def bak_cmd(script: str) -> str:
    return f'{BAK_ENV} && {BAK_PYTHON} {script}'

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 17),
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'etl_dwh_combined',
    default_args=default_args,
    description='MAG + BAK: fetch Excel → STG(incr) → ODS → DDS → MART',
    schedule_interval='* 5 * * *',
    max_active_runs=1,
    catchup=False,
    tags=['etl', 'dwh', 'daily'],
)

start = EmptyOperator(task_id='start', dag=dag)
done  = EmptyOperator(task_id='done',  dag=dag)

fetch_mag = BashOperator(
    task_id='fetch_mag',
    bash_command=mag_cmd(
        '/opt/airflow/etl_mag_modular/fetch.py '
        '--folder "{{ var.value.get("FOLDER_MAG", "/opt/airflow/data/mag") }}" --run'
    ),
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

fetch_bak = BashOperator(
    task_id='fetch_bak',
    bash_command=bak_cmd(
        '/opt/airflow/etl_bak_modular/fetch.py '
        '--folder "{{ var.value.get("FOLDER_BAK", "/opt/airflow/data/bak") }}" --run'
    ),
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

ods_mag = BashOperator(task_id='ods_mag', dag=dag,
    bash_command=mag_cmd(f'{MAG_MAIN} --layer ods --run'),
    execution_timeout=timedelta(minutes=20))

ods_bak = BashOperator(task_id='ods_bak', dag=dag,
    bash_command=bak_cmd(f'{BAK_MAIN} --layer ods --run'),
    execution_timeout=timedelta(minutes=20))

dds_mag = BashOperator(task_id='dds_mag', dag=dag,
    bash_command=mag_cmd(f'{MAG_MAIN} --layer dds --run'),
    execution_timeout=timedelta(minutes=25))

dds_bak = BashOperator(task_id='dds_bak', dag=dag,
    bash_command=bak_cmd(f'{BAK_MAIN} --layer dds --run'),
    execution_timeout=timedelta(minutes=25))

mart_mag = BashOperator(task_id='mart_mag', dag=dag,
    bash_command=mag_cmd(f'{MAG_MAIN} --layer mart --run'),
    execution_timeout=timedelta(minutes=10))

mart_bak = BashOperator(task_id='mart_bak', dag=dag,
    bash_command=bak_cmd(f'{BAK_MAIN} --layer mart --run'),
    execution_timeout=timedelta(minutes=10))

start >> [fetch_mag, fetch_bak]

fetch_mag >> ods_mag >> dds_mag >> mart_mag
fetch_bak >> ods_bak >> dds_bak >> mart_bak

[mart_mag, mart_bak] >> done
