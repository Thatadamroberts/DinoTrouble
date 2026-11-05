extends Node
## Headless smoke test. Boots a full match with a fixed seed, drives a few
## commands and simulates several minutes of play, checking that the core
## systems work. Exits with code 0 on success and 1 on failure.
##
##   godot --headless --fixed-fps 60 --path . res://scenes/tests/smoke_test.tscn

const World = preload("res://scripts/game/world.gd")

var game = null
var failures: Array = []
var checks := 0


func _ready() -> void:
	print("[smoke] booting match")
	GameState.difficulty = 1
	GameState.hunger_enabled = true
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
	var tower = game.find_building("poacher", "poacher_tower")
	if tower != null:
		tower.take_damage(1e6, null)
		_check(get_tree().get_nodes_in_group("rubble").size() > rubble0, "a destroyed building leaves rubble")

	# --- victory --------------------------------------------------------------
	if not GameState.over:
		var camp = game.find_building("poacher", "poacher_camp")
		camp.take_damage(1e6, null)
		_check(GameState.over and GameState.victory, "destroying the camp wins the game")

	_finish()


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
