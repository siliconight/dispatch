# [DISPATCH_GENERATED] mission config resource — dispatch v{version}
extends Resource

@export var mission_id: String = ""
@export var title: String = ""
@export var mode: String = "online_coop_pve"
@export var net_model: String = "server_authoritative"
@export var players_min: int = 1
@export var players_max: int = 4
@export var states: Array[String] = []
@export var steps: Array[Dictionary] = []
