# Dispatch

Mission shell assembly, validation, and handoff for Godot 4.7.

> Dispatch validates that a mission shell is ready to receive an authoritative runtime. It does not provide or prove that runtime.

Dispatch combines generated spaces (Deli Counter, Lot), gameplay anchors, presentation layers (Zoo, Patina, Lux), and mission intent into a structurally validated Godot mission shell. It prepares the shell for integration with authoritative gameplay, networking, AI, and mission systems owned by the production game runtime. It generates nothing from scratch, silently fixes nothing, hides no failures — and it implements no mission authority, RPCs, replication, persistence, late-join recovery, or objective/combat/AI behavior.

## Install

```
pip install -e .
```

Pure stdlib at runtime (Python 3.10+). `pytest` for the test suite.

## Quickstart

```
dispatch build examples/gas_station_robbery_001/dispatch.mission.json
```

Exit codes: `0` clean or non-blocking issues, `1` blockers found (reports still written), `2` build could not run (missing files, bad spec).

## Build modes

`shell-handoff` (default) — the integration package: mission scene (Functional / Presentation / Handoff), gameplay anchor registry, runtime ownership requirements, proposed beat graph, navigation hints, validation reports, build lock, and an engineering `HANDOFF.md`. Contains no gameplay or networking code of any kind.

`playtest` / `preview-playtest` (aliases), or `--include-preview` on shell-handoff — adds isolated local walkthrough tooling under `preview_only/`: mock beat progression, calm/alarm toggles, placeholder extraction. Every preview file is headed `# DISPATCH PREVIEW ONLY`; the scene gains a `PreviewOnly/PreviewMissionBridge` node. Nothing in it is production code, delete the folder before integration, and rebuilding without the flag removes it. (Note: v0.1.0's runtime skeleton is not preserved as a legacy mode — playtest is shell-handoff plus preview.)

`runtime-adapter` (`--mode runtime-adapter`) — adds `adapters/` interface stubs: a signal contract, an anchor adapter base, and a registry stub. Signals, data contracts, and example integration methods only — no RPC implementations, replication, persistence, or authoritative progression. Anchors with a matching adapter are marked `adapter_available`.

## CLI

```
dispatch contract                               # machine-readable tool probe (JSON)
dispatch init <mission_id>
dispatch assemble <spec.json> [--mode MODE]     # package, no validation
dispatch validate <spec.json>                   # validation + reports only
dispatch export <spec.json> --target godot [--mode MODE]
dispatch overlays <spec.json>                   # debug overlay PNGs
dispatch build <spec.json> [--mode MODE] [--include-preview] [--strict-licenses]
```

`--out <dir>` overrides the export location. `dispatch contract` is the integration point for pipeline orchestrators (Level Factory): tool version, contract id, modes, schemas, capabilities — parse that, never prose.

## Inputs

Driven by `dispatch.mission.json` (schema `dispatch.mission.v0.2`; v0.1 is still read for compatibility). Deli Counter and Lot are required; Zoo, Patina, and Lux are optional. Contracts in `docs/FORMATS.md`. Coordinates: upstream exports are Blender Z-up; Dispatch converts to Godot Y-up with `(x, y, z) -> (x, z, -y)`, same as the Lux light loader.

## What Dispatch validates

Stable shell IDs; required anchor presence and type consistency; runtime ownership and replication requirement declarations (and their internal consistency); player start coverage; objective and extraction reachability over the merged nav-hint graph; beat-graph bindings; navigation islands; functional/presentation separation; structural performance budgets; duplicate or orphaned anchors; missing integration requirements; **resource closure** on the written package (every `mission.tscn` reference emitted inside the export root, no absolute paths, no tool-repo references — blockers); **anchor parity** (`gameplay_anchors.json` must exactly match the anchors in the written `mission.tscn` — blocking); **license records** (aggregated into `LICENSES.md`; unknown bundled licenses warn by default, block with `--strict-licenses`).

The recommended reading of a green report: every mission-critical anchor has a stable shell ID, a declared runtime ownership requirement, a declared replication requirement, and a valid functional-layer placement.

## What Dispatch cannot and does not validate

Actual server authority, RPC security, replication correctness, network prediction, reconciliation, late-join recovery, reconnect behavior, persistence correctness, objective behavior, enemy behavior, combat balance, final gameplay pacing, matchmaking, or shipping online playability. Dispatch never claims online gameplay has been verified. The readiness score is structural only — and it is not a fun score.

## Identity model

Anchors carry stable, deterministic **shell IDs** (`gameplay_anchors.json`), namespaced by mission id (`gas_station_robbery_001/front_door`) so imported missions cannot collide. These are not network IDs — a shell ID is a stable content key. The production runtime maps each shell ID to its own network entity, replicated actor, gameplay component, or save-state record; `runtime_binding` ships as `null` and `integration_status` as `unimplemented` or `adapter_available`. Only the production pipeline sets `integrated` / `verified_by_game_runtime`.

## Using the package in Godot

Copy the exported mission folder to the spec's `godot.res_root` (default `res://missions/<mission_id>/`) and open `mission.tscn`. Read `HANDOFF.md` first: it lists every gameplay-critical anchor, its declared requirements, and everything the game runtime must implement. The `NavigationRegion3D` under `Functional/NavigationHints` is a stub marked `bake_required` — bake in-editor; Dispatch does no geometry processing. GDScript emitted by preview/adapter modes follows the pipeline's standing caveat: engine walk before anything builds on it.

## Rebuild safety and provenance

Every generated node carries `metadata/dispatch_generated`; the root carries `[DISPATCH_GENERATED]` and the build mode. `build.lock.json` (schema `dispatch.build_lock.v0.2`) records the spec hash, every consumed input hash by role, and every produced file hash — Level Factory wraps it in its own lock. `resource_manifest.json` hashes every package file and asserts `requires_editor_plugins: false` / `requires_autoloads: false`: the package is consumable without Dispatch installed. Package content is byte-deterministic for unchanged inputs (the lock's `created_at` and report timestamps are the only varying bytes). Handoff scenes contain no node named Runtime, MissionController, AuthorityController, NetworkController, or ReplicationController — enforced by tests.
