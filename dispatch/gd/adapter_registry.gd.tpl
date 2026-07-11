# DISPATCH RUNTIME ADAPTER — interface only.
# No RPCs, replication, persistence, or authoritative mission progression.
# The production game runtime owns all of those.
#
# [DISPATCH_GENERATED] adapter registry stub — dispatch v{version}
# Mission: {mission_id}
#
# Stub registration point: the production runtime registers one adapter per
# gameplay-critical shell id (see gameplay_anchors.json). unbound() reports
# what remains unimplemented.
extends Node

var _adapters: Dictionary = {}

## Shell ids that require an adapter, injected by the generated scene or
## loaded by the game from gameplay_anchors.json.
@export var required_shell_ids: Array[StringName] = []


func register(shell_id: StringName, adapter: Node) -> void:
	_adapters[shell_id] = adapter


func get_adapter(shell_id: StringName) -> Node:
	return _adapters.get(shell_id)


## Shell ids still lacking a registered adapter.
func unbound() -> Array[StringName]:
	var missing: Array[StringName] = []
	for sid in required_shell_ids:
		if not _adapters.has(sid):
			missing.append(sid)
	return missing
