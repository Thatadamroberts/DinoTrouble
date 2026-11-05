extends Node2D
## Short-lived visual effects drawn procedurally.

var kind := "puff"
var color := Color.WHITE
var life := 0.5
var age := 0.0
var seeds: Array = []


func setup(k: String, pos: Vector2, c: Color) -> void:
	kind = k
	position = pos
	color = c
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
		"puff", "dust":
			var c := color if kind == "puff" else Color(0.7, 0.6, 0.45)
			for s in seeds:
				draw_circle(Vector2(s.x * 14.0, s.y * 6.0 - 6.0) * (0.4 + f), 4.0 * (1.0 - f * 0.5), Color(c, a * 0.8))
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
		"splat":
			for s in seeds:
				draw_circle(s * 6.0 * (0.5 + f), 2.0, Color(0.5, 1.0, 0.3, a))
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
