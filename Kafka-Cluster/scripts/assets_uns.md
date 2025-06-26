# Topology for OpenFactory Assets by Unified Namespace

The topology for OpenFactory assets classified by Unified Namespace is defined in the script [assets\_uns.sql](assets_uns.sql).

## Mapping

The mapping between each asset's physical identifier (`ASSET_UUID`) and its logical identifier (`UNS_ID`) is defined in the source table `asset_to_uns_map_raw`.

This mapping allows applications to refer to assets by their stable role (`UNS_ID`), even if the underlying physical device (`ASSET_UUID`) changes.

## Stream of Asset Events Keyed by `UNS_ID`

The ksqlDB stream `assets_stream_uns` mirrors the original `assets_stream`, but events are rekeyed by `UNS_ID`.
This enables event-driven applications to process data based on logical asset roles in the production line.

## Table of Asset States Keyed by `UNS_ID|ID`

The ksqlDB table `assets_uns` mirrors the original `assets` table but uses the composite key `UNS_ID|ID`.
This supports efficient lookups and stateful operations using Unified Namespace identifiers instead of physical UUIDs.

## Example to Insert a Map
To insert a map between the `ASSET_UUID` `PROVER3018` and the `UNS_ID` `cnc`:
```sql
INSERT INTO asset_to_uns_map_raw (asset_uuid, uns_id, updated_at) 
VALUES ('PROVER3018', 'cnc', '2025-06-23T10:00:00Z');
```
This will populate the `assets_stream_uns` stream and `assets_uns` table with data.

## Example to Remove a Map
To remove a map between the `ASSET_UUID` `PROVER3018` and the `UNS_ID` `cnc`:
```sql
INSERT INTO asset_to_uns_map_raw (asset_uuid, uns_id, updated_at) 
VALUES ('PROVER3018', NULL, '2025-06-23T10:00:00Z');
```
This will remove the entries in the `assets_uns` table and stop creating events in the `assets_stream_uns` stream.
