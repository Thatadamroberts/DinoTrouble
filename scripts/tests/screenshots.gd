extends Node
## Renders a match with a real GPU context (run under Xvfb in CI) and saves
## a few screenshots to <project>/screenshots/. Used to check the graphics
## and catch shader compile errors.
##
##   xvfb-run -a godot --rendering-driver opengl3 --path . res://scenes/tests/screenshots.tscn

const World = preload("res://scripts/game/world.gd")

var game = null


func _ready() -> void:
	var dir := ProjectSettings.globalize_path("res://screenshots")
	DirAccess.make_dir_recursive_absolute(dir)
	GameState.difficulty = 1
	GameState.skip_briefing = true
	GameState.mission_id = "skirmish"
	GameState.pending_save = null
	game = load("res://scenes/main.tscn").instantiate()
	game.map_seed = 4242
	add_child(game)
	game.fog.enabled = false
	await _frames(30)
	# give units something to do so the shots show animation & combat
	var hatchery = game.find_building("player", "hatchery")
	for id in ["trex", "triceratops", "dilophosaurus", "raptor"]:
		game.spawn_unit(id, "player", game.free_spot(World.PLAYER_BASE + Vector2i(6, -4)))
	for id in ["hunter", "trapper", "jeep"]:
		game.spawn_unit(id, "poacher", game.free_spot(World.PLAYER_BASE + Vector2i(10, -6)))
	for u in game.units_of("player"):
		if u.can_gather():
			var n = game.nearest_resource(u.position, "dna", 2000.0)
			if n != null:
				u.cmd_gather(n)
	await _frames(90)

	await _shot("base", game.find_building("player", "ranger_station").position + Vector2(120, -40), 1.0)
	await _shot("base_zoom", hatchery.position + Vector2(140, 30), 2.0)
	await _shot("fight", Iso.tile_to_world(World.PLAYER_BASE + Vector2i(8, -5)), 2.0)
	await _shot("enemy", game.find_building("poacher", "poacher_camp").position, 1.0)
	await _shot("coast", Iso.tile_to_world(Vector2i(32, 58)), 1.0)
	await _shot("wide", Iso.tile_to_world(Vector2i(32, 32)), 0.5)
	await _lineup()
	await _damage()
	await _life()
	await _night()
	print("[shots] done")
	get_tree().quit(0)


## The base at night: lit windows, lamps, glowing fires and fireflies.
func _night() -> void:
	GameState.time_of_day = 0.8
	await _frames(30)
	var station = game.find_building("player", "ranger_station")
	await _shot("night", station.position + Vector2(140, -20), 1.25, false)


## Burning buildings, smoke and rubble.
func _damage() -> void:
	var hatch = game.find_building("player", "hatchery")
	var station = game.find_building("player", "ranger_station")
	hatch.hp = hatch.max_hp * 0.2
	station.hp = station.max_hp * 0.5
	var t = game.spawn_building("watchtower", "player", World.PLAYER_BASE + Vector2i(-3, 6), true)
	t.take_damage(1e6, null)
	await _frames(150)
	await _shot("damage", hatch.position + Vector2(-60, -30), 1.5, false)


## Flying reptiles, butterflies, splashes, muzzle flashes, dust and blood.
func _life() -> void:
	var view_center: Vector2 = Iso.tile_to_world(World.PLAYER_BASE + Vector2i(8, -5))
	game.camera.position = view_center
	game.camera.zoom = Vector2(1.5, 1.5)
	await _frames(5)
	game.ambient.spawn_flock()
	game.ambient.flocks[-1]["pos"] = view_center + Vector2(-260, -120)
	for i in 4:
		game.spawn_decal("blood", view_center + Vector2(randf_range(-120, 120), randf_range(-60, 60)), 1.2)
	await _frames(40)
	await _shot("life", view_center, 1.5, false)


## Every unit type side by side, shot close up at full resolution.
func _lineup() -> void:
	var ids := ["trex", "triceratops", "dilophosaurus", "raptor", "ranger", "engineer", "hunter", "trapper", "jeep"]
	var origin: Vector2 = Iso.tile_to_world(World.PLAYER_BASE + Vector2i(5, 5))
	var x := -200.0
	for id in ids:
		var u = game.spawn_unit(id, "player", origin + Vector2(x, 0))
		u.set_physics_process(false)
		x += 30.0 + u.sprite.texture.get_width() / float(Defs.SHEET_FRAMES) * 0.7
	await _shot("units", origin + Vector2(x / 2.0 - 120.0, -20), 3.0, false)


func _shot(name: String, pos: Vector2, zoom: float, half: bool = true) -> void:
	game.camera.position = pos
	game.camera.zoom = Vector2(zoom, zoom)
	await _frames(20)
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	if half:
		img.resize(img.get_width() / 2, img.get_height() / 2, Image.INTERPOLATE_NEAREST)
	var path := ProjectSettings.globalize_path("res://screenshots/%s.png" % name)
	img.save_png(path)
	print("[shots] saved ", path)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
