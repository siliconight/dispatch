# DISPATCH RUNTIME ADAPTER — interface only.
# No RPCs, replication, persistence, or authoritative mission progression.
# The production game runtime owns all of those.
#
# [DISPATCH_GENERATED] anchor adapter base — dispatch v{version}
# Mission: {mission_id}
#
# Base interface for binding a shell anchor (gameplay_anchors.json) to a
# production gameplay object. Extend per adapter kind (openable_door,
# lootable, extraction_zone, ...) in game code.
extends Node

## Stable shell id from gameplay_anchors.json. Not a network id.
@export var shell_id: StringName = &""

## Declared requirements copied from runtime_ownership_requirements.json.
## The production runtime must satisfy these; Dispatch only declares them.
@export var runtime_requirements: Dictionary = {}


## Example integration method: the game runtime calls this after it has
## created its authoritative object for this anchor and is ready to own it.
func bind_runtime_object(_runtime_object: Node) -> void:
	push_warning("[dispatch adapter] bind_runtime_object not implemented for %s" % shell_id)


## Example integration method: request a state change. Implementations must
## route this through the game's server-authoritative path — never mutate
## mission state locally here.
func request_state_change(_state: Dictionary) -> void:
	push_warning("[dispatch adapter] request_state_change not implemented for %s" % shell_id)
