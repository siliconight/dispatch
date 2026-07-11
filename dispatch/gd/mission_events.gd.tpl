# DISPATCH RUNTIME ADAPTER — interface only.
# No RPCs, replication, persistence, or authoritative mission progression.
# The production game runtime owns all of those.
#
# [DISPATCH_GENERATED] mission event contract — dispatch v{version}
# Mission: {mission_id}
#
# Signal vocabulary the production runtime can emit/consume when wiring the
# mission shell. Names are a proposal; rename freely in your game code.
extends Node

## The runtime entered a proposed beat (beat ids from proposed_beat_graph.json).
signal beat_entered(beat_id: StringName)

## The server accepted completion of a beat.
signal beat_completed(beat_id: StringName)

## A shell anchor changed state (door opened, loot taken, ...). The runtime
## decides validity, ownership, and replication before emitting.
signal anchor_state_changed(shell_id: StringName, state: Dictionary)

## Mission-level outcomes. Server-decided.
signal mission_completed()
signal mission_failed(reason: StringName)
