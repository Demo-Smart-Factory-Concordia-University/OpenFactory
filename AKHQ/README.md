# AKHQ - GUI for Apache Kafka

Docker compose instructions to wire up AKHQ a WebApp to monitor Apache Kafka.

The Docker container exports port `7000` to give access to the WebApp.

## Run the Micro-Service
Wire up the micro-service with
```
docker compose -f AKHQ/docker-compose.yml up -d
```

## Accessing the WebApp
The WebApp will be available on http://localhost:7000.

For more information read the official [documentation](https://akhq.io/)