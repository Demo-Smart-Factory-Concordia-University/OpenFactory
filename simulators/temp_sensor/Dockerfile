FROM python:3.13-slim
LABEL author="Rolf Wuthrich" 
LABEL organisation="Concordia University"
LABEL description="Docker image for OpenFactory Temperature Sensor simulator"
LABEL documentation="https://github.com/Demo-Smart-Factory-Concordia-University/OpenFactory"

ARG UNAME=ofa
ARG UID=1200
ARG GID=1200

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN groupadd --gid $GID $UNAME
RUN useradd --create-home --uid $UID --gid $GID $UNAME
RUN apt-get update
RUN apt-get -y install git

# python dependencies
RUN pip install git+https://github.com/Demo-Smart-Factory-Concordia-University/MTCAdapters.git

WORKDIR /home/$UNAME
USER $UNAME

COPY adapter.py .

CMD ["python3", "-u", "adapter.py"]
