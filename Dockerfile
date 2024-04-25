# Build
# docker build -t ofa/ofa .
#
# Run
# docker run --network factory-net --rm -it ofa/ofa bash


FROM python:3.10

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
COPY . /ofa

# Creates a non-root user with an explicit UID
# Copies secrets
# Adds permission to access the /ofa folder
RUN mkdir -p /home/appuser/.ssh
COPY ./openfactory/config/secrets /home/appuser/.ssh
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /ofa
RUN chown -R appuser /home/appuser
USER appuser
RUN echo "alias ofa='python ofa.py'" > /home/appuser/.bashrc

CMD ["python", "ofa.py"]
