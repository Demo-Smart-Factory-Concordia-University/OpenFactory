# OpenFactory environmen variables
To run properly, OpenFactory needs some environment variables to be defined. They must be added into the file `.ofaenv` at the top of the project directory. OpenFactory will use this file to setup the variables as needed. For example, it will first setup these variables before parsing the OpenFactory configuration file `openfactory/config/openfactory.yml`.

The following variables need to be defined:
- `MANAGER_NODE_IP`: IP address of the machine used to manage OpenFactory
- `MTCONNECT_AGENT_CFG_FILE`: the location of the configuration file of the MTConnect Agents. Unless the structure of the project is changed or a cusotm configuration file is needed, this has to be set to `openfactory/ofa/agent/configs/agent.cfg`

Important note:
After updating the `.ofaenv`, make sure to restart all services of OpenFactory.
