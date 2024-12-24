# Test Agent

This Docker Compose project sets up an agent based on the Docker image created by the GitHub workflow [mtc_agent.yml](../../../.github/workflows/mtc_agent.yml).

### Deploying the Agent

To deploy the Agent using Docker Compose:

```bash
docker compose up -d
```

This will start the Agent in detached mode, running on port `5555`.

### Running the Adapter

To verify if the Agent responds as expected to the adapter, run the following command:

```bash
python adapter.py
```

The adapter will listen for incoming connections on port `7800` (or any other port you’ve configured) and should interact with the Agent running in the Docker container.

### Verifying the Setup

- Once the Agent is running, it will be available on port `5555` for connections.
- The adapter will send `|avail|AVAILABLE` to the Agent.
- The Agent should recognise the SHDR message.

If everything is set up correctly, the adapter will show any received data from the Agent in the terminal.
