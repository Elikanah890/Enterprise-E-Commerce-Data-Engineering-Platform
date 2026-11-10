FROM apache/airflow:2.9.3

USER airflow

RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.11.txt" \
    "apache-airflow==2.9.3" \
    "apache-airflow-providers-postgres" \
    "numpy>=1.26" \
    "pandas==2.1.4" \
    "python-dotenv>=1.0"
