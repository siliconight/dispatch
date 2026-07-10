# [DISPATCH_GENERATED] mission runtime controller — dispatch v{version}
# Mission: {mission_id}
#
# Server-authoritative mission state skeleton. Dispatch generates the flow
# binding; game code owns behavior (attach your own systems to the signals).
# Do not edit in place — regenerate with `dispatch build`, put manual changes
# in dispatch.overrides.json or your own scripts.
extends Node

signal phase_changed(previous: StringName, current: StringName)
signal objective_completed(objective: StringName)
signal mission_completed()
signal mission_failed(reason: StringName)

@export var mission_config: Resource

var _states: Array[StringName] = []
var _phase_index: int = 0
var _completed_objectives: Dictionary = {{}}


func _ready() -> void:
	if mission_config == null:
		push_error("[dispatch] MissionController has no mission_config")
		return
	for s: Variant in mission_config.states:
		_states.append(StringName(s))
	set_multiplayer_authority(1)


func current_phase() -> StringName:
	if _states.is_empty():
		return &"PRE_MISSION"
	return _states[_phase_index]


func is_server() -> bool:
	return multiplayer == null or multiplayer.multiplayer_peer == null or multiplayer.is_server()


## Server-side entry point: gameplay systems report objective completion here.
## Never call from client prediction — extraction and loot must be
## server-confirmed (TDD 13.5).
func report_objective(objective: StringName) -> void:
	if not is_server():
		push_warning("[dispatch] report_objective called on client; ignored")
		return
	_completed_objectives[objective] = true
	objective_completed.emit(objective)
	_try_advance()


## Server-side trigger entry point (alarms, weapon fire, scripted events).
func report_trigger(trigger: StringName) -> void:
	if not is_server():
		return
	var step: Dictionary = _current_step()
	if not step.is_empty() and StringName(step.get("trigger", "")) == trigger:
		_advance()


func _current_step() -> Dictionary:
	var i: int = _phase_index - 1  # states[0] is PRE_MISSION
	var steps: Array = mission_config.steps
	if i >= 0 and i < steps.size():
		return steps[i]
	return {{}}


func _try_advance() -> void:
	var step: Dictionary = _current_step()
	if step.is_empty():
		if current_phase() == &"PRE_MISSION":
			_advance()
		return
	var objective: String = str(step.get("objective", ""))
	if objective != "" and _completed_objectives.get(StringName(objective), false):
		_advance()


func _advance() -> void:
	if _phase_index >= _states.size() - 1:
		return
	var previous: StringName = current_phase()
	_phase_index += 1
	_replicate_phase.rpc(_phase_index)
	phase_changed.emit(previous, current_phase())
	if current_phase() == &"COMPLETE":
		mission_completed.emit()


## Start the mission (server): PRE_MISSION -> first flow state.
func start_mission() -> void:
	if not is_server():
		return
	if current_phase() == &"PRE_MISSION":
		_advance()


@rpc("authority", "call_remote", "reliable")
func _replicate_phase(index: int) -> void:
	var previous: StringName = current_phase()
	_phase_index = index
	phase_changed.emit(previous, current_phase())
