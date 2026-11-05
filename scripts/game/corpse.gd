extends Node2D
## A fallen unit: plays the death frames, lingers, then fades away.

const LINGER := 6.0
const FADE := 2.0

var sprite: Sprite2D
var age := 0.0


func setup(u) -> void:
	position = u.position
	sprite = Sprite2D.new()
	sprite.texture = u.sprite.texture
	sprite.hframes = Defs.SHEET_FRAMES
	sprite.frame = Defs.FRAMES_DEATH[0]
	sprite.offset = u.sprite.offset
	sprite.flip_h = u.sprite.flip_h
	add_child(sprite)
	z_index = -1  # lie under the living


func _process(delta: float) -> void:
	age += delta
	if age > 0.25:
		sprite.frame = Defs.FRAMES_DEATH[1]
	if age > LINGER:
		modulate.a = clampf(1.0 - (age - LINGER) / FADE, 0.0, 1.0)
	if age > LINGER + FADE:
		queue_free()
