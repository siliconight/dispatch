# Dispatch Data Contracts (v0.1)

All positions in upstream files are meters, Blender Z-up by default. Any file
may declare `"up_axis": "y"` to opt out of the `(x, y, z) -> (x, z, -y)`
conversion. Dispatch reads these files; it never writes into upstream build
directories.

## Mission spec — `dispatch.mission.json` (schema `dispatch.mission.v0.1`)

See TDD section 9 and `examples/gas_station_robbery_001/dispatch.mission.json`.
Optional blocks Dispatch honors beyond the TDD example:

```json
{
  "godot":   { "res_root": "res://missions/<mission_id>" },
  "budgets": { "max_props": 400, "max_lights": 48, "max_shadow_lights": 8,
               "max_unique_materials": 96, "max_nav_nodes": 4000 },
  "tuning":  { "anchor_nav_radius": 3.0, "nav_bridge_radius": 1.5,
               "spawn_min_spacing": 1.0, "spawn_clear_radius": 0.5 }
}
```

Input manifests are resolved relative to the spec file. Deli Counter and Lot
are required; Zoo, Patina, Lux optional.

## Anchor record (used by DC and Lot gameplay files)

```json
{ "id": "cash_register", "type": "objective", "pos": [-4, 3.5, 0],
  "rot_y": 0, "tags": ["loot_room"], "objective": "open_cash_register" }
```

`type` is one of: player_start, ai_spawn, objective, door, loot, cover,
patrol_point, extraction, trigger, breach_point, interaction, camera_debug.
Unknown types produce nodes but are not validated. `objective` (or a matching
tag) is what mission-flow steps bind to; `location_tag` steps match tags or
the anchor id. Ids must be unique across ALL inputs.

## Prop placement (optional `props` list in DC/Lot gameplay files)

```json
{ "asset_id": "dumpster_01", "pos": [8, -4, 0], "rot_y": 180 }
```

Resolved against the Zoo catalog and `props/<asset_id>.glb`. Missing GLBs
become Marker3D stubs flagged `missing_asset`.

## Nav hints (`shell.nav_hints.json`, `lot.nav_hints.json`)

```json
{ "schema": "dc.nav_hints.v1", "up_axis": "z",
  "nodes": [ { "id": "door", "pos": [0, -1.5, 0] } ],
  "links": [ ["door", "sales_floor"] ] }
```

Node ids are namespaced per source on merge (`deli_counter:door`). Nodes from
different sources within `nav_bridge_radius` are auto-bridged; every bridge is
reported (no hidden assumptions). Reachability, island detection, and
anchor-to-nav binding (`anchor_nav_radius`) run on this merged graph.

## Deli Counter

```
shell.glb                 building shell (function: collision, traversal)
shell.gameplay.json       { "schema", "up_axis", "anchors": [...], "props": [...] }   <- spec points here
shell.collision.json      optional, passed through to reports
shell.nav_hints.json      nav graph, see above
```

## Lot

```
lot.glb
lot.layout.json           { "schema", "site", "bounds" }                              <- spec points here
lot.gameplay.json         anchors + props, same shape as DC gameplay
lot.nav_hints.json
```

## Zoo

```
zoo.catalog.json          { "assets": [ { "asset_id", "category", "gameplay_tags", ... } ] }
props/<asset_id>.glb      instanced per placement
```

## Patina

```
shell.patina.glb          styled shell mesh -> World/VisualsRoot (presentation, client)
shell.patina.json         { "schema", "materials": [...] }                            <- spec points here
textures/                 copied into the package assets/
```

The DC shell stays instanced under World/BuildingRoot as the function layer
(greybox equals function); Patina never replaces gameplay data.

## Lux

```
lux.profile.json          { "preset", ... } -> LightingRoot metadata               <- spec points here
lux.lighting.json         { "lights": [ { "kind", "shadows" } ] } (budget checks)
lux.volumes.json          passed through
```

Lighting is client presentation. The Lux addon owns the runtime look; Dispatch
records the profile and copies the files to `assets/lux/`.

## Outputs

```
mission.tscn                    Godot 4 scene, format=3, deterministic
mission_config.gd / .tres       compiled flow resource (states + steps + anchor bindings)
mission_runtime.gd              server-authoritative controller skeleton
mission_manifest.json           schema dispatch.manifest.v0.1 — build record
network_authority_map.json      schema dispatch.authority.v0.1 — roots + replication registry
nav/navgraph.json               merged graph (schema dispatch.navgraph.v0.1)
nav/cover_points.json           cover anchors
nav/ai_routes.json              patrol anchors
build.lock.json                 schema dispatch.lock.v0.1 — upstream hashes
validation/report.{md,json,html}
validation/overlays/*.png       nav, spawn, objective_flow, cover (top-down; image x = +X, image y = +Z)
```

Network ids in the replication registry are assigned deterministically by
sorted (anchor type, id) starting at 1000 — stable across rebuilds when
upstream ids are stable.
