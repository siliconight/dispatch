# Dispatch Data Contracts (v0.2)

All positions in upstream files are meters, Blender Z-up by default. Any file
may declare `"up_axis": "y"` to opt out of the `(x, y, z) -> (x, z, -y)`
conversion. Dispatch reads these files; it never writes into upstream build
directories.

## Mission spec — `dispatch.mission.json` (schema `dispatch.mission.v0.2`; v0.1 read for compatibility)

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

## License records (delta D10)

Any input manifest may carry:

```json
"license": { "name": "proprietary-siliconight", "source": "...", "notes": "..." }
```

Absent = `unknown`. Aggregated into `LICENSES.md`; unknown bundled licenses
warn by default and block under `--strict-licenses`.

## Contract probe (delta D12)

`dispatch contract` prints JSON: tool, version, contract id, modes, emitted
schemas, capabilities. Pipeline adapters must parse this instead of prose.

## Outputs

```
mission.tscn                          Godot 4 scene: Functional / Presentation / Handoff
                                      (+ PreviewOnly in preview mode); format=3, deterministic
mission_manifest.json                 schema dispatch.manifest.v0.2 — build record incl. mode
gameplay_anchors.json                 schema dispatch.gameplay_anchors.v0.2 — flat shell-id
                                      registry (namespaced <mission_id>/<anchor_id>), sorted by
                                      shell_id: transform, tags, source_tool, source_building,
                                      required_authority, expected_adapter, integration_status,
                                      runtime_binding (always null from Dispatch),
                                      runtime_requirements. Validated to exactly match the
                                      anchors in mission.tscn (blocking).
proposed_beat_graph.json              schema dispatch.proposed_beat_graph.v0.2 — design intent
                                      only: beats (id, type: location|objective|extraction|
                                      trigger|carry, status: always "proposed", shell_ids)
                                      + connections
runtime_ownership_requirements.json   schema dispatch.runtime_ownership_requirements.v0.2 —
                                      requirements, not a map: per-anchor declarations the
                                      production runtime must satisfy (owner, replication,
                                      late-join state, persistence); integration_status always
                                      "unimplemented" here. No networking library, RPC names,
                                      serialization, or network entity IDs are prescribed.
navigation_hints.json                 schema dispatch.navigation_hints.v0.2 — merged node/edge
                                      graph; auto-bridge edges flagged bridged:true with the
                                      bridge_radius that produced them; navmesh: bake_required
resource_manifest.json                schema dispatch.resource_manifest.v0.2 — every package
                                      file with sha256; requires_editor_plugins/autoloads: false
LICENSES.md                           aggregated upstream license records
HANDOFF.md                            engineering handoff: verbatim boundary language,
                                      integration checklist, non-claims
build.lock.json                       schema dispatch.build_lock.v0.2 — spec hash, per-role
                                      input hashes, per-file output hashes, created_at
assets/                               functional geometry (shell.glb, lot.glb, collision manifest)
presentation/                         patina shell, textures, lux files, prop GLBs
validation/report.{md,json,html}      BLUF-first; integration_ready flag; "not validated" list
validation/overlays/*.png             nav, spawn, objective_flow, cover (top-down; x=+X, y=+Z)
preview_only/preview_mission_bridge.gd    preview-playtest mode only; # DISPATCH PREVIEW ONLY header
adapters/*.gd                         runtime-adapter mode only; interface stubs, no RPCs
```

Shell IDs are stable, deterministic build identifiers — never network IDs.
Integration status values Dispatch may emit: `unimplemented`,
`adapter_available`. `integrated` and `verified_by_game_runtime` belong to the
production game pipeline.
