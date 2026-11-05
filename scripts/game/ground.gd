extends Node2D
## Draws the terrain with res://shaders/ground.gdshader. The map is encoded
## into two small "splat" textures (one texel per tile) that the shader
## samples with linear filtering to blend terrain types, water depth and
## ambient occlusion. They are rebuilt whenever the map changes.

const MARGIN := 24.0  # tiles of ocean drawn around the island
const WATER := 0
const SAND := 1
const GRASS := 2
const JUNGLE := 3
const DIRT := 4
const ROCK := 5
const DEPTH_TILES := 5.0

var map = null
var mat: ShaderMaterial
var splat_a: Image
var splat_b: Image
var tex_a: ImageTexture
var tex_b: ImageTexture
var built_version := -1


func setup(m) -> void:
	map = m
	z_index = -10
	mat = ShaderMaterial.new()
	mat.shader = load("res://shaders/ground.gdshader")
	for n in ["grass", "jungle", "sand", "dirt", "rock"]:
		mat.set_shader_parameter("tex_" + n, load("res://assets/sprites/terrain/%s.png" % n))
	mat.set_shader_parameter("tex_noise", load("res://assets/sprites/terrain/noise.png"))
	mat.set_shader_parameter("map_size", float(m.size))
	material = mat
	splat_a = Image.create(m.size, m.size, false, Image.FORMAT_RGBA8)
	splat_b = Image.create(m.size, m.size, false, Image.FORMAT_RGBA8)
	_rebuild()
	tex_a = ImageTexture.create_from_image(splat_a)
	tex_b = ImageTexture.create_from_image(splat_b)
	mat.set_shader_parameter("splat_a", tex_a)
	mat.set_shader_parameter("splat_b", tex_b)
	queue_redraw()


func _process(_delta: float) -> void:
	if map != null and map.version != built_version:
		_rebuild()
		tex_a.update(splat_a)
		tex_b.update(splat_b)


func _rebuild() -> void:
	built_version = map.version
	var n: int = map.size
	var depth := _water_depth()
	for y in n:
		for x in n:
			var t := Vector2i(x, y)
			var kind: int = map.get_tile(t)
			splat_a.set_pixel(x, y, Color(
				1.0 if kind == WATER else 0.0,
				1.0 if kind == SAND else 0.0,
				1.0 if kind == GRASS else 0.0,
				1.0 if kind == JUNGLE else 0.0))
			splat_b.set_pixel(x, y, Color(
				1.0 if kind == DIRT else 0.0,
				1.0 if kind == ROCK else 0.0,
				depth[y * n + x],
				_occlusion(t)))


## How far each water tile is from land (0 = shore, 1 = open sea).
func _water_depth() -> PackedFloat32Array:
	var n: int = map.size
	var dist := PackedFloat32Array()
	dist.resize(n * n)
	dist.fill(DEPTH_TILES)
	var frontier: Array = []
	for y in n:
		for x in n:
			if map.get_tile(Vector2i(x, y)) != WATER:
				dist[y * n + x] = 0.0
				frontier.append(Vector2i(x, y))
	var step := 0.0
	while not frontier.is_empty() and step < DEPTH_TILES:
		step += 1.0
		var next: Array = []
		for p in frontier:
			for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				var q: Vector2i = p + d
				if q.x < 0 or q.y < 0 or q.x >= n or q.y >= n:
					continue
				var i: int = q.y * n + q.x
				if dist[i] > step:
					dist[i] = step
					next.append(q)
		frontier = next
	for i in dist.size():
		dist[i] = dist[i] / DEPTH_TILES
	return dist


## Soft darkening around obstacles (trees, rocks, buildings).
func _occlusion(t: Vector2i) -> float:
	if not map.is_land(t):
		return 0.0
	var occ := 0.0
	for dy in range(-1, 2):
		for dx in range(-1, 2):
			var q := t + Vector2i(dx, dy)
			if map.in_bounds(q) and map.blocked[map.idx(q)] != 0:
				occ += 0.5 if (dx == 0 and dy == 0) else 0.14
	return clampf(occ, 0.0, 0.85)


func _draw() -> void:
	if map == null:
		return
	var top: Vector2 = Iso.tile_to_world(Vector2(-MARGIN, -MARGIN))
	var right: Vector2 = Iso.tile_to_world(Vector2(map.size + MARGIN, -MARGIN))
	var bottom: Vector2 = Iso.tile_to_world(Vector2(map.size + MARGIN, map.size + MARGIN))
	var left: Vector2 = Iso.tile_to_world(Vector2(-MARGIN, map.size + MARGIN))
	var r := Rect2(Vector2(left.x, top.y), Vector2(right.x - left.x, bottom.y - top.y))
	draw_rect(r, Color.WHITE)
