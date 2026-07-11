# DISPATCH PREVIEW ONLY
# Not production gameplay or networking code.
# The shipping game runtime must own mission authority,
# validation, replication, persistence, and reconnect behavior.
#
# [DISPATCH_GENERATED] preview mission bridge — dispatch v{version}
# Mission: {mission_id}
#
# Local, single-process walkthrough tooling: mock beat progression, calm/alarm
# toggles, placeholder extraction. Regenerate with `dispatch build --mode
# preview-playtest`; do not edit in place.
extends Node

signal beat_entered(beat_id: StringName)
signal beat_completed(beat_id: StringName)
signal alarm_changed(alarm: bool)
signal preview_extraction_completed()

## res:// path to proposed_beat_graph.json; set by the generated scene.
@export var beat_graph_path: String = ""

var _beats: Array[Dictionary] = []
var _index: int = -1
var _alarm: bool = false


func _ready() -> void:
	if beat_graph_path == "":
		push_warning("[dispatch preview] no beat_graph_path set")
		return
	var f := FileAccess.open(beat_graph_path, FileAccess.READ)
	if f == null:
		push_warning("[dispatch preview] cannot open %s" % beat_graph_path)
		return
	var data: Variant = JSON.parse_string(f.get_as_text())
	if typeof(data) == TYPE_DICTIONARY:
		for b: Variant in data.get("beats", []):
			_beats.append(b)


func current_beat() -> Dictionary:
	if _index >= 0 and _index < _beats.size():
		return _beats[_index]
	return {}


## Start the walkthrough at the first proposed beat.
func start_preview() -> void:
	_index = -1
	next_beat()


## Route walkthrough controls: step forward/back through proposed beats.
func next_beat() -> void:
	if _index < _beats.size() - 1:
		_index += 1
		beat_entered.emit(StringName(str(current_beat().get("id", ""))))


func prev_beat() -> void:
	if _index > 0:
		_index -= 1
		beat_entered.emit(StringName(str(current_beat().get("id", ""))))


## Mock objective completion: marks the current beat done and advances.
func complete_current_beat() -> void:
	var beat := current_beat()
	if beat.is_empty():
		return
	beat_completed.emit(StringName(str(beat.get("id", ""))))
	if str(beat.get("type", "")) == "extraction":
		complete_extraction()
	else:
		next_beat()


## Calm / alarm state trigger (preview visual & audio hooks only).
func set_alarm(alarm: bool) -> void:
	if _alarm != alarm:
		_alarm = alarm
		alarm_changed.emit(_alarm)


func is_alarm() -> bool:
	return _alarm


## Placeholder extraction completion. The shipping runtime must gate
## extraction server-side; this just ends the preview walkthrough.
func complete_extraction() -> void:
	preview_extraction_completed.emit()
