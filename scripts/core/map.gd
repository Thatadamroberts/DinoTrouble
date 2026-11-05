extends RefCounted
## Island terrain grid, decoration placement and A* pathfinding.

enum T { WATER, SAND, GRASS, JUNGLE, DIRT, ROCK }

const TILE_NAMES := ["water", "sand", "grass", "jungle", "dirt", "rock"]
const DECOR_VARIANTS := {
	"tree": 3, "vtree": 2, "palm": 2, "giant_fern": 2, "cycad": 2, "conifer": 2, "stump": 2, "log": 2,
	"bush": 2, "fern_small": 2, "boulder": 2, "tuft": 3, "flowers": 4, "mushrooms": 3, "pebbles": 3,
	"bones": 2, "reeds": 3, "water_rock": 2, "lily": 3,
}
## Decor that does not block movement (water decor sits on unwalkable water anyway).
const WALKABLE_DECOR := ["bush", "fern_small", "tuft", "flowers", "mushrooms", "pebbles", "bones", "reeds", "water_rock", "lily"]
## Per-terrain decor odds as [name, cumulative probability], checked in order.
const DECOR_TABLE := {
	T.JUNGLE: [["tree", 0.18], ["vtree", 0.26], ["palm", 0.31], ["giant_fern", 0.37], ["cycad", 0.41], ["conifer", 0.43],
		["log", 0.45], ["stump", 0.46], ["bush", 0.58], ["fern_small", 0.66], ["mushrooms", 0.70], ["tuft", 0.76]],
	T.GRASS: [["tree", 0.022], ["conifer", 0.03], ["cycad", 0.038], ["palm", 0.05], ["vtree", 0.055], ["stump", 0.06], ["log", 0.065],
		["boulder", 0.075], ["bush", 0.10], ["fern_small", 0.11], ["tuft", 0.24], ["flowers", 0.28], ["pebbles", 0.30],
		["mushrooms", 0.31], ["bones", 0.312]],
	T.SAND: [["palm", 0.05], ["pebbles", 0.08], ["bones", 0.083]],
	T.DIRT: [["boulder", 0.03], ["pebbles", 0.08], ["tuft", 0.11], ["bones", 0.115]],
	T.ROCK: [["boulder", 0.04], ["pebbles", 0.10], ["tuft", 0.12]],
}
const SHORE_TABLE := [["reeds", 0.2], ["palm", 0.26], ["pebbles", 0.3]]
const WATER_TABLE := [["lily", 0.07], ["water_rock", 0.11]]
const CLEAR_TABLE := [["tuft", 0.06], ["flowers", 0.08], ["pebbles", 0.09]]

var size := 64
var tiles := PackedByteArray()
var blocked := PackedByteArray()  # trees, boulders, buildings, resources
var clear := PackedByteArray()  # kept free of decoration
var decor: Array = []  # [{"type": String, "tile": Vector2i, "variant": int}]
var astar := AStarGrid2D.new()
## Bumped whenever blocking changes, so renderers know to refresh.
var version := 0


func idx(t: Vector2i) -> int:
	return t.y * size + t.x


func in_bounds(t: Vector2i) -> bool:
	return t.x >= 0 and t.y >= 0 and t.x < size and t.y < size


func get_tile(t: Vector2i) -> int:
	if not in_bounds(t):
		return T.WATER
	return tiles[idx(t)]


func is_land(t: Vector2i) -> bool:
	return in_bounds(t) and tiles[idx(t)] != T.WATER


func is_jungle(t: Vector2i) -> bool:
	return in_bounds(t) and tiles[idx(t)] == T.JUNGLE


func is_walkable(t: Vector2i) -> bool:
	return is_land(t) and blocked[idx(t)] == 0


func set_blocked(t: Vector2i, value: bool) -> void:
	if not in_bounds(t):
		return
	blocked[idx(t)] = 1 if value else 0
	astar.set_point_solid(t, not is_walkable(t))
	version += 1


func set_footprint(origin: Vector2i, s: int, value: bool) -> void:
	for y in s:
		for x in s:
			set_blocked(origin + Vector2i(x, y), value)


## clearings: Array of [Vector2i centre, float radius] that must be open land.
## roads: Array of [Vector2i a, Vector2i b] dirt tracks guaranteed walkable.
func generate(seed_value: int, clearings: Array, roads: Array) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var n1 := FastNoiseLite.new()
	n1.seed = seed_value
	n1.frequency = 0.06
	var n2 := FastNoiseLite.new()
	n2.seed = seed_value + 7
	n2.frequency = 0.09
	var n3 := FastNoiseLite.new()
	n3.seed = seed_value + 13
	n3.frequency = 0.12

	var count := size * size
	tiles.resize(count)
	blocked.resize(count)
	clear.resize(count)
	blocked.fill(0)
	clear.fill(0)
	decor.clear()

	var c := (size - 1) / 2.0
	for y in size:
		for x in size:
			var d: float = Vector2(x - c, y - c).length() / (size * 0.5)
			var h: float = 1.0 - d * 1.15 + n1.get_noise_2d(x, y) * 0.3
			var t: int = T.GRASS
			if h < 0.05:
				t = T.WATER
			elif h < 0.13:
				t = T.SAND
			elif n2.get_noise_2d(x, y) > 0.18:
				t = T.JUNGLE
			elif n3.get_noise_2d(x, y) > 0.4:
				t = T.DIRT
			elif n3.get_noise_2d(x, y) < -0.55:
				t = T.ROCK
			if x == 0 or y == 0 or x == size - 1 or y == size - 1:
				t = T.WATER
			tiles[y * size + x] = t

	for road in roads:
		_carve_road(road[0], road[1], rng)
	for cl in clearings:
		_make_clearing(cl[0], float(cl[1]))

	_place_decor(rng)
	_setup_astar()
	# Make sure every clearing can reach the first one (the player's base).
	if clearings.size() > 0:
		var home: Vector2i = clearings[0][0]
		var reach := _flood(home)
		for cl in clearings:
			var p: Vector2i = cl[0]
			if not reach.has(p):
				_carve_line(p, Vector2i(size / 2, size / 2))
				_carve_line(Vector2i(size / 2, size / 2), home)
		_setup_astar()


func _make_clearing(center: Vector2i, radius: float) -> void:
	var r := int(ceil(radius))
	for dy in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var p := center + Vector2i(dx, dy)
			if not in_bounds(p) or p.x == 0 or p.y == 0 or p.x == size - 1 or p.y == size - 1:
				continue
			if Vector2(dx, dy).length() > radius:
				continue
			var t: int = tiles[idx(p)]
			if t == T.WATER or t == T.SAND or t == T.JUNGLE:
				tiles[idx(p)] = T.GRASS
			clear[idx(p)] = 1


func _carve_road(a: Vector2i, b: Vector2i, rng: RandomNumberGenerator) -> void:
	var steps := int(Vector2(a).distance_to(Vector2(b)) * 2.0)
	var dir := Vector2(b - a).normalized()
	var perp := Vector2(-dir.y, dir.x)
	var wobble := rng.randf_range(2.0, 4.0)
	for i in steps + 1:
		var f := float(i) / maxi(1, steps)
		var p: Vector2 = Vector2(a).lerp(Vector2(b), f) + perp * sin(f * TAU) * wobble
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				var t := Vector2i(roundi(p.x) + dx, roundi(p.y) + dy)
				if not in_bounds(t) or t.x == 0 or t.y == 0 or t.x == size - 1 or t.y == size - 1:
					continue
				if absi(dx) + absi(dy) <= 1:
					tiles[idx(t)] = T.DIRT
				elif tiles[idx(t)] == T.WATER:
					tiles[idx(t)] = T.SAND
				clear[idx(t)] = 1


func _carve_line(a: Vector2i, b: Vector2i) -> void:
	var steps := int(Vector2(a).distance_to(Vector2(b)) * 2.0)
	for i in steps + 1:
		var p: Vector2 = Vector2(a).lerp(Vector2(b), float(i) / maxi(1, steps))
		var t := Vector2i(roundi(p.x), roundi(p.y))
		if not in_bounds(t):
			continue
		if tiles[idx(t)] == T.WATER:
			tiles[idx(t)] = T.SAND
		if blocked[idx(t)] != 0:
			blocked[idx(t)] = 0
			for j in range(decor.size() - 1, -1, -1):
				if decor[j]["tile"] == t:
					decor.remove_at(j)
		clear[idx(t)] = 1


func _place_decor(rng: RandomNumberGenerator) -> void:
	for y in size:
		for x in size:
			var t := Vector2i(x, y)
			var i := idx(t)
			var kind: int = tiles[i]
			var r := rng.randf()
			var kind_name := ""
			if kind == T.WATER:
				if _touches(t, true):
					kind_name = _pick(WATER_TABLE, r)
			elif clear[i] != 0:
				# open ground keeps only a little low, walkable clutter
				if kind == T.GRASS:
					kind_name = _pick(CLEAR_TABLE, r)
			elif kind == T.SAND and _touches(t, false):
				kind_name = _pick(SHORE_TABLE, r)
			else:
				kind_name = _pick(DECOR_TABLE.get(kind, []), r)
			if kind_name == "":
				continue
			var variants: int = DECOR_VARIANTS[kind_name]
			decor.append({"type": kind_name, "tile": t, "variant": rng.randi_range(0, variants - 1)})
			if not WALKABLE_DECOR.has(kind_name):
				blocked[i] = 1


func _pick(table: Array, r: float) -> String:
	for e in table:
		if r < float(e[1]):
			return e[0]
	return ""


## Water tile next to land (land = true), or land tile next to water (land = false).
func _touches(t: Vector2i, land: bool) -> bool:
	for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		var q: Vector2i = t + d
		if in_bounds(q) and (tiles[idx(q)] != T.WATER) == land:
			return true
	return false


func _setup_astar() -> void:
	astar = AStarGrid2D.new()
	astar.region = Rect2i(0, 0, size, size)
	astar.cell_size = Vector2(1, 1)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.update()
	for y in size:
		for x in size:
			var t := Vector2i(x, y)
			if not is_walkable(t):
				astar.set_point_solid(t, true)


func _flood(start: Vector2i) -> Dictionary:
	var seen := {}
	var s := nearest_walkable(start)
	if not is_walkable(s):
		return seen
	var stack: Array = [s]
	seen[s] = true
	while not stack.is_empty():
		var p: Vector2i = stack.pop_back()
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var q: Vector2i = p + d
			if not seen.has(q) and is_walkable(q):
				seen[q] = true
				stack.append(q)
	return seen


## Closest walkable tile to t (t itself if it is walkable).
func nearest_walkable(t: Vector2i, max_r: int = 12) -> Vector2i:
	if is_walkable(t):
		return t
	for r in range(1, max_r + 1):
		var best := Vector2i(-1, -1)
		var best_d := 1e9
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if maxi(absi(dx), absi(dy)) != r:
					continue
				var p := t + Vector2i(dx, dy)
				if is_walkable(p):
					var dd := float(dx * dx + dy * dy)
					if dd < best_d:
						best_d = dd
						best = p
		if best.x >= 0:
			return best
	return t


## World-space path from one position to another, smoothed.
## Returns an empty array if the goal cannot be reached.
func find_path(from: Vector2, to: Vector2) -> PackedVector2Array:
	var out := PackedVector2Array()
	var a := nearest_walkable(Iso.world_to_tile(from))
	var goal_tile: Vector2i = Iso.world_to_tile(to)
	var exact := is_walkable(goal_tile)
	var b := nearest_walkable(goal_tile)
	if not is_walkable(a) or not is_walkable(b):
		return out
	if a == b:
		out.append(to if exact else Iso.tile_to_world(b))
		return out
	var ids: Array[Vector2i] = astar.get_id_path(a, b)
	if ids.is_empty():
		return out
	var pts: Array = [from]
	for i in range(1, ids.size()):
		pts.append(Iso.tile_to_world(ids[i]))
	if exact:
		pts[pts.size() - 1] = to
	# String-pulling: skip intermediate points while the straight line is clear.
	var i := 0
	while i < pts.size() - 1:
		var j := pts.size() - 1
		while j > i + 1 and not line_clear(pts[i], pts[j]):
			j -= 1
		out.append(pts[j])
		i = j
	return out


func line_clear(a: Vector2, b: Vector2) -> bool:
	var ga: Vector2 = Iso.world_to_grid(a)
	var gb: Vector2 = Iso.world_to_grid(b)
	var steps := int(ga.distance_to(gb) * 5.0) + 1
	for k in steps + 1:
		var g := ga.lerp(gb, float(k) / steps)
		if not is_walkable(Vector2i(roundi(g.x), roundi(g.y))):
			return false
		# avoid squeezing diagonally between two blocked tiles
		if not is_walkable(Vector2i(roundi(g.x + 0.3), roundi(g.y))) and not is_walkable(Vector2i(roundi(g.x), roundi(g.y + 0.3))):
			return false
	return true
