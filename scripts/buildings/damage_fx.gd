extends Node2D
## Smoke, fire and sparks rising from a damaged building, or the dying
## smoulder of rubble. Particles are plain dictionaries drawn as pixels.

const MAX_PARTS := 70

var building = null
var world = null
var size := 2
var roof_h := 40.0
var smoulder := 0.0  # > 0 for rubble: seconds left to smoke
var level := 0  # 0 none, 1 smoke, 2 fire
var parts: Array = []
var emit_t := 0.0
var sources: Array = []


func setup_building(b) -> void:
	building = b
	world = b.world
	size = b.size
	roof_h = b.sprite.texture.get_height() - size * 16.0
	_pick_sources()


func setup_rubble(w, s: int, seconds: float) -> void:
	world = w
	size = s
	roof_h = 8.0
	smoulder = seconds
	_pick_sources()


func _ready() -> void:
	z_index = 25


func _pick_sources() -> void:
	sources.clear()
	for i in 3:
		sources.append(Vector2(randf_range(-size * 18.0, size * 18.0), -randf_range(roof_h * 0.35, roof_h * 0.8)))


func _process(delta: float) -> void:
	if building != null:
		if not is_instance_valid(building) or building.dead:
			return
		var f: float = building.hp / building.max_hp
		level = 0 if (not building.built or f > 0.66) else (1 if f > 0.33 else 2)
		if building.built:
			building.sprite.modulate = Color(0.78, 0.72, 0.68) if level == 2 else Color.WHITE
	elif smoulder > 0.0:
		smoulder -= delta
		level = 1
	else:
		level = 0
	var on_screen: bool = world == null or world.view_rect().grow(250.0).has_point(global_position)
	if level > 0 and on_screen:
		emit_t -= delta
		while emit_t <= 0.0 and parts.size() < MAX_PARTS:
			emit_t += 0.09 if level == 1 else 0.035
			_emit()
	for p in parts:
		p["age"] += delta
		var t: float = p["age"] / p["life"]
		match p["kind"]:
			"smoke":
				p["pos"] += Vector2(6.0 + t * 8.0, -22.0) * delta
			"fire":
				p["pos"] += Vector2(randf_range(-6.0, 6.0), -30.0) * delta
			"spark":
				p["vel"] += Vector2(0, 70.0) * delta
				p["pos"] += p["vel"] * delta
	parts = parts.filter(func(p): return p["age"] < p["life"])
	if not parts.is_empty() or level > 0:
		queue_redraw()


func _emit() -> void:
	var src: Vector2 = sources[randi() % sources.size()]
	var jitter := Vector2(randf_range(-3, 3), randf_range(-2, 2))
	if level == 2 and randf() < 0.65:
		parts.append({"kind": "fire", "pos": src + jitter, "age": 0.0, "life": randf_range(0.35, 0.7)})
	if level == 2 and randf() < 0.08:
		parts.append({"kind": "spark", "pos": src, "vel": Vector2(randf_range(-20, 20), randf_range(-60, -30)), "age": 0.0, "life": 0.8})
	parts.append({"kind": "smoke", "pos": src + jitter, "age": 0.0, "life": randf_range(1.6, 2.6) * (1.3 if level == 2 else 1.0),
		"dark": level == 2})


func _draw() -> void:
	for p in parts:
		var t: float = p["age"] / p["life"]
		var pos: Vector2 = (p["pos"] as Vector2).round()
		match p["kind"]:
			"smoke":
				# puffy pixel clouds that grow as they rise and fade out
				var s := roundf(4.0 + t * (13.0 if p["dark"] else 9.0))
				var g := 0.16 if p["dark"] else 0.62
				var a := pow(1.0 - t, 0.7) * (0.75 if p["dark"] else 0.55)
				draw_rect(Rect2(pos - Vector2(s, s) * 0.5, Vector2(s, s)), Color(g, g, g * 0.95, a))
				var s2 := roundf(s * 0.6)
				draw_rect(Rect2(pos - Vector2(s * 0.5 + 1.0, s * 0.5 + 1.0), Vector2(s2, s2)), Color(g + 0.12, g + 0.12, g + 0.1, a * 0.8))
			"fire":
				var c := Color(1.0, 0.95, 0.5).lerp(Color(1.0, 0.45, 0.1), t).lerp(Color(0.7, 0.1, 0.05), maxf(0.0, t - 0.5) * 2.0)
				var fs := roundf(6.0 - t * 3.0)
				draw_rect(Rect2(pos - Vector2(fs, fs) * 0.5, Vector2(fs, fs + 2.0)), Color(c, 1.0 - t * 0.5))
			"spark":
				draw_rect(Rect2(pos, Vector2(1, 1)), Color(1.0, 0.85, 0.4, 1.0 - t))
