FROM python:3.10
LABEL author="Rolf Wuthrich" description="Docker image for SIG350 adapter"

# Build arguments
ARG UNAME=ofauser
ARG UID=1001

# Creates a non-root user with an explicit UID
RUN adduser --uid ${UID} --disabled-password --gecos "" ${UNAME}

# Install python modules
RUN pip install requests

WORKDIR /ofa

# Switches to non-root user
USER ${UNAME}

CMD "tail -F anything"
