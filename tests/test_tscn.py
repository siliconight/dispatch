from dispatch.tscn import Raw, Scene, SceneNode, serialize


def _scene():
    s = Scene(root_name="Root")
    s.add_ext("Script", "res://x.gd", "1_x")
    s.add(SceneNode(name="Root", type="Node3D"))
    n = SceneNode(name="Child", parent=".", pos=(1, 2, 3), rot_y=90,
                  metadata={"flag": True, "name": 'say "hi"'})
    n.script = "1_x"
    n.props["cfg"] = Raw('ExtResource("1_x")')
    s.add(n)
    return s


def test_serialize_shape():
    out = serialize(_scene())
    assert out.startswith("[gd_scene load_steps=2 format=3]")
    assert '[ext_resource type="Script" path="res://x.gd" id="1_x"]' in out
    assert '[node name="Child" type="Node3D" parent="."]' in out
    assert 'script = ExtResource("1_x")' in out
    assert 'cfg = ExtResource("1_x")' in out
    assert 'metadata/flag = true' in out
    assert 'metadata/name = "say \\"hi\\""' in out
    # yaw 90: basis c=0 s=1, origin appended
    assert "transform = Transform3D(0, 0, 1, 0, 1, 0, -1, 0, 0, 1, 2, 3)" in out


def test_deterministic():
    assert serialize(_scene()) == serialize(_scene())
