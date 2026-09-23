"""`__version__` and the VERSION file are one number.

They were two. `dispatch/__init__.py` read 0.3.0 while `VERSION` read 0.5.1,
because 0.4.0, 0.5.0 and 0.5.1 each bumped the file and left the literal alone.

That is not cosmetic. `__version__` is stamped into `navigation_hints.json`,
the build lock and the closure report as `dispatch_version`, and Level
Factory's `doctor` prints it -- so a package assembled by 0.5.1 reported itself
as 0.3.0, and anybody reading a cold run's own output to confirm which code
produced it was told the wrong thing. It was caught exactly that way, by
`doctor` printing `v0.3.0 @ 27ae9183` for a commit that is 0.5.1.

Pinned rather than derived: reading VERSION at import time would make the
package depend on a data file being installed beside it. One literal, one file,
and a test that fails when they disagree.
"""
import pathlib

import dispatch

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_package_version_equals_the_version_file():
    on_disk = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert dispatch.__version__ == on_disk, (
        "dispatch.__version__ is %r and VERSION is %r -- every artefact "
        "Dispatch stamps carries the former"
        % (dispatch.__version__, on_disk))


def test_the_version_file_is_not_empty():
    """A vacuity guard: an empty VERSION would make the comparison above pass
    against an empty __version__ and prove nothing."""
    on_disk = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert on_disk, "VERSION is empty"
    assert on_disk.count(".") >= 2, "VERSION %r is not a semver" % on_disk
