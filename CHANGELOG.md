# Changelog

## v0.3.0 — 2026-07-11

Level Factory integration release per the "Dispatch v0.2 shell-handoff Contract Delta" (contract stays `dispatch.mission.v0.2`; tool version 0.3.0). Ships the delta items not already covered by v0.2.0's repositioning, and aligns v0.2.0's output to the delta's exact schema shapes.

### New (by delta D-number)
- **D8** `build.lock.json` upgraded to `dispatch.build_lock.v0.2`: spec_sha256, per-role input hashes (`deli_counter:shell.glb`, ...), per-file output hashes, contract id, mode, created_at. Written last; Level Factory wraps it.
- **D10** License tracking: input manifests may carry a `license` record (absent = unknown); aggregated `LICENSES.md`; unknown bundled licenses warn by default, become blockers with `--strict-licenses` (LF invokes strict).
- **D11** Resource closure (Dispatch's share): post-export scan of the WRITTEN package — every `mission.tscn` reference must be emitted inside the export root; absolute filesystem paths and tool-repo/workspace references are blockers (AC5); `resource_manifest.json` (`dispatch.resource_manifest.v0.2`) hashes every package file and asserts requires_editor_plugins/autoloads: false. Clean-project testing and Lux localization stay with Level Factory.
- **D12** `dispatch contract` machine-readable probe: tool, version, contract, modes, schemas, capabilities (all seven required capabilities plus runtime_adapter_optional, license_aggregation). AC6/AC9 pattern for every pipeline tool.
- **AC4** Anchor parity validator: `gameplay_anchors.json` must exactly match the Marker3D anchors in the written `mission.tscn` — blocking on any mismatch.
- `--include-preview` flag emits `preview_only/` in shell-handoff mode (D2).

### Aligned to delta-exact shapes (breaking vs v0.2.0 output)
- **D3** `runtime_ownership_requirements.json` schema id `dispatch.runtime_ownership_requirements.v0.2`; top-level `anchors[]` records with shell_id / anchor_type / integration_status (always "unimplemented" in this file — AC3) / expected_adapter / runtime_requirements.
- **D4** Shell IDs namespaced `<mission_id>/<anchor_id>` everywhere exported (scene metadata, registry, ownership, beat graph); metadata gains `required_authority` (server|none) — a requirement, not a description. AC2 holds: no emitted file contains `net_id` or `network_authority`.
- **D5** `gameplay_anchors.json` schema `dispatch.gameplay_anchors.v0.2`: sorted by shell_id, transform {pos, rot_y_deg}, source_tool, source_building.
- **D6** Beat graph schema `dispatch.proposed_beat_graph.v0.2`; every beat carries `status: "proposed"`; beats reference namespaced shell_ids.
- **D7** `navigation_hints.json`: node/edge form; auto-bridge edges flagged `bridged: true` with `bridge_radius`; top-level `navmesh: "bake_required"`.
- **D9** HANDOFF.md carries the delta's three verbatim paragraphs, the shell-id-is-not-a-replication-ID statement, package inventory, and the preview-deletion note when preview is included.
- **D13** Language audit: report labels use "Shell integration requirements complete"; boundary footer on every report; word-boundary forbidden-phrase test (online ready / network verified / multiplayer verified / shipping ready / balanced / fun) enforced in CI.

### Deliberate deviations (flagged, not silent)
- **AC7 amended**: `--mode playtest` is an alias for shell-handoff + `--include-preview`, NOT a byte-for-byte v0.1.0 reproduction — resurrecting `mission_runtime.gd`/`mission_config.tres`/net_id would re-import everything the handoff spec purged. AC1 holds in every mode: zero `.gd` outside `preview_only/` (plus opt-in `adapters/` interface stubs).
- `runtime-adapter` mode (from the Mission Shell Handoff spec) is kept and listed in the probe; the delta's mode table omitted it.
- Preview bridge reads `proposed_beat_graph.json` directly; no `preview_only/mission_config.tres` (that line in the delta's layout predates v0.2.0's config removal).
- Open Q1 resolved as recommended: Dispatch mints and namespaces shell IDs. Open Q2: linear beat graphs only (what the overlay already models). Open Q3: fixture manifests demonstrate the license record; unknown+warn is the default path.

### Tests
79 passing (was 65): probe, closure violations (absolute path, external ref, missing emitted file), anchor-parity tamper, license warn/strict, include-preview, playtest alias, forbidden-phrase audit, navigation edges, verbatim handoff language.

## v0.2.0 — 2026-07-10

Repositioning release per "Dispatch Changes for Mission Shell Handoff": Dispatch assembles, validates, and hands off mission shells; the production game runtime owns mission state, gameplay behavior, replication, persistence, and online correctness. Definition of Done (spec section 12) — all ten items:

1. `shell-handoff` is the default build mode (`--mode` also offers `preview-playtest`, `runtime-adapter`).
2. Default builds contain no production runtime controller and attach no scripts; `mission_runtime.gd` / `mission_config.tres|gd` and the whole Runtime subtree are gone.
3. Preview behavior is optional and isolated under `preview_only/` (`PreviewOnly/PreviewMissionBridge` node, every file headed `# DISPATCH PREVIEW ONLY`); rebuilding in default mode removes it.
4. Stable shell IDs replace network IDs — net-id assignment (1000+) removed; `runtime_binding: null` ships in `gameplay_anchors.json` for the game to fill.
5. `network_authority_map.json` -> `runtime_ownership_requirements.json`: declared requirements (authoritative_owner, replication_required, late_join_state_required, mission_persistence_required); no networking library, RPC names, replication frequency, serialization, prediction/reconciliation, persistence backend, or entity IDs prescribed.
6. Mission flow -> `proposed_beat_graph.json` (beats with location/objective/extraction/trigger/carry types + connections); runtime-state language (PRE_MISSION/COMPLETE states) removed.
7. Validation claims integration readiness: `online_runtime` validator -> `integration_readiness` (declaration completeness + internal consistency, presentation separation, player-start coverage, server-owned extraction declaration); reports carry an explicit "not validated by Dispatch" list; score statuses reworded (`ready_for_handoff` etc.).
8. Integration status on every anchor: Dispatch emits only `unimplemented` / `adapter_available` (the latter in runtime-adapter mode); `integrated` / `verified_by_game_runtime` are reserved for the game pipeline and rejected if seen.
9. No hidden gameplay or networking implementation: handoff scenes are script-free; forbidden node names (Runtime, MissionController, AuthorityController, NetworkController, ReplicationController) enforced by tests; adapter stubs are signal/contract interfaces with no RPCs.
10. README, FORMATS, CLI help, reports, and HANDOFF.md all use the same ownership language.

### Also
- New scene structure per spec section 9: Functional (Geometry/Collision/GameplayAnchors/NavigationHints) / Presentation (Props/Materials/Decals/Lighting/Atmosphere) / Handoff (OwnershipRequirements/ProposedBeatGraph/ValidationMetadata). Props moved to Presentation with gameplay_tags metadata; Patina styled shell under Presentation/Materials.
- New package layout per spec section 10: gameplay_anchors.json, proposed_beat_graph.json, runtime_ownership_requirements.json, navigation_hints.json (replaces nav/), presentation/ asset folder, HANDOFF.md engineering document.
- `runtime-adapter` mode ships adapters/: mission_events.gd (signal contract), anchor_adapter.gd (base interface), adapter_registry.gd (stub registration + unbound() report).
- Spec schema `dispatch.mission.v0.2`; v0.1 still read with an info notice. Manifest/report/anchors/ownership/beat-graph schemas bumped to v0.2.
- 65 tests (was 52), including mode isolation, forbidden-name, and v0.1 compat coverage.

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
