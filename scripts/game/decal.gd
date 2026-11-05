extends Node2D
## A flat ground mark (blood, oil or scorch) that fades away over time.

const FADE := 6.0

var kind := "blood"
var life := 20.0
var age := 0.0
var blobs: Array = []  # [Vector2 offset, float radius]
var col := Color(0.4, 0.05, 0.04)
var redraw_t := 0.0


func setup(k: String, pos: Vector2, sz: float) -> void:
	kind = k
	position = pos
	z_index = -1
	match kind:
		"oil":
			col = Color(0.07, 0.06, 0.05)
			life = 30.0
		"scorch":
			col = Color(0.1, 0.08, 0.06)
			life = 40.0
		_:
			col = Color(0.42, 0.05, 0.04)
			life = 22.0
	var n := int(3 + sz * 4)
	for i in n:
		var r := randf_range(1.5, 3.5) * sz
		var off := Vector2(randf_range(-7, 7), randf_range(-3, 3)) * sz
		blobs.append([off, r])
	for i in int(sz * 6):  # spatter droplets
		blobs.append([Vector2(randf_range(-14, 14), randf_range(-6, 6)) * sz, 1.0])


func _process(delta: float) -> void:
	age += delta
	if age >= life:
		queue_free()
		return
	if age > life - FADE:
		redraw_t -= delta
		if redraw_t <= 0.0:
			redraw_t = 0.25
			queue_redraw()


func _draw() -> void:
	var a := clampf((life - age) / FADE, 0.0, 1.0) * 0.8
	var c := Color(col, a)
	var dark := Color(col.darkened(0.35), a)
	for b in blobs:
		var off: Vector2 = b[0]
		var r: float = b[1]
		if r <= 1.0:
			draw_rect(Rect2(off.round(), Vector2(1, 1)), dark)
		else:
			draw_set_transform(off.round(), 0.0, Vector2(1.0, 0.5))
			draw_circle(Vector2.ZERO, r, c)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
