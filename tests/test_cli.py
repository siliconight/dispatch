import json

from dispatch.cli import main


def test_build_end_to_end(world, capsys):
    rc = main(["build", str(world / "dispatch.mission.json")])
    assert rc == 0
    out = world / "export/godot/missions/gas_station_robbery_001"
    for rel in ("mission.tscn", "mission_manifest.json", "network_authority_map.json",
                "mission_config.tres", "mission_runtime.gd", "build.lock.json",
                "validation/report.md", "validation/report.json", "validation/report.html",
                "validation/overlays/nav_overlay.png", "nav/navgraph.json"):
        assert (out / rel).is_file(), rel
    manifest = json.loads((out / "mission_manifest.json").read_text())
    assert manifest["mission_id"] == "gas_station_robbery_001"
    assert manifest["anchor_counts"]["player_start"] == 4
    assert "readiness 100" in capsys.readouterr().out


def test_build_exit_1_on_blocker(world, capsys):
    p = world / "build/lot/lot.nav_hints.json"
    d = json.loads(p.read_text())
    d["links"] = [l for l in d["links"] if l != ["curb", "lot_edge"]]
    p.write_text(json.dumps(d))
    rc = main(["build", str(world / "dispatch.mission.json")])
    assert rc == 1
    assert "BLOCKER" in capsys.readouterr().out


def test_missing_input_exit_2(world, capsys):
    (world / "build/deli_counter/shell.gameplay.json").unlink()
    rc = main(["build", str(world / "dispatch.mission.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "shell.gameplay.json is missing" in err
    assert "Suggested fix" in err


def test_validate_writes_reports_only(world):
    rc = main(["validate", str(world / "dispatch.mission.json")])
    assert rc == 0
    out = world / "export/godot/missions/gas_station_robbery_001"
    assert (out / "validation/report.md").is_file()
    assert not (out / "mission.tscn").exists()


def test_init(tmp_path, capsys):
    rc = main(["init", "warehouse_raid_001", "--out", str(tmp_path / "wr")])
    assert rc == 0
    spec = json.loads((tmp_path / "wr" / "dispatch.mission.json").read_text())
    assert spec["mission_id"] == "warehouse_raid_001"
    assert (tmp_path / "wr" / "build" / "deli_counter").is_dir()
    # refuses to overwrite
    assert main(["init", "warehouse_raid_001", "--out", str(tmp_path / "wr")]) == 2


def test_build_deterministic(world):
    spec = str(world / "dispatch.mission.json")
    out = world / "export/godot/missions/gas_station_robbery_001"
    main(["build", spec])
    first = (out / "mission.tscn").read_bytes()
    main(["build", spec])
    assert (out / "mission.tscn").read_bytes() == first
