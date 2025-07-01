# Setup an OpenFactory node

1. Install Docker on the node
2. Create the `openfactory` user
   ```
   sudo adduser openfactory
   ```
   Add the user to the `docker` group
   ```
   sudo usermod -aG docker openfactory
   ```
3. Set up a password less ssh access for the openfactory user. 

   Copy the public key of the openfactory user to the node.
   For this, on the OpenFacotry manager log as `openfactory` and copy the key to your node:
   ```
   ssh-copy-id openfactory@<node-ip>
   ```
   Check that your access is password less by running
   ```
   ssh openfactory@<node-ip>
   ```
   Once logged in the node, check your user has the right to manage Docker:
   ```
   docker ps
   ```
