# OpenFactory Devcontainer

The OpenFactory devcontainer is designed to connect to an **external OpenFactory cluster** and an **external Kafka cluster** from within the container.  

The devcontainer acts as an **OpenFactory terminal**. The **host machine** acts as:
- A **single-node OpenFactory cluster**
- A **Kafka cluster** (set up using a dedicated Docker Compose project)

For general information on using devcontainers, see the [Visual Studio Code documentation](https://code.visualstudio.com/docs/devcontainers/containers).

---

## ⚙️ One-Time Setup (on your host machine)

To prepare your host for running the devcontainer:

1. **Define the `HOST_IP` environment variable**  
   Add the following to your `.bashrc` (or equivalent shell config file):

   ```bash
   export HOST_IP=<IP address of your host machine>
   ```

2. **Set up password-less SSH access for the `openfactory` user**  
   From your host machine, run:

   ```bash
   ssh openfactory@$HOST_IP
   ```

   You should connect without being prompted for a password. If not, ensure your SSH key is configured for that user.

3. **[Set up SSH agent forwarding](#ssh-agent-forwarding-setup)** into the devcontainer  
   This is required to securely bring your SSH keys into the container environment.

   Once it's set up, you should be able to run the following *inside the container* without a password:

   ```bash
   ssh openfactory@$HOST_IP
   ```

---

## 🚀 Starting the Devcontainer

Before launching the devcontainer, make sure to:

1. **Start the OpenFactory single-node cluster on your host machine**  
   Use the [`init_infrastructure.py`](init_infrastructure.py) script.

2. **Start the Kafka cluster**  
   From your host machine:

   ```bash
   docker compose -f tests/integration-tests/docker-compose.yml up -d
   ```

---

## 🔐 SSH Agent Forwarding Setup

To access private Git repositories or remote services from within the devcontainer, **SSH agent forwarding** allows you to securely use your SSH key **without copying it into the container**.

### 🛠 One-Time Setup (on your host)

1. **Create or reuse an SSH key**:

   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Add your SSH key to GitHub or your Git service**:  
   Follow GitHub's guide: [Adding a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

3. **Create a helper script to manage the SSH agent**  
   Save this as `~/.ssh/start-agent.sh`:

   ```bash
   #!/bin/bash
   AGENT_ENV="$HOME/.ssh/agent-env"

   # Start agent if not already running
   if ! pgrep -u "$USER" ssh-agent > /dev/null; then
       echo "Starting new SSH agent..."
       eval "$(ssh-agent -s)" > "$AGENT_ENV"
   fi

   # Load the agent environment
   if [ -f "$AGENT_ENV" ]; then
       source "$AGENT_ENV"
   fi

   # Add key if not already loaded
   ssh-add -l > /dev/null 2>&1
   if [ $? -ne 0 ]; then
       ssh-add ~/.ssh/id_ed25519
   fi
   ```

4. **Make the script executable**:

   ```bash
   chmod +x ~/.ssh/start-agent.sh
   ```

5. **Auto-load it in your `.bashrc`**:

   ```bash
   # Start SSH agent and add key
   if [ -f "$HOME/.ssh/start-agent.sh" ]; then
       source "$HOME/.ssh/start-agent.sh"
   fi
   ```

6. **Apply the changes**:

   ```bash
   source ~/.bashrc
   ```

---

### ✅ Testing SSH Access

1. Launch the devcontainer.
2. Inside the container, run:

   ```bash
   ssh -T git@github.com
   ```

You should see something like:

```
Hi your-username! You've successfully authenticated...
```

---

### 🔐 Notes

- Your **private key stays on your host** — it is *never copied* into the container.
- If you're connecting to your host from another machine via SSH, ensure agent forwarding is enabled in your SSH config:

   ```ssh
   Host your-host
     ForwardAgent yes
   ```
