import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import make_example  # noqa: E402

from dispatch.assembler import build_context  # noqa: E402
from dispatch.spec import load_spec  # noqa: E402


@pytest.fixture
def world(tmp_path):
    """Full example world in a tmp dir; returns its root path."""
    root = tmp_path / "mission"
    make_example.main(root)
    return root


@pytest.fixture
def spec(world):
    return load_spec(world / "dispatch.mission.json")


@pytest.fixture
def ctx(spec):
    return build_context(spec)


def edit_json(path: Path, fn) -> None:
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data, indent=2))
