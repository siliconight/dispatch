import struct

from dispatch.overlays import write_overlays


def test_overlays_are_valid_pngs(ctx, tmp_path):
    written = write_overlays(ctx, tmp_path)
    names = {p.name for p in written}
    assert names == {"nav_overlay.png", "spawn_overlay.png",
                     "objective_flow.png", "cover_overlay.png"}
    for p in written:
        b = p.read_bytes()
        assert b[:8] == b"\x89PNG\r\n\x1a\n"
        w, h = struct.unpack(">II", b[16:24])
        assert w > 100 and h > 100
