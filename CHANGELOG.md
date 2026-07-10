# Changelog

## v0.1.0 — 2026-07-10

First implementation of the Dispatch TDD v0.1 (recommended first implementation, TDD section 30): Python CLI, one complete happy path — DC shell + Lot site + Zoo props + Patina visuals + Lux lighting -> one online-ready Godot 4.7 mission scene.

### Added
- Mission spec loader/validator (`dispatch.mission.v0.1`) with budgets/tuning/godot blocks and loud, fix-suggesting errors (TDD 22).
- Import Resolver: per-tool file resolution (DC + Lot required; Zoo/Patina/Lux optional), schema capture, `build.lock.json` with sha256 hashes (TDD 13.1, 21).
- Importers for Deli Counter, Lot, Zoo, Patina, Lux; Blender Z-up -> Godot Y-up conversion `(x, z, -y)` matching the Lux light loader; per-file `up_axis` override.
- Gameplay Anchor Binder: 12 anchor types, unique-id checks, deterministic stable network ids by sorted (type, id) from 1000 (TDD 13.3).
- Nav graph from DC+Lot nav hints: merge with reported auto-bridging, BFS reachability, island detection, anchor-to-nav binding.
- Mission Flow Compiler: PRE_MISSION -> steps -> COMPLETE, binding by objective/tag/id; trigger-only steps (Dangerous Mode) supported (TDD 13.4, 14).
- Scene Assembler + deterministic TSCN writer: full TDD-11 hierarchy (World/Gameplay/Runtime), Marker3D anchors with authority/net_id/tags metadata, GLB instancing, Patina styled shell under VisualsRoot with DC shell kept as the function layer, prop instancing against the Zoo catalog, `NavigationRegion3D` stub marked bake_required.
- Network authority map + replication registry (`network_authority_map.json`, TDD 12).
- Runtime GDScript: `mission_runtime.gd` server-authoritative flow controller skeleton + `mission_config.gd/.tres` compiled flow resource.
- Validators: assembly, online runtime readiness (TDD 13.5), multiplayer spawns (13.10), objective reachability (13.9), AI nav readiness (13.6), performance budgets (13.11). Severity model per TDD 15.
- Mission readiness score (TDD 16) — structural only, never a fun score; blockers cap overall <=59, majors <=89.
- Reports: BLUF-first report.md / report.json / report.html (TDD 17).
- Debug overlays: nav / spawn / objective_flow / cover PNGs via stdlib-only PNG writer.
- CLI: init / assemble / validate / export / overlays / build; exit 0 clean, 1 blockers, 2 build failure (TDD 18, 30).
- Example fixture `examples/gas_station_robbery_001` (regenerable via `scripts/make_example.py`) exercising the full TDD-9 flow including Civilian/Dangerous Mode.
- 52 tests (pytest), pure stdlib runtime.

### Deferred to later versions
- Override system (`dispatch.overrides.json`), cover/sightline validators, headless bot tests, Godot editor plugin, geometry-level validation, navmesh baking.
