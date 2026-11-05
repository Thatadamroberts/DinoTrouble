extends Node2D
## Health / hunger / progress bars drawn above a unit or building.

var ent = null
var width := 24.0


func _ready() -> void:
	z_index = 30


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	if ent == null or ent.dead:
		return
	var y := 0.0
	var show_hp: bool = ent.selected or ent.hp < ent.max_hp
	if show_hp:
		_bar(y, ent.hp / ent.max_hp, _hp_color(ent.hp / ent.max_hp))
		y += 5.0
	if ent.kind_tag == "unit":
		if ent.is_dino() and ent.faction == "player" and GameState.hunger_enabled and (ent.selected or ent.hunger < 35.0):
			_bar(y, ent.hunger / 100.0, Color(0.95, 0.6, 0.15))
			y += 5.0
		if ent.tame_t > 0.0:
			_bar(y, ent.tame_t / ent.tame_needed, Color(0.4, 0.8, 1.0))
		if ent.feral:
			_text(Vector2(-3, -6), "!", Color(1, 0.3, 0.2))
		elif ent.stun_t > 0.0:
			_text(Vector2(-6, -6), "zz", Color(0.8, 0.9, 1.0))
		elif ent.carry > 0:
			var c := Color(1.0, 0.65, 0.15) if ent.carry_type == "dna" else Color(0.75, 0.55, 0.3)
			draw_rect(Rect2(-3, -9, 6, 5), c)
	elif ent.kind_tag == "building":
		if not ent.built:
			_bar(y, ent.progress, Color(0.4, 0.75, 1.0))
		elif ent.selected and not ent.queue.is_empty():
			_bar(y, ent.queue_progress(), Color(0.4, 0.75, 1.0))


func _bar(y: float, f: float, c: Color) -> void:
	f = clampf(f, 0.0, 1.0)
	draw_rect(Rect2(-width / 2.0 - 1.0, y - 1.0, width + 2.0, 5.0), Color(0, 0, 0, 0.75))
	draw_rect(Rect2(-width / 2.0, y, width * f, 3.0), c)


func _hp_color(f: float) -> Color:
	if f > 0.6:
		return Color(0.3, 0.9, 0.3)
	if f > 0.3:
		return Color(0.95, 0.8, 0.2)
	return Color(0.9, 0.25, 0.2)


func _text(pos: Vector2, s: String, c: Color) -> void:
	draw_string(ThemeDB.fallback_font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, c)
