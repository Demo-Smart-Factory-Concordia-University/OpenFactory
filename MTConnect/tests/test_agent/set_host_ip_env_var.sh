#!/bin/bash

# Get the host's IP address
HOST_IP=$(hostname -I | awk '{print $1}')

# Add the export to the .bashrc file to persist across sessions
echo "export HOST_IP=$HOST_IP" >> ~/.bashrc
