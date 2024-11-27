FROM python:3.10
LABEL author="Rolf Wuthrich" 
LABEL organisation="Concordia University"
LABEL description="Docker image for OpenFactory influxDB connector"
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
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /home/$UNAME
USER $UNAME

# Import codes into docker image
COPY influxdb_connector.py .

CMD ["python", "influxdb_connector.py"]
