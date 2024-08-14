# OpenFactory Node setup
Each OpenFactory node requires
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

3. Make sure the entry `OPENFACTORY_USER:` in the [OpenFactory yml configuration file](../openfactory/config/openfactory.yml) is equal to the user created :
   ```
   OPENFACTORY_USER: openfactory
   ```

4. On the OpenFactory manager machine, as OpenFactory user, create an SSH key (if not yet already done):
   ```
   ssh-keygen
   ```
   If the key had to be generated, add it to the `secrets` folder of OpenFactory

5. Copy the ssh key to the node:
   ```
   ssh-copy-id <node>
   ```
   where `<node>` is the addess of the node to setup

6. Verify you can ssh into the node without password:
   ```
   ssh <node>
   ```

7. Add the node to the `known_hosts` file in the `secrets` folder of OpenFactory
