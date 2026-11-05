extends Node2D
## Ambient life: flocks of flying reptiles (with ground shadows), butterflies
## over the grass and fish leaping in the shallows. Only runs near the camera.

const SHEET := preload("res://assets/sprites/ambient/pteranodon.png")
const FRAMES := 4
const ALTITUDE := 150.0
const MAX_BUTTERFLIES := 10

var world = null
var flocks: Array = []
var butterflies: Array = []
var flock_t := 6.0
var fish_t := 3.0
var shadow_layer: Node2D


func setup(w) -> void:
	world = w
	z_index = 36  # above cloud shadows, below fog
	z_as_relative = false
	shadow_layer = Node2D.new()
	shadow_layer.z_index = -2
	shadow_layer.z_as_relative = false
	shadow_layer.draw.connect(_draw_shadows)
	add_child(shadow_layer)


func spawn_flock() -> void:
	var view: Rect2 = world.view_rect()
	var left := randf() < 0.5
	var start := Vector2(view.position.x - 80.0 if left else view.end.x + 80.0, randf_range(view.position.y, view.end.y))
	var vel := Vector2(randf_range(70.0, 95.0) * (1.0 if left else -1.0), randf_range(-12.0, 12.0))
	var birds: Array = []
	for i in randi_range(2, 4):
		birds.append({"off": Vector2(-i * 26.0 * signf(vel.x), randf_range(-18.0, 18.0) + (i % 2) * 10.0), "phase": randf() * 4.0})
	flocks.append({"pos": start, "vel": vel, "birds": birds, "age": 0.0})


func _process(delta: float) -> void:
	if world == null or world.camera == null:
		return
	var view: Rect2 = world.view_rect()
	# flying reptiles
	flock_t -= delta
	if flock_t <= 0.0:
		flock_t = randf_range(20.0, 40.0)
		spawn_flock()
	for fl in flocks:
		fl["pos"] += fl["vel"] * delta
		fl["age"] += delta
		for b in fl["birds"]:
			b["phase"] += delta * 6.0
	flocks = flocks.filter(func(fl): return fl["age"] < 40.0 and view.grow(400.0).has_point(fl["pos"]))
	# butterflies
	while butterflies.size() < MAX_BUTTERFLIES:
		var p := Vector2(randf_range(view.position.x, view.end.x), randf_range(view.position.y, view.end.y))
		if world.map.get_tile(Iso.world_to_tile(p)) == 2:  # grass only
			butterflies.append({"pos": p, "target": p, "t": 0.0, "col": [Color(1.0, 0.85, 0.2), Color(1.0, 1.0, 1.0), Color(0.6, 0.8, 1.0), Color(1.0, 0.5, 0.7)][randi() % 4]})
		else:
			break
	for bf in butterflies:
		bf["t"] += delta
		if bf["pos"].distance_to(bf["target"]) < 2.0:
			bf["target"] = bf["pos"] + Vector2(randf_range(-30, 30), randf_range(-14, 14))
		bf["pos"] = bf["pos"].move_toward(bf["target"], delta * 22.0) + Vector2(0, sin(bf["t"] * 9.0) * 0.4)
	butterflies = butterflies.filter(func(bf): return view.grow(60.0).has_point(bf["pos"]))
	# fish
	fish_t -= delta
	if fish_t <= 0.0:
		fish_t = randf_range(2.0, 5.0)
		for i in 6:
			var q := Vector2(randf_range(view.position.x, view.end.x), randf_range(view.position.y, view.end.y))
			var tile: Vector2i = Iso.world_to_tile(q)
			if world.map.get_tile(tile) == 0 and world.map.in_bounds(tile):
				world.spawn_fx("splash", q)
				world.play_sfx("splash", q, -10.0)
				break
	queue_redraw()
	shadow_layer.queue_redraw()


func _draw() -> void:
	var fw := SHEET.get_width() / float(FRAMES)
	var fh := float(SHEET.get_height())
	for fl in flocks:
		var left: bool = fl["vel"].x < 0.0
		for b in fl["birds"]:
			var p: Vector2 = (fl["pos"] + b["off"]).round()
			var frame := int(b["phase"]) % FRAMES
			var src := Rect2(frame * fw, 0, fw, fh)
			var sx := -1.0 if left else 1.0
			draw_set_transform(p, 0.0, Vector2(sx, 1.0))
			draw_texture_rect_region(SHEET, Rect2(-fw / 2.0, -fh / 2.0, fw, fh), src)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	for bf in butterflies:
		var p2: Vector2 = (bf["pos"] as Vector2).round()
		var open := int(bf["t"] * 14.0) % 2 == 0
		draw_rect(Rect2(p2, Vector2(1, 1)), Color(0.15, 0.1, 0.05))
		if open:
			draw_rect(Rect2(p2 + Vector2(-2, -1), Vector2(2, 2)), bf["col"])
			draw_rect(Rect2(p2 + Vector2(1, -1), Vector2(2, 2)), bf["col"])
		else:
			draw_rect(Rect2(p2 + Vector2(-1, -2), Vector2(1, 2)), bf["col"])
			draw_rect(Rect2(p2 + Vector2(1, -2), Vector2(1, 2)), bf["col"])


func _draw_shadows() -> void:
	for fl in flocks:
		for b in fl["birds"]:
			var p: Vector2 = (fl["pos"] + b["off"] + Vector2(ALTITUDE * 0.4, ALTITUDE)).round()
			shadow_layer.draw_set_transform(p, 0.0, Vector2(1.0, 0.4))
			shadow_layer.draw_circle(Vector2.ZERO, 9.0, Color(0.02, 0.05, 0.02, 0.22))
			shadow_layer.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
