extends Node
## Headless smoke test. Boots a full match with a fixed seed, drives a few
## commands and simulates several minutes of play, checking that the core
## systems work. Exits with code 0 on success and 1 on failure.
##
##   godot --headless --fixed-fps 60 --path . res://scenes/tests/smoke_test.tscn

const World = preload("res://scripts/game/world.gd")
const Missions = preload("res://scripts/core/missions.gd")

var game = null
var failures: Array = []
var checks := 0


func _ready() -> void:
	print("[smoke] booting match")
	GameState.difficulty = 1
	GameState.hunger_enabled = true
	GameState.skip_briefing = true
	GameState.mission_id = "skirmish"
	GameState.pending_save = null
	game = load("res://scenes/main.tscn").instantiate()
	game.map_seed = 4242
	add_child(game)
	await _frames(3)

	_check(game.map != null, "map generated")
	_check(_units("player").size() == 7, "player starts with 7 units (got %d)" % _units("player").size())
	_check(_units("poacher").size() == 7, "poachers start with 7 units")
	_check(_units("wild").size() >= 8, "wild dinosaurs spawned (got %d)" % _units("wild").size())
	_check(game.find_building("player", "hatchery") != null, "player hatchery exists")
	_check(game.find_building("poacher", "poacher_camp") != null, "poacher camp exists")
	var path: PackedVector2Array = game.map.find_path(Iso.tile_to_world(World.PLAYER_BASE + Vector2i(3, 3)), Iso.tile_to_world(World.ENEMY_BASE + Vector2i(3, 3)))
	_check(path.size() > 0, "path exists between the two bases")

	# --- movement -----------------------------------------------------------
	var ranger = _first("player", "ranger")
	var start: Vector2 = ranger.position
	ranger.cmd_move(start + Vector2(140, -50))

	# --- gathering ------------------------------------------------------------
	var engineers := _of("player", "engineer")
	var amber = game.nearest_resource(engineers[0].position, "dna", 3000.0)
	_check(amber != null, "amber deposit near base")
	engineers[0].cmd_gather(amber)
	engineers[1].cmd_gather(amber)

	# --- hatching -------------------------------------------------------------
	var hatchery = game.find_building("player", "hatchery")
	var raptors0 := _of("player", "raptor").size()
	_check(hatchery.train("raptor"), "hatchery accepts a raptor order")
	var dna0: int = GameState.get_res("player", "dna")

	# --- construction ---------------------------------------------------------
	GameState.add("player", "supplies", 500)
	var origin := _find_build_spot("watchtower")
	_check(origin.x >= 0, "found a valid watchtower spot")
	var tower = null
	if origin.x >= 0:
		tower = game.spawn_building("watchtower", "player", origin, false)
		engineers[2].cmd_build(tower)

	await _seconds(4.0)
	_check(ranger.position.distance_to(start) > 60.0, "ranger moved")

	# --- combat -----------------------------------------------------------------
	var hunter = game.spawn_unit("hunter", "poacher", ranger.position + Vector2(100, 0))
	var hunter_hp: float = hunter.hp
	await _seconds(6.0)
	_check(not is_instance_valid(hunter) or hunter.dead or hunter.hp < hunter_hp, "ranger fought the hunter")

	await _seconds(14.0)
	_check(_of("player", "raptor").size() > raptors0, "a raptor hatched")
	_check(GameState.get_res("player", "dna") > dna0, "engineers delivered DNA (%d -> %d)" % [dna0, GameState.get_res("player", "dna")])
	_check(tower != null and is_instance_valid(tower) and tower.built, "engineer finished the watchtower")

	# --- dinosaur abilities -------------------------------------------------
	var trex = game.spawn_unit("trex", "player", game.free_spot(World.PLAYER_BASE + Vector2i(4, -3)))
	var victim = game.spawn_unit("hunter", "poacher", trex.position + Vector2(60, 0))
	trex.cmd_attack(victim)
	await _seconds(3.0)
	_check(not is_instance_valid(victim) or victim.dead or victim.hp < victim.max_hp, "T. rex attacked")

	# --- taming ---------------------------------------------------------------
	var trike = _first("wild", "triceratops")
	if trike != null:
		var tamer = engineers[2] if is_instance_valid(engineers[2]) else engineers[0]
		tamer.position = trike.position + Vector2(40, 0)
		tamer.cmd_tame(trike)
		await _seconds(8.0)
		_check(trike.faction == "player", "engineer tamed a wild triceratops")

	# --- hunger -----------------------------------------------------------------
	var starving = _first("player", "raptor")
	if starving != null:
		starving.position = game.free_spot(Vector2i(32, 32))
		starving.hunger = 0.5
		await _seconds(2.0)
		_check(starving.feral or starving.dead, "a starving raptor goes feral")

	# --- long simulation: AI economy and waves --------------------------------
	var spawned0: int = game.spawn_count.get("poacher", 0)
	await _seconds(200.0)
	_check(game.ai.wave_n >= 1 or GameState.over, "poacher AI launched an attack wave")
	_check(int(game.spawn_count.get("poacher", 0)) > spawned0, "poacher AI trained units")

	# --- living world & damage --------------------------------------------------
	_check(game.ambient != null and is_instance_valid(game.ambient), "ambient life is running")
	_check(game.decals.size() <= World.MAX_DECALS, "blood/oil decals stay under the cap (%d)" % game.decals.size())
	var home = game.find_building("player", "ranger_station")
	if home == null:
		home = game.find_building("player", "hatchery")
	if home != null and not GameState.over:
		game.camera.focus_on(home.position)
		home.hp = home.max_hp * 0.25
		await _seconds(1.0)
		_check(home.damage_fx.level == 2 and home.damage_fx.parts.size() > 0, "a badly damaged building burns and smokes")
		home.hp = home.max_hp
	var rubble0 := get_tree().get_nodes_in_group("rubble").size()
	var ptower = game.find_building("poacher", "poacher_tower")
	if ptower != null:
		ptower.take_damage(1e6, null)
		_check(get_tree().get_nodes_in_group("rubble").size() > rubble0, "a destroyed building leaves rubble")

	# --- victory --------------------------------------------------------------
	if not GameState.over:
		var camp = game.find_building("poacher", "poacher_camp")
		camp.take_damage(1e6, null)
		await _seconds(1.0)
		_check(GameState.over and GameState.victory, "destroying the camp wins the game")

	await _campaign_tests()
	_finish()


func _boot(mission_id: String, seed_value: int = -1, save = null):
	if game != null and is_instance_valid(game):
		game.queue_free()
		await _frames(2)
	get_tree().paused = false
	GameState.mission_id = mission_id
	GameState.pending_save = save
	game = load("res://scenes/main.tscn").instantiate()
	if seed_value >= 0:
		game.map_seed = seed_value
	add_child(game)
	await _frames(3)


func _campaign_tests() -> void:
	# every mission boots with its objectives
	for m in Missions.CAMPAIGN:
		await _boot(String(m["id"]))
		_check(game.mission_node.objectives.size() == m["objectives"].size(), "mission %s boots with its objectives" % m["id"])
	# tutorial objectives complete in order
	await _boot("m1")
	GameState.stats["gathered_dna"] = 60
	await _seconds(1.0)
	_check(game.mission_node.objectives[0]["done"] and not game.mission_node.objectives[1]["done"], "tutorial objectives progress in order")
	# stolen eggs: breaking the cages rescues hatchlings and wins
	await _boot("m2")
	var raptors0 := _of("player", "raptor").size()
	var cages: Array = get_tree().get_nodes_in_group("buildings").filter(func(b): return b.def_id == "egg_cage")
	_check(cages.size() == 3, "mission 2 has three egg cages")
	for c in cages:
		c.take_damage(1e6, null)
	await _seconds(1.0)
	_check(_of("player", "raptor").size() >= raptors0 + 6, "breaking cages frees hatchlings")
	_check(GameState.over and GameState.victory, "rescuing all eggs wins mission 2")
	_check(SaveSystem.unlocked >= 3, "winning unlocks the next mission")
	# hold the line: the survive timer wins
	await _boot("m3")
	GameState.elapsed = 359.0
	await _seconds(2.0)
	_check(GameState.over and GameState.victory, "surviving the timer wins mission 3")
	# save / load round trip
	await _boot("skirmish", 4242)
	await _seconds(2.0)
	var data: Dictionary = JSON.parse_string(JSON.stringify(SaveSystem.serialize(game)))
	var units0 := get_tree().get_nodes_in_group("units").size()
	var dna0: int = GameState.get_res("player", "dna")
	await _boot("skirmish", -1, data)
	_check(get_tree().get_nodes_in_group("units").size() == units0, "loading a save restores every unit (%d)" % units0)
	_check(GameState.get_res("player", "dna") == dna0, "loading a save restores resources")
	_check(game.map_seed == 4242, "loading a save rebuilds the same island")
	# night
	GameState.time_of_day = 0.8
	_check(GameState.night() > 0.9 and GameState.sight_mult() < 0.8, "night falls and sight shrinks")
	GameState.time_of_day = 0.3
	_check(GameState.night() < 0.05, "daytime is bright")
	await _audio_tests()


func _audio_tests() -> void:
	var buses_ok := true
	for b in ["Music", "SFX", "Ambience", "UI"]:
		buses_ok = buses_ok and AudioServer.get_bus_index(b) >= 0
	_check(buses_ok, "audio buses exist")
	var missing: Array = []
	for snd in ["shot", "burst", "tower_shot", "spit", "net", "bite", "bite_small", "bite_large", "roar", "trex_roar",
			"raptor_call", "dilo_call", "trike_call", "stomp", "impact_flesh", "impact_wood", "dino_death", "human_down",
			"hatch", "build", "gather_rock", "gather_wood", "collapse", "explosion", "splash", "select", "ui_click",
			"ui_confirm", "objective", "alert", "wave_drums", "victory", "defeat"]:
		if not Audio.has_sound(snd):
			missing.append(snd)
	_check(missing.is_empty(), "every sound effect has variants (missing: %s)" % [missing])
	_check(Audio.loop_stream(Audio.MUSIC["combat"]) != null and Audio.loop_stream(Audio.AMBIENCE["surf"]) != null, "music and ambience load")
	_check(Audio.music_state == "explore", "exploration music plays in a match (got %s)" % Audio.music_state)
	Audio.combat_ping()
	Audio.combat_ping()
	await _seconds(0.3)
	_check(Audio.music_state == "combat", "fighting switches to combat music")
	Audio.last_combat -= 30.0
	await _seconds(0.3)
	_check(Audio.music_state == "explore", "quiet returns to exploration music")
	GameState.time_of_day = 0.8
	await _seconds(3.0)
	_check(float(Audio.amb_level["night"]) > float(Audio.amb_level["day"]), "night ambience takes over after dark")
	SaveSystem.set_setting("music_volume", 0.5)
	var vol := AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Music"))
	_check(absf(vol - linear_to_db(0.5)) < 0.1, "music volume setting drives the Music bus")


func _finish() -> void:
	print("[smoke] %d checks, %d failures" % [checks, failures.size()])
	for f in failures:
		print("[smoke] FAILED: ", f)
	get_tree().paused = false
	get_tree().quit(1 if failures.size() > 0 else 0)


func _check(ok: bool, what: String) -> void:
	checks += 1
	if ok:
		print("[smoke] ok   ", what)
	else:
		print("[smoke] FAIL ", what)
		failures.append(what)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _seconds(s: float) -> void:
	await _frames(int(s * Engine.physics_ticks_per_second))


func _units(faction: String) -> Array:
	return game.units_of(faction)


func _of(faction: String, id: String) -> Array:
	return _units(faction).filter(func(u): return u.def_id == id)


func _first(faction: String, id: String):
	var arr := _of(faction, id)
	return arr[0] if not arr.is_empty() else null


func _find_build_spot(id: String) -> Vector2i:
	var base: Vector2i = World.PLAYER_BASE
	for r in range(2, 9):
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				var o := base + Vector2i(dx, dy)
				if game.can_place(id, o):
					return o
	return Vector2i(-1, -1)
