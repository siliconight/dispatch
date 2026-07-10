# Dispatch

Online mission assembly and validation for Godot 4.7.

> Assemble the mission. Validate the mission. Package the mission for online play.

Dispatch is the orchestration layer above Deli Counter, Lot, Zoo, Patina, and Lux. It imports their outputs, assembles a Godot 4.7 mission scene, validates that the mission is playable as server-authoritative 1-4 player online co-op, and packages the result for playtest. It generates nothing from scratch, silently fixes nothing, and hides no failures.

## Install

```
pip install -e .
```

Pure stdlib at runtime (Python 3.10+). `pytest` for the test suite.

## Quickstart

```
dispatch build examples/gas_station_robbery_001/dispatch.mission.json
```

Produces `examples/gas_station_robbery_001/export/godot/missions/gas_station_robbery_001/` containing `mission.tscn`, `mission_manifest.json`, `network_authority_map.json`, `mission_config.tres`, `mission_runtime.gd`, `nav/`, `build.lock.json`, and `validation/` (report.md / .json / .html + overlay PNGs).

Exit codes: `0` clean or non-blocking issues, `1` blockers found (reports still written), `2` build could not run (missing files, bad spec).

## CLI

```
dispatch init <mission_id>           # scaffold a spec + build folders
dispatch assemble <spec.json>        # resolve + write the Godot package (no validation)
dispatch validate <spec.json>        # validation + reports only (no scene written)
dispatch export <spec.json> --target godot
dispatch overlays <spec.json>        # debug overlay PNGs only
dispatch build <spec.json>           # resolve -> assemble -> validate -> export -> report
```

`--out <dir>` overrides the default export location on every command.

## Inputs

Driven by `dispatch.mission.json` (schema `dispatch.mission.v0.1`). Deli Counter and Lot are required; Zoo, Patina, and Lux are optional and skipped with an info note when absent. Expected files per tool and all JSON contracts are in `docs/FORMATS.md`.

Coordinates: upstream exports are Blender Z-up (pipeline convention); Dispatch converts to Godot Y-up with `(x, y, z) -> (x, z, -y)`, same as the Lux light loader. Set `"up_axis": "y"` in an upstream file to bypass conversion.

## What v0.1 validates

- Assembly: required anchors exist, ids unique, every flow step binds to an anchor or a trigger.
- Online runtime: every mission-critical anchor has a stable network id and server authority; nothing gameplay-critical under presentation roots; player starts cover the 1-4 player range; no flow dependency on debug anchors.
- Reachability: BFS over the merged DC+Lot nav-hint graph; every start reaches the first beat, consecutive beats connect, extraction reachable from objectives; anchors off-nav are blockers.
- Multiplayer spawns: overlap, spacing, nav binding, spawn-kill exposure near AI spawns.
- AI nav: island detection, AI spawns and patrol points on the nav graph.
- Performance: prop/light/shadow/material/nav-node budget warnings from manifest data (risk flags, not guarantees).

Issues carry severity (blocker/major/moderate/minor/info), a plain message, and a suggested fix. The readiness score is structural only — Dispatch does not score fun.

## What v0.1 does not do

- No navmesh baking and no geometry parsing: the exported `NavigationRegion3D` is marked `bake_required`; bake it in the Godot editor before AI playtest. Heavy geometry validation is a later optional native layer.
- No sightline or cover-quality scoring yet (MVP should-haves).
- No auto-fixes. Ever, silently. Suggested fixes are text in the report.
- No overrides system yet (`dispatch.overrides.json` is specced for v0.2).

## Using the package in Godot

Copy the exported mission folder into your project so it lives at the spec's `godot.res_root` (default `res://missions/<mission_id>/`), then open `mission.tscn`. `Runtime/MissionController` carries `mission_runtime.gd` with the compiled flow in `mission_config.tres`: call `start_mission()` on the server, feed it `report_objective(...)` / `report_trigger(...)` from your gameplay systems, listen to `phase_changed` / `mission_completed`. Game code owns behavior; Dispatch only binds the flow.

The GDScript side follows the pipeline's standing caveat: it needs an engine walk on real hardware before downstream work builds on it.

## Rebuild safety

Every generated node carries `metadata/dispatch_generated` and the scene root carries `[DISPATCH_GENERATED]`. `build.lock.json` records upstream schemas, sizes, and sha256 hashes. Builds are byte-deterministic for unchanged inputs. Keep manual edits out of generated files until the overrides system lands.

## Decisions taken from the TDD open questions

CLI first (Q5). Spec drives the flow, upstream tools place anchors, Dispatch binds and validates (Q1/Q2). 4-player co-op is the default assumption (Q3). Director zones are scene stubs only (Q4). No auto-fixes in v0.1 (Q6). Reports are developer-first md/json with a designer-readable html (Q7). Variants, GOOL audio zones, and the auto test harness are deferred (Q8-Q10).
