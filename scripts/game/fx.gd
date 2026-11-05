extends Node2D
## Short-lived visual effects drawn procedurally.

static var _add_mat: CanvasItemMaterial = null

var kind := "puff"
var color := Color.WHITE
var size := 1.0
var life := 0.5
var age := 0.0
var seeds: Array = []


func setup(k: String, pos: Vector2, c: Color, sz: float = 1.0) -> void:
	kind = k
	position = pos
	color = c
	size = sz
	match kind:
		"roar":
			life = 0.8
		"collapse":
			life = 1.0
		"hearts":
			life = 1.0
		"marker":
			life = 0.45
		"spark":
			life = 0.15
		"flash":
			life = 0.12
			if _add_mat == null:
				_add_mat = CanvasItemMaterial.new()
				_add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
			material = _add_mat
		"splash":
			life = 1.0
		"debris":
			life = 0.6
		"dust":
			life = 0.55
		_:
			life = 0.5
	for i in 8:
		seeds.append(Vector2(randf_range(-1, 1), randf_range(-1, 1)))


func _process(delta: float) -> void:
	age += delta
	if age >= life:
		queue_free()
		return
	queue_redraw()


func _draw() -> void:
	var f := age / life
	var a := 1.0 - f
	match kind:
		"puff":
			for s in seeds:
				draw_circle(Vector2(s.x * 14.0, s.y * 6.0 - 6.0) * (0.4 + f), 4.0 * (1.0 - f * 0.5), Color(color, a * 0.8))
		"dust":
			# low, wide puffs kicked up by feet and wheels
			for s in seeds:
				var p := Vector2(s.x * 10.0 * size, s.y * 2.5 * size - 2.0 - f * 5.0 * size) * (0.5 + f)
				draw_rect(Rect2(p.round(), Vector2.ONE * maxf(1.0, round(3.0 * size * (1.0 - f * 0.4)))), Color(0.72, 0.62, 0.46, a * 0.55))
		"collapse":
			for s in seeds:
				draw_circle(Vector2(s.x * 50.0, s.y * 20.0 - 20.0) * (0.3 + f), 10.0 * (1.0 - f * 0.4), Color(0.45, 0.4, 0.35, a * 0.7))
		"roar":
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
			for i in 3:
				var r := (f + i * 0.15) * 200.0
				draw_arc(Vector2.ZERO, r, 0.0, TAU, 40, Color(1.0, 0.85, 0.5, a * 0.6), 3.0)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		"spark":
			for s in seeds:
				draw_line(Vector2.ZERO, s * 6.0, Color(1.0, 0.9, 0.5, a), 1.0)
		"flash":
			# additive glow plus a hard pixel star
			draw_circle(Vector2.ZERO, 12.0 * size * (1.0 - f * 0.5), Color(color.r * 0.5, color.g * 0.4, color.b * 0.2, a * 0.5))
			draw_circle(Vector2.ZERO, 5.0 * size, Color(color, a * 0.8))
			if f < 0.5:
				for d in [Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1)]:
					draw_rect(Rect2((d * 4.0 * size).round(), Vector2(2, 2)), Color(1, 1, 0.85, a))
		"splat":
			for s in seeds:
				draw_circle(s * 6.0 * (0.5 + f), 2.0, Color(0.5, 1.0, 0.3, a))
		"splash":
			# a fish leaps in an arc, then rings and droplets
			if f < 0.45:
				var t := f / 0.45
				var fp := Vector2(-8.0 + 16.0 * t, -sin(t * PI) * 14.0)
				draw_rect(Rect2(fp.round(), Vector2(3, 1)), Color(0.75, 0.82, 0.86))
				draw_rect(Rect2((fp + Vector2(-1, 1)).round(), Vector2(1, 1)), Color(0.45, 0.55, 0.6))
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.45))
			for i in 2:
				var rr := (f * 1.2 - i * 0.25) * 18.0
				if rr > 0.0:
					draw_arc(Vector2.ZERO, rr, 0.0, TAU, 18, Color(0.85, 0.95, 0.95, a * 0.8), 1.0)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
			if f > 0.4:
				for s in seeds:
					var t2 := (f - 0.4) / 0.6
					var dp := Vector2(s.x * 8.0 * t2, -absf(s.y) * 10.0 * t2 + 22.0 * t2 * t2 - 2.0)
					draw_rect(Rect2(dp.round(), Vector2.ONE), Color(0.9, 0.97, 1.0, a))
		"debris":
			for s in seeds:
				var dp := Vector2(s.x * 18.0 * f, -absf(s.y) * 22.0 * f + 40.0 * f * f)
				draw_rect(Rect2(dp.round(), Vector2(2, 2)), Color(color, a))
		"hearts":
			for i in 3:
				var p := Vector2((i - 1) * 9.0, -f * 22.0 - absf(i - 1) * 3.0)
				_heart(p, Color(1.0, 0.45, 0.6, a))
		"marker":
			draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
			draw_arc(Vector2.ZERO, 14.0 * (1.0 - f * 0.6), 0.0, TAU, 20, Color(color, a), 2.0)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _heart(p: Vector2, c: Color) -> void:
	draw_circle(p + Vector2(-2, 0), 2.5, c)
	draw_circle(p + Vector2(2, 0), 2.5, c)
	draw_colored_polygon(PackedVector2Array([p + Vector2(-4.5, 1), p + Vector2(4.5, 1), p + Vector2(0, 6)]), c)
