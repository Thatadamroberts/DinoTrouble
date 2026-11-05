extends Node2D
## Bullets, venom globs and nets. Homes in on the target and applies the hit.

var attacker = null
var target = null
var kind := "bullet"
var damage := 0.0
var speed := 520.0
var dest := Vector2.ZERO
var start := Vector2.ZERO
var world = null
var travelled := 0.0
var total := 1.0


func setup(w, from_ent, to_ent, k: String, dmg: float, from_pos: Vector2) -> void:
	world = w
	attacker = from_ent
	target = to_ent
	kind = k
	damage = dmg
	position = from_pos
	start = from_pos
	dest = to_ent.position + Vector2(0, -10)
	total = maxf(1.0, start.distance_to(dest))
	if kind == "venom":
		speed = 300.0
	elif kind == "net":
		speed = 260.0


func _physics_process(delta: float) -> void:
	if target != null and is_instance_valid(target) and not target.dead:
		dest = target.position + Vector2(0, -10)
	var to := dest - position
	var step := speed * delta
	travelled += step
	if to.length() <= step:
		_hit()
		return
	position += to.normalized() * step
	queue_redraw()


func _hit() -> void:
	if target != null and is_instance_valid(target) and not target.dead:
		world.apply_hit(attacker, target, damage, kind)
	queue_free()


func _draw() -> void:
	# Lobbed projectiles arc upward.
	var lift := 0.0
	if kind != "bullet":
		var f := clampf(travelled / total, 0.0, 1.0)
		lift = -sin(f * PI) * 18.0
	match kind:
		"bullet":
			var dir := (dest - position).normalized()
			draw_line(-dir * 6.0, Vector2.ZERO, Color(1.0, 0.95, 0.6), 2.0)
		"venom":
			draw_circle(Vector2(0, lift), 3.5, Color(0.5, 1.0, 0.3))
			draw_circle(Vector2(-1, lift - 1), 1.5, Color(0.85, 1.0, 0.7))
		"net":
			var c := Color(0.85, 0.85, 0.75)
			var o := Vector2(0, lift)
			draw_arc(o, 5.0, 0.0, TAU, 12, c, 1.0)
			draw_line(o + Vector2(-5, 0), o + Vector2(5, 0), c, 1.0)
			draw_line(o + Vector2(0, -5), o + Vector2(0, 5), c, 1.0)
