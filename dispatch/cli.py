"""Dispatch CLI.

    dispatch init <mission_id>
    dispatch assemble <spec.json> [--mode MODE]
    dispatch validate <spec.json>
    dispatch export <spec.json> --target godot [--mode MODE]
    dispatch overlays <spec.json>
    dispatch build <spec.json> [--mode MODE]   # resolve -> assemble -> validate -> export -> report

Build modes (handoff spec section 2): shell-handoff (default, no runtime
code), preview-playtest (adds isolated preview_only/ walkthrough tooling),
runtime-adapter (adds adapters/ interface stubs — signals and contracts only,
never RPCs, replication, persistence, or authoritative progression).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import DispatchError, __version__
from .assembler import (DEFAULT_MODE, MODES, assemble_scene, build_context,
                        default_out_dir, export_package)
from .closure import check_anchor_parity, scan_package, write_resource_manifest
from .licenses import validate as validate_licenses
from .licenses import write_licenses_md
from .resolver import write_lock_file
from .overlays import write_overlays
from .report import write_handoff, write_reports
from .score import compute
from .spec import SCHEMA_MISSION, load_spec
from .validators import run_all

INIT_SPEC = {
    "schema": SCHEMA_MISSION,
    "mission_id": "",
    "title": "",
    "engine": "godot_4_7",
    "mode": "online_coop_pve",
    "players": {"min": 1, "max": 4, "preferred": 4},
    "networking": {"model": "server_authoritative", "critical_state_owner": "server"},
    "theme": "",
    "inputs": {
        "deli_counter": "build/deli_counter/shell.gameplay.json",
        "lot": "build/lot/lot.layout.json",
        "zoo": "build/zoo/zoo.catalog.json",
        "patina": "build/patina/shell.patina.json",
        "lux": "build/lux/lux.profile.json",
    },
    "mission_flow": [
        {"step": "spawn", "location_tag": "mission_start"},
        {"step": "approach", "objective": "reach_site"},
        {"step": "loot", "objective": "grab_the_take"},
        {"step": "escape", "objective": "reach_extraction"},
    ],
    "validation": {
        "require_online_runtime_readiness": True,
        "require_all_objectives_reachable": True,
        "require_all_players_spawn_valid": True,
        "require_ai_navmesh": True,
        "require_performance_budget": True,
    },
}


def _out_dir(spec, args) -> Path:
    return Path(args.out).resolve() if args.out else default_out_dir(spec)


def cmd_init(args) -> int:
    mission_id = args.mission_id
    root = Path(args.out or mission_id)
    if (root / "dispatch.mission.json").exists():
        print(f"refusing to overwrite existing spec in {root}", file=sys.stderr)
        return 2
    root.mkdir(parents=True, exist_ok=True)
    spec = dict(INIT_SPEC)
    spec["mission_id"] = mission_id
    spec["title"] = mission_id.replace("_", " ").title()
    (root / "dispatch.mission.json").write_text(
        json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    for tool in ("deli_counter", "lot", "zoo", "patina", "lux"):
        (root / "build" / tool).mkdir(parents=True, exist_ok=True)
    print(f"initialized {root / 'dispatch.mission.json'}")
    print("point inputs at your Deli Counter / Lot / Zoo / Patina / Lux exports, then run:")
    print(f"  dispatch build {root / 'dispatch.mission.json'}")
    return 0


def cmd_assemble(args) -> int:
    spec = load_spec(args.spec)
    ctx = build_context(spec, mode=getattr(args, "mode", DEFAULT_MODE),
                        include_preview=getattr(args, "include_preview", False))
    scene = assemble_scene(ctx)
    out = _out_dir(spec, args)
    export_package(ctx, scene, out)
    write_handoff(ctx, out)
    write_licenses_md(ctx, out)
    write_resource_manifest(out)
    write_lock_file(spec, ctx.resolved, out, mode=ctx.mode)
    print(f"assembled {out / 'mission.tscn'} (mode {ctx.mode})")
    return 0


def cmd_validate(args) -> int:
    spec = load_spec(args.spec)
    ctx = build_context(spec)
    assemble_scene(ctx)  # structural pass; scene not written
    issues = run_all(ctx)
    score = compute(issues)
    out = _out_dir(spec, args)
    vdir = write_reports(ctx, issues, score, out)
    _print_summary(issues, score, vdir)
    return 1 if any(i.severity == "blocker" for i in issues) else 0


def cmd_contract(args) -> int:
    """Machine-readable capability probe (delta D12). Pipeline adapters parse
    this instead of scraping prose."""
    from . import SCHEMA_MISSION
    print(json.dumps({
        "tool": "dispatch",
        "version": __version__,
        "contract": SCHEMA_MISSION,
        "modes": list(MODES),
        "schemas": [
            "dispatch.runtime_ownership_requirements.v0.2",
            "dispatch.proposed_beat_graph.v0.2",
            "dispatch.navigation_hints.v0.2",
            "dispatch.resource_manifest.v0.2",
            "dispatch.build_lock.v0.2",
            "dispatch.gameplay_anchors.v0.2",
            "dispatch.manifest.v0.2",
            "dispatch.report.v0.2",
        ],
        "capabilities": [
            "assemble_shell",
            "validate_shell",
            "export_godot",
            "shell_handoff",
            "preview_playtest_optional",
            "portable_resource_closure",
            "dependency_manifest",
            "runtime_adapter_optional",
            "license_aggregation",
        ],
    }, indent=2))
    return 0


def cmd_overlays(args) -> int:
    spec = load_spec(args.spec)
    ctx = build_context(spec)
    out = _out_dir(spec, args)
    written = write_overlays(ctx, out)
    for p in written:
        print(f"wrote {p}")
    return 0


def cmd_export(args) -> int:
    if args.target != "godot":
        print(f"unsupported export target {args.target!r}; only godot is supported", file=sys.stderr)
        return 2
    return cmd_assemble(args)


def cmd_build(args) -> int:
    spec = load_spec(args.spec)
    ctx = build_context(spec, mode=getattr(args, "mode", DEFAULT_MODE),
                        include_preview=getattr(args, "include_preview", False))
    scene = assemble_scene(ctx)
    out = _out_dir(spec, args)
    export_package(ctx, scene, out)
    # validators + post-export checks against the WRITTEN package
    issues = run_all(ctx)
    issues += scan_package(out, ctx.res_root)
    issues += check_anchor_parity(out)
    issues += validate_licenses(ctx, strict=getattr(args, "strict_licenses", False))
    score = compute(issues)
    vdir = write_reports(ctx, issues, score, out)
    write_handoff(ctx, out, issues, score)
    write_licenses_md(ctx, out)
    write_overlays(ctx, out)
    write_resource_manifest(out)
    write_lock_file(spec, ctx.resolved, out, mode=ctx.mode)
    print(f"exported {out} (mode {ctx.mode})")
    _print_summary(issues, score, vdir)
    return 1 if any(i.severity == "blocker" for i in issues) else 0


def _print_summary(issues, score, vdir) -> None:
    counts = {}
    for i in issues:
        counts[i.severity] = counts.get(i.severity, 0) + 1
    parts = ", ".join(f"{counts.get(s, 0)} {s}" for s in ("blocker", "major", "moderate", "minor"))
    print(f"readiness {score['mission_readiness']} ({score['status']}) — {parts}")
    print(f"report: {vdir / 'report.md'}")
    for i in issues:
        if i.severity == "blocker":
            print(f"  BLOCKER [{i.system}] {i.message}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="dispatch",
        description=("Assemble and validate mission shells for integration into a "
                     "server-authoritative 1-4 player online co-op game. Dispatch packages "
                     "mission intent and prepares an integration contract; the production "
                     "game runtime owns mission state, gameplay, replication, and persistence."),
    )
    parser.add_argument("--version", action="version", version=f"dispatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="scaffold a mission spec and build folders")
    p.add_argument("mission_id")
    p.add_argument("--out", help="directory to create (default: ./<mission_id>)")
    p.set_defaults(fn=cmd_init)

    for name, fn, hlp, has_mode in (
        ("assemble", cmd_assemble, "resolve inputs and write the mission shell package (no validation)", True),
        ("validate", cmd_validate, "run validation and write reports", False),
        ("overlays", cmd_overlays, "write debug overlay PNGs", False),
        ("build", cmd_build, "resolve -> assemble -> validate -> export -> report", True),
    ):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("spec", help="path to dispatch.mission.json")
        p.add_argument("--out", help="output directory (default: <spec dir>/export/godot/missions/<mission_id>)")
        if has_mode:
            p.add_argument("--mode", choices=MODES, default=DEFAULT_MODE,
                           help="shell-handoff (default) | playtest/preview-playtest | runtime-adapter")
            p.add_argument("--include-preview", action="store_true",
                           help="emit preview_only/ in shell-handoff mode")
            if name == "build":
                p.add_argument("--strict-licenses", action="store_true",
                               help="unknown bundled licenses become blockers (Level Factory default)")
        p.set_defaults(fn=fn)

    p = sub.add_parser("contract", help="print the machine-readable tool contract (JSON)")
    p.set_defaults(fn=cmd_contract)

    p = sub.add_parser("export", help="export the mission shell package for a target engine")
    p.add_argument("spec")
    p.add_argument("--target", default="godot")
    p.add_argument("--out")
    p.add_argument("--mode", choices=MODES, default=DEFAULT_MODE)
    p.add_argument("--include-preview", action="store_true")
    p.set_defaults(fn=cmd_export)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except DispatchError as e:
        print(e.render(), file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
