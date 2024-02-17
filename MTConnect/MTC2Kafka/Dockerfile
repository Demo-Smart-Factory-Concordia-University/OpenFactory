FROM python:3.10-slim
LABEL author="Rolf Wuthrich" 
LABEL organisation="Concordia University"
LABEL description="Docker image for Kafka producer"
LABEL documentation="https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory"

ARG UNAME=producer
ARG UID=1200
ARG GID=1200

RUN groupadd --gid $GID $UNAME
RUN useradd --create-home --uid $UID --gid $GID $UNAME
RUN apt-get update
RUN apt-get -y install git

# kafka-python library
RUN pip install git+https://github.com/rwuthric/python-mtc2kafka.git --upgrade

WORKDIR /home/$UNAME
USER $UNAME

COPY kafka_producer.py .

CMD ["python3", "-u", "kafka_producer.py"]