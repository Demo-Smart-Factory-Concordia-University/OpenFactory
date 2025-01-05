FROM python:3.10
LABEL author="Rolf Wuthrich" 
LABEL organisation="Concordia University"
LABEL description="Docker image for OpenFactory InfluxDB connector"
LABEL documentation="https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory"

ARG UNAME=influxdb_connector
ARG UID=1200
ARG GID=1200

RUN groupadd --gid $GID $UNAME
RUN useradd --create-home --uid $UID --gid $GID $UNAME

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
RUN apt-get update
RUN apt-get -y install git
RUN python -m pip install influxdb-client
RUN python -m pip install git+https://github.com/rwuthric/PyKSQL.git

USER $UNAME
WORKDIR /home/$UNAME/influxdb

# Import codes into docker image
RUN mkdir influxdb
COPY sinkconnector.py .
COPY influxdb/influxdb_connector.py influxdb
COPY influxdb/service.py influxdb
COPY influxdb/__init__.py influxdb

WORKDIR /home/$UNAME
CMD ["python", "-m", "influxdb.influxdb.service"]
