# https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html#initializing-environment

mkdir -p ./dags ./logs ./plugins ./config
echo -e "AIRFLOW_UID=$(id -u)" > .env