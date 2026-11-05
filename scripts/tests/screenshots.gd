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
	print("[shots] done")
	get_tree().quit(0)


func _shot(name: String, pos: Vector2, zoom: float) -> void:
	game.camera.position = pos
	game.camera.zoom = Vector2(zoom, zoom)
	await _frames(20)
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := ProjectSettings.globalize_path("res://screenshots/%s.png" % name)
	img.save_png(path)
	print("[shots] saved ", path)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
