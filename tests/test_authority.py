from dispatch.authority import build_authority_map, node_path_for


def test_authority_map(ctx):
    m = ctx.authority
    assert m["model"] == "server_authoritative"
    assert "Gameplay/AI" in m["server_authoritative"]
    assert "World/LightingRoot" in m["client_presentation"]
    reg = m["replication_registry"]
    ids = [r["net_id"] for r in reg]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    # every objective/extraction/door/loot/ai_spawn anchor is registered
    expect = {a.id for a in ctx.anchors
              if a.type in ("objective", "extraction", "door", "loot", "ai_spawn")}
    got = {r["node"].rsplit("/", 1)[1] for r in reg}
    assert expect <= got


def test_node_paths(ctx):
    by_id = {a.id: a for a in ctx.anchors}
    assert node_path_for(by_id["player_start_01"]) == "Gameplay/PlayerStarts/player_start_01"
    assert node_path_for(by_id["clerk_spawn"]) == "Gameplay/AI/SpawnZones/clerk_spawn"
    assert node_path_for(by_id["escape_vehicle"]) == "Gameplay/ExtractionPoints/escape_vehicle"
