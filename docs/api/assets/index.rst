OpenFactory Assets
==================

Two classes, :class:`openfactory.assets.Asset` and :class:`openfactory.assets.AssetUNS` are available to interact with deployed OpenFactory Assets.
The `Asset` class uses the `ASSET_UUID` to identify the Asset, whereas the `AssetUNS` class
uses the UNS (unified namespace) identifier of the Asset.

Both classes are derived from the abstract :class:`openfactory.assets.asset_base.BaseAsset` class.

.. toctree::
   :maxdepth: 2

   assets_base
   assets
   assets_uns

Below are listed additional classes and methods which help manipualting OpenFactory Assets

.. toctree::
   :maxdepth: 2

   assets_utils
