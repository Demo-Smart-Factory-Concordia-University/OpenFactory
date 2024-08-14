# OpenFactory Manager Node setup
The OpenFactory manager node requires
1. Docker installed
2. An OpenFactory user which is a member of the `docker` group
3. SSH password less access to the node from the OpenFactory manger machine for the OpenFactory user

## Setup OpenFactoryUser
Any user account can be used, but it must be the same username across all OpenFactory nodes and it must be added to the [OpenFactory yml configuration file](../openfactory/config/openfactory.yml) under the field `OPENFACTORY_USER`. For example
```
...
# OpenFactory User
OPENFACTORY_USER: openfactory
...
```
### Detailed steps
1. Create the OpenFactory user account:
   ```
   sudo adduser openfactory
   ```

2. Add user `openfactory` to the `docker` group:
   ```
   sudo usermod -aG docker openfactory
   ```

3. Make sure the entry `OPENFACTORY_USER:` in the [OpenFactory yml configuration file](../openfactory/config/openfactory.yml) is equal to the user created:
   ```
   OPENFACTORY_USER: openfactory
   ```

4. On the OpenFactory manager node, as OpenFactory user, create an SSH key:
   ```
   ssh-keygen
   ```

5. Add the `secrets` folder of OpenFactory
   ```
   cp .ssh/id_rsa /path/to/secrets
   ```
   Note: if the user that will run OpenFactory on the manager machine is different than the OpenFactory user, 
   then make sure to adjust the ownership and file permissions correctly of the copied key.

6. Copy the ssh key to the manager node (the OpenFactory user must be able to ssh from the manger node into the manager node without password):
   ```
   ssh-copy-id <manager-node-ip>
   ```

7. Verify you can ssh into the manager node without password:
   ```
   ssh <manager-node-ip>
   ```
   
8. Add the manager machine to the `known_hosts` file in the `secrets` folder of OpenFactory
