"""Dispatch — online mission assembly and validation for Godot 4.7.

Assemble the mission. Validate the mission. Package the mission for online play.
"""

#: THE VERSION EVERY ARTEFACT IS STAMPED WITH, and it must equal the
#: VERSION file. It did not: this read 0.3.0 while VERSION said 0.5.1,
#: because 0.4.0, 0.5.0 and 0.5.1 each bumped the file and not this
#: literal. Dispatch writes `dispatch_version` into navigation_hints,
#: the build lock and the closure report, so a package built by 0.5.1
#: claimed to be built by 0.3.0 -- and a cold run reading its own
#: output to confirm which code ran would have been told the wrong
#: thing. `tests/test_version.py` pins the two together.
__version__ = "0.5.2"

SCHEMA_MISSION = "dispatch.mission.v0.2"
SCHEMA_MISSION_LEGACY = "dispatch.mission.v0.1"
GENERATED_MARKER = "[DISPATCH_GENERATED]"


class DispatchError(Exception):
    """Loud, useful failure (TDD section 22).

    Every DispatchError message should say what failed, what was expected,
    and suggest a fix.
    """

    def __init__(self, message: str, expected: str = "", suggested_fix: str = ""):
        self.message = message
        self.expected = expected
        self.suggested_fix = suggested_fix
        super().__init__(self.render())

    def render(self) -> str:
        parts = [f"Build failed: {self.message}"]
        if self.expected:
            parts.append(f"\nExpected:\n{self.expected}")
        if self.suggested_fix:
            parts.append(f"\nSuggested fix:\n{self.suggested_fix}")
        return "\n".join(parts)
