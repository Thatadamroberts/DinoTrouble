extends Node2D
## Draws the isometric terrain tiles (redrawn only when the map changes).

const MapScript = preload("res://scripts/core/map.gd")
const MARGIN := 14  # extra ocean drawn around the island

var map = null
var tex := {}


func setup(m) -> void:
	map = m
	z_index = -10
	for i in MapScript.TILE_NAMES.size():
		var name_str: String = MapScript.TILE_NAMES[i]
		var arr: Array = []
		for v in 3:
			arr.append(load("res://assets/sprites/tiles/%s_%d.png" % [name_str, v]))
		tex[i] = arr
	queue_redraw()


func _draw() -> void:
	if map == null:
		return
	var off := Vector2(32, 16)
	for y in range(-MARGIN, map.size + MARGIN):
		for x in range(-MARGIN, map.size + MARGIN):
			var t: int = map.get_tile(Vector2i(x, y))
			var arr: Array = tex[t]
			var v: int = absi(x * 7 + y * 13) % arr.size()
			draw_texture(arr[v], Iso.tile_to_world(Vector2(x, y)) - off)
