FROM apache/airflow:latest

USER root
RUN apt-get update && apt-get install -y ca-certificates

USER airflow
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# FIX WARN: UndefinedVar: Usage of undefined variable '$PYTHONPATH'
ENV PYTHONPATH="/opt/airflow:/opt/airflow/src:$PYTHONPATH"
