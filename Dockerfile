# Build
# docker build -t ofa/ofa .
#
# Run
# docker run --network factory-net --rm -it ofa/ofa bash


FROM python:3.10

# Build arguments
ARG UNAME=ofauser
ARG UID=1001

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
RUN apt-get update
RUN apt-get -y install git
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /ofa

# Creates a non-root user with an explicit UID
RUN adduser --uid ${UID} --disabled-password --gecos "" ${UNAME}

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
