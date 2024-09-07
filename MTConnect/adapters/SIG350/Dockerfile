# build: docker build -t ofa/sig350 .
FROM python:3.10
LABEL author="Rolf Wuthrich" description="Docker image for SIG350 adapter"

# Build arguments
ARG UNAME=ofauser
ARG UID=1001

# Creates a non-root user with an explicit UID
RUN adduser --uid ${UID} --disabled-password --gecos "" ${UNAME}

# Install MTCAdapters
RUN pip install git+https://git@github.com/Demo-Smart-Factory-Concordia-University/MTCAdapters.git --upgrade

WORKDIR /ofa
ADD sig350adapter.py /ofa/sig350adapter.py

# Switches to non-root user
USER ${UNAME}

CMD [ "python3", "-u", "sig350adapter.py" ]
