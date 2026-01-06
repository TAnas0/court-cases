FROM apache/airflow:3.1.3

USER root
RUN apt-get update && apt-get install -y ca-certificates

USER airflow
RUN pip install --upgrade pip setuptools wheel

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt


COPY . .
RUN pip install -e .
