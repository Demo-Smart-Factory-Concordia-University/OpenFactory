OpenFactory Deployment Strategies
=================================

OpenFactory Assets are deployed on the OpenFactory cluster using one of the deployment strategy classes listed below.
These classes inherit from the abstract base class :class:`openfactory.openfactory_deploy_strategy.OpenFactoryServiceDeploymentStrategy`.

Currently, two deployment strategies are implemented:

- :class:`openfactory.openfactory_deploy_strategy.LocalDockerDeploymentStrategy`

  Intended for development purposes when no OpenFactory cluster is available.
  This strategy deploys all OpenFactory services as standalone Docker containers on the local machine.

- :class:`openfactory.openfactory_deploy_strategy.SwarmDeploymentStrategy`

  This is the default deployment strategy used in OpenFactory.
  It deploys services as Docker Swarm services, suitable for production or multi-node environments.

.. autoclass:: openfactory.openfactory_deploy_strategy.OpenFactoryServiceDeploymentStrategy
.. autoclass:: openfactory.openfactory_deploy_strategy.LocalDockerDeploymentStrategy
.. autoclass:: openfactory.openfactory_deploy_strategy.SwarmDeploymentStrategy
