extends Control
## Diamond-shaped minimap. Left-click/drag moves the camera, right-click
## issues a move/attack command to the selected units.

const TILE_COLORS := [
	Color(0.16, 0.37, 0.56), Color(0.85, 0.76, 0.48), Color(0.31, 0.54, 0.18),
	Color(0.2, 0.38, 0.14), Color(0.54, 0.42, 0.24), Color(0.48, 0.48, 0.43),
]

var world = null
var base_img: Image
var img: Image
var tex: ImageTexture
var timer := 0.0
var size_n := 64
var xform := Transform2D.IDENTITY
var pings: Array = []  # [{pos, t}]


func setup(w) -> void:
	world = w
	size_n = w.map.size
	custom_minimum_size = Vector2(230, 150)
	mouse_filter = Control.MOUSE_FILTER_STOP
	base_img = Image.create(size_n, size_n, false, Image.FORMAT_RGBA8)
	for y in size_n:
		for x in size_n:
			var t := Vector2i(x, y)
			var c: Color = TILE_COLORS[w.map.get_tile(t)]
			if w.map.blocked[w.map.idx(t)] != 0:
				c = c.darkened(0.3)
			base_img.set_pixel(x, y, c)
	img = base_img.duplicate()
	tex = ImageTexture.create_from_image(img)


func ping(pos: Vector2) -> void:
	pings.append({"pos": pos, "t": 3.0})


func _process(delta: float) -> void:
	for p in pings:
		p["t"] -= delta
	pings = pings.filter(func(p): return p["t"] > 0.0)
	timer -= delta
	if timer <= 0.0:
		timer = 0.4
		_refresh()
	queue_redraw()


func _refresh() -> void:
	img.copy_from(base_img)
	var fog = world.fog
	for y in size_n:
		for x in size_n:
			var t := Vector2i(x, y)
			if not fog.tile_explored(t):
				img.set_pixel(x, y, Color(0.02, 0.03, 0.05))
			elif not fog.tile_visible(t):
				img.set_pixel(x, y, img.get_pixel(x, y).darkened(0.45))
	for r in get_tree().get_nodes_in_group("resources"):
		_dot(r.position, Color(1.0, 0.7, 0.2), false, r)
	for e in get_tree().get_nodes_in_group("entities"):
		if e.kind_tag == "resource" or e.dead:
			continue
		var c: Color = Defs.faction_color(e.faction)
		_dot(e.position, c, e.kind_tag == "building", e)
	tex.update(img)


func _dot(pos: Vector2, c: Color, big: bool, e) -> void:
	if not e.visible:
		return
	var t: Vector2i = Iso.world_to_tile(pos)
	var r := 1 if big else 0
	for dy in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var p := t + Vector2i(dx, dy)
			if p.x >= 0 and p.y >= 0 and p.x < size_n and p.y < size_n:
				img.set_pixel(p.x, p.y, c)


func _update_xform() -> void:
	var k: float = minf(size.x / (2.0 * size_n), size.y / float(size_n))
	var oy: float = (size.y - size_n * k) / 2.0
	xform = Transform2D(Vector2(k, k / 2.0), Vector2(-k, k / 2.0), Vector2(size.x / 2.0, oy))


## World position -> minimap local position.
func world_to_mini(p: Vector2) -> Vector2:
	var g: Vector2 = Iso.world_to_grid(p) + Vector2(0.5, 0.5)
	return xform * g


func mini_to_world(p: Vector2) -> Vector2:
	var g: Vector2 = xform.affine_inverse() * p - Vector2(0.5, 0.5)
	return Iso.tile_to_world(g)


func _draw() -> void:
	_update_xform()
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.03, 0.06, 0.1))
	draw_set_transform_matrix(xform)
	draw_texture(tex, Vector2.ZERO)
	draw_set_transform_matrix(Transform2D.IDENTITY)
	if world != null and world.camera != null:
		var r: Rect2 = world.view_rect()
		var pts := PackedVector2Array([
			world_to_mini(r.position), world_to_mini(Vector2(r.end.x, r.position.y)),
			world_to_mini(r.end), world_to_mini(Vector2(r.position.x, r.end.y)),
			world_to_mini(r.position)])
		draw_polyline(pts, Color(1, 1, 1, 0.8), 1.0)
	for p in pings:
		var mp := world_to_mini(p["pos"])
		var f: float = fmod(p["t"], 1.0)
		draw_arc(mp, 4.0 + (1.0 - f) * 10.0, 0.0, TAU, 16, Color(1, 0.3, 0.2, f), 2.0)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			world.camera.focus_on(mini_to_world(event.position))
			accept_event()
		elif event.button_index == MOUSE_BUTTON_RIGHT:
			world.selection.command_at(mini_to_world(event.position))
			accept_event()
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
		world.camera.focus_on(mini_to_world(event.position))
		accept_event()
