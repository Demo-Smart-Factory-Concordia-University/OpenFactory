# Build
# docker build -t ofa/ofa .
#
# Run
# docker run --network factory-net --rm -it ofa/ofa bash


FROM python:3.10

# Build arguments
ARG UNAME=ofauser
ARG UID=1001
ARG DOCKER_GID=984

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get -y install git && \
    groupadd -g ${DOCKER_GID} docker || true && \
    useradd -m -u ${UID} -G docker -s /bin/bash ${UNAME}

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /ofa

# Copies secrets
RUN mkdir -p /home/${UNAME}/.ssh
COPY ./openfactory/config/secrets /home/${UNAME}/.ssh

# Adds folder permissions
RUN chown -R ${UNAME} /ofa
RUN chown -R ${UNAME} /home/${UNAME}

# Switches to non-root user
USER ${UNAME}
RUN echo "alias ofa='python ofa.py'" > /home/${UNAME}/.bashrc

CMD ["python", "ofa.py"]
