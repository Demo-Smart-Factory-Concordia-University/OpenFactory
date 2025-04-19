# Dockerfile for OpenFactory Test App
#
# build with:
# docker build -f tests/integration-tests/apps/Dockerfile -t ofa/test-app .

FROM python:3.13-slim-bullseye

ARG UNAME=test_app
ARG UID=1200
ARG GID=1200
ARG VERSION=latest

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Setup non-root user
RUN groupadd --gid $GID $UNAME && \
    useradd --create-home --uid $UID --gid $GID $UNAME

# Install git
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Install OpenFactory
WORKDIR /home/$UNAME
COPY  . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .

# Set environment variable from build argument
ENV APPLICATION_VERSION=${VERSION}

USER $UNAME

CMD ["python3", "-u", "tests/integration-tests/apps/mocked_app.py"]
