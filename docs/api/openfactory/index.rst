OpenFactory Core API
=====================

OpenFactory exposes three core classes to interact with the platform, depending on the use case:

- :class:`openfactory.openfactory.OpenFactory`

  Used by OpenFactory Assets to interact with the platform. No special privileges are required.

- :class:`openfactory.openfactory_manager.OpenFactoryManager`

  Used by OpenFactory administrators responsible for deploying Assets on the cluster.  
  Requires Docker access on at least one OpenFactory manager node.

- :class:`openfactory.openfactory_cluster.OpenFactoryCluster`

  Used by infrastructure administrators responsible for managing the OpenFactory cluster itself.  
  Requires Docker access on at least one manager node **and** SSH access to all OpenFactory nodes.

.. toctree::
   :maxdepth: 2

   openfactory
   openfactory_manager
   openfactory_cluster
   openfactory_deploy_strategies
