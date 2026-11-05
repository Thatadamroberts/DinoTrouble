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
## Mission tuning: {waves, first_wave, interval, min_wave, mix, target, income}
var cfg: Dictionary = {}
var base_min_wave := 3


func setup(w) -> void:
	world = w
	rng.randomize()
	cfg = w.mission.get("ai", {})
	base_min_wave = int(cfg.get("min_wave", 3))
	min_wave = base_min_wave
	var first: float = [240.0, 180.0, 140.0][GameState.difficulty]
	if cfg.has("first_wave"):
		first = float(cfg["first_wave"]) * [1.3, 1.0, 0.8][GameState.difficulty]
	wave_t = first
	if SaveSystem.pending_ai != null:
		wave_t = float(SaveSystem.pending_ai.get("wave_t", wave_t))
		wave_n = int(SaveSystem.pending_ai.get("wave_n", 0))
		min_wave = int(SaveSystem.pending_ai.get("min_wave", min_wave))
		SaveSystem.pending_ai = null


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

	if wave_t <= 0.0 and bool(cfg.get("waves", true)):
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
	var mix: Array = cfg.get("mix", [])
	if not mix.is_empty():
		var pick: String = mix[rng.randi() % mix.size()]
		if GameState.can_afford("poacher", Defs.UNITS[pick]["cost"]):
			camp.train(pick)
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
	var tgt = null
	if String(cfg.get("target", "base")) == "gatherers":
		# raiders go for the nearest gatherer in the field
		var best := 1e9
		for e in world.units_of("player"):
			if e.can_gather():
				var d: float = Iso.idist(e.position, units[0].position)
				if d < best:
					best = d
					tgt = e
	if tgt == null:
		tgt = world.find_building("player", "hatchery")
	if tgt == null:
		tgt = world.find_building("player", "ranger_station")
	if tgt == null:
		var all: Array = world.units_of("player")
		if all.is_empty():
			return
		tgt = all[0]
	wave_n += 1
	min_wave = base_min_wave + wave_n
	wave_t = [110.0, 85.0, 65.0][GameState.difficulty]
	if cfg.has("interval"):
		wave_t = float(cfg["interval"]) * [1.3, 1.0, 0.8][GameState.difficulty]
	for u in units:
		u.cmd_attack_move(tgt.position + Vector2(rng.randf_range(-40, 40), rng.randf_range(-20, 20)))
	GameState.notify("Poacher attack wave %d incoming!" % wave_n)
	Audio.ui("wave_drums", -2.0)
	world.play_ui("alert")
	if world.hud != null:
		world.hud.ping_minimap(units[0].position)
