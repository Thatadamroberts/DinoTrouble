extends Node
## Poacher computer opponent: keeps trappers gathering, trains an army,
## defends its camp and sends growing attack waves at the player's base.

const THINK_INTERVAL := 1.0
const TRAPPER_TARGET := 4

var world = null
var think_t := 2.0
var wave_t := 180.0
var wave_n := 0
var min_wave := 3
var rng := RandomNumberGenerator.new()


func setup(w) -> void:
	world = w
	rng.randomize()
	wave_t = [240.0, 180.0, 140.0][GameState.difficulty]


func _process(delta: float) -> void:
	if GameState.over or world == null:
		return
	wave_t -= delta
	think_t -= delta
	if think_t > 0.0:
		return
	think_t = THINK_INTERVAL
	_think()


func _think() -> void:
	var camp = world.find_building("poacher", "poacher_camp")
	if camp == null:
		return
	var units: Array = world.units_of("poacher")
	var trappers: Array = []
	var army: Array = []
	for u in units:
		if u.def_id == "trapper":
			trappers.append(u)
		else:
			army.append(u)

	_manage_economy(trappers)
	_manage_production(camp, trappers, army)
	_defend(camp, army)

	if wave_t <= 0.0:
		var idle: Array = army.filter(func(u): return u.is_idle())
		if idle.size() >= min_wave:
			_launch_wave(idle)
		else:
			wave_t = 20.0  # check again soon


func _manage_economy(trappers: Array) -> void:
	var want := "dna" if GameState.get_res("poacher", "dna") < GameState.get_res("poacher", "supplies") * 0.5 else "supplies"
	for t in trappers:
		if t.is_idle():
			var node = world.nearest_resource(t.position, want, 1400.0)
			if node == null:
				node = world.nearest_resource(t.position, "dna" if want == "supplies" else "supplies", 1400.0)
			if node != null:
				t.cmd_gather(node)


func _manage_production(camp, trappers: Array, army: Array) -> void:
	if camp.queue.size() >= 2:
		return
	if trappers.size() < TRAPPER_TARGET:
		camp.train("trapper")
		return
	var roll := rng.randf()
	if roll < 0.25 and GameState.can_afford("poacher", Defs.UNITS["jeep"]["cost"]):
		camp.train("jeep")
	elif roll < 0.4:
		camp.train("trapper")  # extra gatherers speed up the economy
	else:
		camp.train("hunter")


func _defend(camp, army: Array) -> void:
	var threat = null
	for e in world.units_of("player"):
		if Iso.idist(e.position, camp.position) < 9.0 * Iso.TILE_DIST:
			threat = e
			break
	if threat == null:
		return
	for u in army:
		if u.is_idle():
			u.cmd_attack_move(threat.position)


func _launch_wave(units: Array) -> void:
	var tgt = world.find_building("player", "hatchery")
	if tgt == null:
		tgt = world.find_building("player", "ranger_station")
	if tgt == null:
		var all: Array = world.units_of("player")
		if all.is_empty():
			return
		tgt = all[0]
	wave_n += 1
	min_wave = 3 + wave_n
	wave_t = [110.0, 85.0, 65.0][GameState.difficulty]
	for u in units:
		u.cmd_attack_move(tgt.position + Vector2(rng.randf_range(-40, 40), rng.randf_range(-20, 20)))
	GameState.notify("Poacher attack wave %d incoming!" % wave_n)
	world.play_ui("alert")
	if world.hud != null:
		world.hud.ping_minimap(units[0].position)
