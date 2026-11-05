extends Node2D
## A gatherable resource: amber deposit (DNA) or supply cache (supplies).

var kind_tag := "resource"
var faction := "neutral"
var def_id := ""
var res_type := "dna"
var amount := 0
var max_amount := 1
var radius := 18.0
var tile := Vector2i.ZERO
var dead := false
var selected := false
var hp := 1.0
var max_hp := 1.0
var map = null


func setup(id: String, t: Vector2i, w) -> void:
	def_id = id
	var d: Dictionary = Defs.RESOURCES[id]
	res_type = d["gives"]
	amount = int(d["amount"])
	max_amount = amount
	tile = t
	map = w.map
	position = Iso.tile_to_world(t)
	var sprite := Sprite2D.new()
	sprite.texture = load("res://assets/sprites/resources/%s.png" % id)
	sprite.offset = Vector2(0, -sprite.texture.get_height() / 2.0 + 6.0)
	add_child(sprite)
	map.set_blocked(tile, true)
	add_to_group("resources")
	add_to_group("entities")


func display_name() -> String:
	return Defs.RESOURCES[def_id]["name"]


func set_selected(value: bool) -> void:
	selected = value
	queue_redraw()


func take(n: int) -> int:
	if dead:
		return 0
	var got := mini(n, amount)
	amount -= got
	if amount <= 0:
		dead = true
		map.set_blocked(tile, false)
		remove_from_group("resources")
		remove_from_group("entities")
		if GameState.world != null:
			GameState.world.on_entity_died(self)
		queue_free()
	return got


func _draw() -> void:
	if selected:
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
		draw_arc(Vector2.ZERO, 26.0, 0.0, TAU, 32, Color(1.0, 0.85, 0.4), 2.0)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
