extends Node
## Day/night cycle: tints the world through dawn, day, dusk and night and
## draws additive glows (windows, lamps, campfires, fires, headlights and
## fireflies) on a layer that follows the camera, so the tint doesn't dim them.

const KEYS := [
	[0.0, Color(0.86, 0.74, 0.72)], [0.08, Color(1.0, 0.96, 0.88)], [0.55, Color(1.0, 0.95, 0.87)],
	[0.62, Color(0.98, 0.66, 0.5)], [0.70, Color(0.30, 0.34, 0.56)], [0.92, Color(0.28, 0.32, 0.54)],
	[1.0, Color(0.86, 0.74, 0.72)],
]
const MAX_FIREFLIES := 24

var world = null
var grade: CanvasModulate
var glow: Node2D
var glow_tex: Texture2D
var fireflies: Array = []
var t_anim := 0.0


func setup(w, grade_node: CanvasModulate) -> void:
	world = w
	grade = grade_node
	var layer := CanvasLayer.new()
	layer.layer = 1
	layer.follow_viewport_enabled = true
	add_child(layer)
	glow = Node2D.new()
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	glow.material = m
	glow.draw.connect(_draw_glows)
	layer.add_child(glow)
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	g.add_point(0.35, Color(1, 1, 1, 0.55))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.width = 64
	gt.height = 64
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	glow_tex = gt
	apply()


static func color_at(t: float) -> Color:
	t = fposmod(t, 1.0)
	for i in range(KEYS.size() - 1):
		var a: Array = KEYS[i]
		var b: Array = KEYS[i + 1]
		if t <= float(b[0]):
			var f := (t - float(a[0])) / (float(b[0]) - float(a[0]))
			return (a[1] as Color).lerp(b[1], f)
	return KEYS[0][1]


func apply() -> void:
	if grade != null:
		grade.color = color_at(GameState.time_of_day)


func _process(delta: float) -> void:
	if world == null:
		return
	t_anim += delta
	if GameState.cycle_enabled and not GameState.over:
		GameState.time_of_day = fposmod(GameState.time_of_day + delta / GameState.DAY_LENGTH, 1.0)
	apply()
	_update_fireflies(delta)
	glow.queue_redraw()


func _update_fireflies(delta: float) -> void:
	var n: float = GameState.night()
	var view: Rect2 = world.view_rect()
	var want := int(MAX_FIREFLIES * clampf((n - 0.4) / 0.6, 0.0, 1.0))
	while fireflies.size() < want:
		var p := Vector2(randf_range(view.position.x, view.end.x), randf_range(view.position.y, view.end.y))
		var tile: int = world.map.get_tile(Iso.world_to_tile(p))
		if tile == 2 or tile == 3:
			fireflies.append({"pos": p, "vel": Vector2.from_angle(randf() * TAU) * 6.0, "phase": randf() * TAU})
		else:
			break
	for f in fireflies:
		f["vel"] = (f["vel"] as Vector2).rotated(randf_range(-1.5, 1.5) * delta)
		f["pos"] += f["vel"] * delta
		f["phase"] += delta * 3.0
	fireflies = fireflies.filter(func(f): return view.grow(40.0).has_point(f["pos"]))
	if fireflies.size() > want:
		fireflies.resize(want)


func _light(pos: Vector2, radius: float, c: Color, view: Rect2) -> void:
	if not view.grow(radius).has_point(pos):
		return
	glow.draw_texture_rect(glow_tex, Rect2(pos - Vector2(radius, radius * 0.75), Vector2(radius * 2.0, radius * 1.5)), false, c)


func _draw_glows() -> void:
	var n: float = GameState.night()
	var view: Rect2 = world.view_rect()
	var flicker := 0.85 + 0.15 * sin(t_anim * 13.0) * sin(t_anim * 7.3)
	for b in get_tree().get_nodes_in_group("buildings"):
		if b.dead or not b.visible:
			continue
		# fires glow day and night, brighter in the dark
		if b.damage_fx != null and b.damage_fx.level == 2:
			_light(b.position + Vector2(0, -b.damage_fx.roof_h * 0.5), 90.0, Color(1.0, 0.45, 0.12, (0.25 + 0.5 * n) * flicker), view)
		if n < 0.03 or not b.built:
			continue
		for l in b.data.get("lights", []):
			var c: Color = l[2]
			var fl := flicker if l.size() > 3 and l[3] else 1.0
			_light(b.position + l[0], float(l[1]), Color(c, c.a * n * fl), view)
	if n >= 0.03:
		for lamp in world.lamps:
			_light(lamp.position + Vector2(6, -40), 48.0, Color(1.0, 0.82, 0.45, 0.7 * n), view)
			_light(lamp.position + Vector2(0, 0), 40.0, Color(1.0, 0.8, 0.45, 0.35 * n), view)
		for u in get_tree().get_nodes_in_group("units"):
			if u.def_id == "jeep" and not u.dead and u.visible:
				var d := Vector2(-1.0 if u.facing_left else 1.0, -0.5 if u.facing_back else 0.5)
				_light(u.position + d * 34.0, 30.0, Color(1.0, 0.95, 0.75, 0.55 * n), view)
	for f in fireflies:
		var a := (0.5 + 0.5 * sin(f["phase"])) * n
		var p: Vector2 = (f["pos"] as Vector2).round()
		glow.draw_rect(Rect2(p, Vector2(1, 1)), Color(0.85, 1.0, 0.45, a))
		_light(p, 5.0, Color(0.7, 1.0, 0.3, a * 0.6), view)
