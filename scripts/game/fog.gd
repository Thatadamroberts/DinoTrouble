extends Node2D
## Fog of war. Keeps explored/visible grids for the player and draws a
## smooth overlay by stretching a 1-pixel-per-tile texture onto the iso grid.

const UPDATE_INTERVAL := 0.2

var world = null
var size := 64
var explored := PackedByteArray()
var seen := PackedByteArray()
var img: Image
var tex: ImageTexture
var timer := 0.0
var enabled := true


func setup(w) -> void:
	world = w
	size = w.map.size
	explored.resize(size * size)
	explored.fill(0)
	seen.resize(size * size)
	seen.fill(0)
	img = Image.create(size, size, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.02, 0.03, 0.05, 1.0))
	tex = ImageTexture.create_from_image(img)
	z_index = 40
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR


func tile_visible(t: Vector2i) -> bool:
	if not enabled:
		return true
	if t.x < 0 or t.y < 0 or t.x >= size or t.y >= size:
		return false
	return seen[t.y * size + t.x] != 0


func tile_explored(t: Vector2i) -> bool:
	if not enabled:
		return true
	if t.x < 0 or t.y < 0 or t.x >= size or t.y >= size:
		return false
	return explored[t.y * size + t.x] != 0


func _process(delta: float) -> void:
	timer -= delta
	if timer > 0.0:
		return
	timer = UPDATE_INTERVAL
	recompute()


func recompute() -> void:
	seen.fill(0)
	for e in get_tree().get_nodes_in_group("faction_player"):
		if e.dead:
			continue
		var c: Vector2i = Iso.world_to_tile(e.position)
		var r: int = maxi(2, int(round(float(e.data.get("sight", 6)) * GameState.sight_mult())))
		var r2 := r * r
		for dy in range(-r, r + 1):
			var y := c.y + dy
			if y < 0 or y >= size:
				continue
			for dx in range(-r, r + 1):
				var x := c.x + dx
				if x < 0 or x >= size or dx * dx + dy * dy > r2:
					continue
				var i := y * size + x
				seen[i] = 1
				explored[i] = 1
	for y in size:
		for x in size:
			var i := y * size + x
			var a := 0.0
			if not enabled:
				a = 0.0
			elif seen[i] == 0:
				a = 0.5 if explored[i] != 0 else 1.0
			img.set_pixel(x, y, Color(0.02, 0.03, 0.05, a))
	tex.update(img)
	# Hide enemies outside vision; buildings stay visible once explored.
	for e in get_tree().get_nodes_in_group("entities"):
		if e.faction == "player":
			e.visible = true
			continue
		var t: Vector2i = Iso.world_to_tile(e.position)
		if e.kind_tag == "unit":
			e.visible = tile_visible(t)
		else:
			e.visible = tile_explored(t)
	queue_redraw()


func _draw() -> void:
	# Grid pixel (i, j) spans grid coords [i - 0.5, i + 0.5]; map that onto
	# the iso diamond for tile (i, j).
	draw_set_transform_matrix(Transform2D(Vector2(32, 16), Vector2(-32, 16), Vector2(0, -16)))
	draw_texture(tex, Vector2.ZERO)
	draw_set_transform_matrix(Transform2D.IDENTITY)
