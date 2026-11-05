extends Node2D
## Main game scene. Builds the island, spawns everything, and offers queries
## (targets, resources, drop-offs) that units, buildings and AI rely on.

const MapScript = preload("res://scripts/core/map.gd")
const UnitScript = preload("res://scripts/units/unit.gd")
const BuildingScript = preload("res://scripts/buildings/building.gd")
const ResourceScript = preload("res://scripts/game/resource_node.gd")
const ProjectileScript = preload("res://scripts/game/projectile.gd")
const FxScript = preload("res://scripts/game/fx.gd")
const GroundScript = preload("res://scripts/game/ground.gd")
const FogScript = preload("res://scripts/game/fog.gd")
const SelectionScript = preload("res://scripts/game/selection.gd")
const CameraScript = preload("res://scripts/game/rts_camera.gd")
const HudScript = preload("res://scripts/ui/hud.gd")
const AIScript = preload("res://scripts/ai/poacher_ai.gd")
const CorpseScript = preload("res://scripts/game/corpse.gd")
const DecalScript = preload("res://scripts/game/decal.gd")
const DamageFxScript = preload("res://scripts/buildings/damage_fx.gd")
const AmbientScript = preload("res://scripts/game/ambient.gd")
const DayNightScript = preload("res://scripts/game/day_night.gd")
const MissionsScript = preload("res://scripts/core/missions.gd")
const MissionScript = preload("res://scripts/game/mission.gd")
const MAX_DECALS := 60

const MAP_SIZE := 64
const PLAYER_BASE := Vector2i(14, 49)
const ENEMY_BASE := Vector2i(49, 14)
const HASH_CELL := 64.0

const PLAYER_AMBER := [Vector2i(9, 44), Vector2i(19, 54)]
const PLAYER_CRATES := [Vector2i(8, 51), Vector2i(22, 47)]
const ENEMY_AMBER := [Vector2i(44, 9), Vector2i(54, 19)]
const ENEMY_CRATES := [Vector2i(51, 8), Vector2i(47, 22)]
const MID_AMBER := [Vector2i(31, 31), Vector2i(24, 22), Vector2i(40, 41)]
const MID_CRATES := [Vector2i(22, 34), Vector2i(41, 28), Vector2i(33, 45), Vector2i(29, 17)]
## [species, home tile, count]
const WILD_GROUPS := [
	["raptor", Vector2i(36, 25), 3],
	["triceratops", Vector2i(24, 38), 2],
	["dilophosaurus", Vector2i(43, 35), 2],
	["triceratops", Vector2i(37, 47), 1],
	["raptor", Vector2i(26, 13), 2],
]

var map_seed := -1
var map = null
var ground: Node2D
var entities: Node2D
var ground_decor: Node2D
var projectiles: Node2D
var fog = null
var selection = null
var camera = null
var hud = null
var ai = null

var grid_hash := {}
var alert_cd := 0.0
var spawn_count := {}
var decals: Array = []
var ambient = null
var power_lines: Node2D
var poles: Array = []
var lamps: Array = []
var grade: CanvasModulate
var day_night = null
var mission: Dictionary = {}
var mission_node = null


func _ready() -> void:
	GameState.reset()
	GameState.world = self
	mission = MissionsScript.get_mission(GameState.mission_id)
	var save = GameState.pending_save
	if save != null:
		map_seed = int(save["seed"])
	elif map_seed < 0:
		map_seed = int(mission["seed"]) if int(mission["seed"]) >= 0 else randi() % 100000
	GameState.time_of_day = float(mission.get("time", 0.15))
	GameState.cycle_enabled = bool(mission.get("cycle", true))
	_build_map()

	ground = GroundScript.new()
	ground.name = "Ground"
	add_child(ground)
	ground.setup(map)

	ground_decor = Node2D.new()
	ground_decor.name = "GroundDecor"
	add_child(ground_decor)

	entities = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	add_child(entities)

	projectiles = Node2D.new()
	projectiles.name = "Projectiles"
	projectiles.z_index = 20
	add_child(projectiles)

	_setup_atmosphere()

	fog = FogScript.new()
	fog.name = "Fog"
	fog.setup(self)
	add_child(fog)

	selection = SelectionScript.new()
	selection.name = "Selection"
	selection.setup(self)
	add_child(selection)

	camera = CameraScript.new()
	camera.name = "Camera"
	camera.setup(self)
	add_child(camera)

	_setup_audio()
	_spawn_decor()
	if save != null:
		SaveSystem.restore(self, save)
		GameState.pending_save = null
	else:
		_spawn_start()
	_spawn_base_props()

	day_night = DayNightScript.new()
	day_night.name = "DayNight"
	add_child(day_night)
	day_night.setup(self, grade)

	ambient = AmbientScript.new()
	ambient.name = "Ambient"
	add_child(ambient)
	ambient.setup(self)

	mission_node = MissionScript.new()
	mission_node.name = "Mission"
	add_child(mission_node)
	mission_node.setup(self, mission)

	ai = AIScript.new()
	ai.name = "PoacherAI"
	ai.setup(self)
	add_child(ai)

	hud = HudScript.new()
	hud.name = "HUD"
	add_child(hud)
	hud.setup(self)

	focus_home()
	if SaveSystem.pending_camera != null:
		camera.focus_on(SaveSystem.pending_camera)
		SaveSystem.pending_camera = null
	fog.recompute()
	var autosave := Timer.new()
	autosave.wait_time = 120.0
	autosave.autostart = true
	autosave.timeout.connect(func(): SaveSystem.save_game(self, SaveSystem.AUTOSAVE))
	add_child(autosave)
	GameState.game_over.connect(_on_game_over)
	if save == null:
		hud.show_briefing(mission)


func _build_map() -> void:
	map = MapScript.new()
	map.size = MAP_SIZE
	var clearings: Array = [[PLAYER_BASE, 9.0], [ENEMY_BASE, 9.0]]
	for t in PLAYER_AMBER + PLAYER_CRATES + ENEMY_AMBER + ENEMY_CRATES + MID_AMBER + MID_CRATES:
		clearings.append([t, 1.6])
	for g in WILD_GROUPS:
		clearings.append([g[1], 2.5])
	var center := Vector2i(MAP_SIZE / 2, MAP_SIZE / 2)
	var roads: Array = [[PLAYER_BASE, center], [center, ENEMY_BASE]]
	map.generate(map_seed, clearings, roads)


## Pixels between the bottom of a decor sprite and the point it stands on,
## and how strongly it sways in the wind.
const DECOR_STYLE := {
	"tree": {"base": 6, "x": 4, "sway": 1.0},
	"vtree": {"base": 6, "x": 4, "sway": 1.0},
	"palm": {"base": 6, "x": 4, "sway": 2.0},
	"giant_fern": {"base": 6, "x": 4, "sway": 1.6},
	"cycad": {"base": 6, "x": 4, "sway": 0.8},
	"conifer": {"base": 6, "x": 4, "sway": 0.8},
	"stump": {"base": 4, "x": 2, "sway": 0.0},
	"log": {"base": 6, "x": 0, "sway": 0.0},
	"bush": {"base": 3, "x": 0, "sway": 1.0},
	"fern_small": {"base": 3, "x": 0, "sway": 1.0},
	"boulder": {"base": 4, "x": 0, "sway": 0.0},
	"tuft": {"base": 2, "x": 0, "sway": 1.0},
	"flowers": {"base": 2, "x": 0, "sway": 1.0},
	"mushrooms": {"base": 2, "x": 0, "sway": 0.0},
	"pebbles": {"base": 3, "x": 0, "sway": 0.0},
	"bones": {"base": 4, "x": 0, "sway": 0.0},
	"reeds": {"base": 2, "x": 0, "sway": 1.5},
	"water_rock": {"base": 8, "x": 0, "sway": 0.0},
	"lily": {"base": 6, "x": 0, "sway": 0.0},
}
## Flat decor drawn under units instead of depth-sorted with them.
const GROUND_DECOR := ["tuft", "flowers", "mushrooms", "pebbles", "bones", "lily", "water_rock"]


func _spawn_decor() -> void:
	var textures := {}
	var sway_shader: Shader = load("res://shaders/sway.gdshader")
	var materials := {}
	for d in map.decor:
		var kind: String = d["type"]
		var key := "%s_%d" % [kind, d["variant"]]
		if not textures.has(key):
			textures[key] = load("res://assets/sprites/decor/%s.png" % key)
		var style: Dictionary = DECOR_STYLE.get(kind, {"base": 4, "x": 0, "sway": 0.0})
		var s := Sprite2D.new()
		var tex: Texture2D = textures[key]
		s.texture = tex
		var walkable: bool = MapScript.WALKABLE_DECOR.has(kind)
		var jitter := Vector2(randf_range(-12, 12), randf_range(-6, 6)) if walkable else Vector2(randf_range(-4, 4), randf_range(-2, 2))
		s.position = Iso.tile_to_world(d["tile"]) + jitter
		s.offset = Vector2(float(style["x"]), -tex.get_height() / 2.0 + float(style["base"]))
		var amount: float = style["sway"]
		if amount > 0.0:
			if not materials.has(amount):
				var m := ShaderMaterial.new()
				m.shader = sway_shader
				m.set_shader_parameter("amount", amount)
				m.set_shader_parameter("speed", 1.1 + amount * 0.2)
				materials[amount] = m
			s.material = materials[amount]
		if GROUND_DECOR.has(kind):
			s.z_index = -1  # always under units walking through them
			ground_decor.add_child(s)
		else:
			entities.add_child(s)


func _spawn_start() -> void:
	spawn_building("ranger_station", "player", Vector2i(13, 48), true)
	spawn_building("hatchery", "player", Vector2i(17, 44), true)
	for e in mission.get("enemy_buildings", []):
		spawn_building(e[0], "poacher", e[1], true)
	if GameState.difficulty >= 2:
		for e in mission.get("hard_extra", []):
			spawn_building(e[0], "poacher", e[1], true)
	for f in ["player", "poacher"]:
		var key := "player_res" if f == "player" else "enemy_res"
		if mission.has(key):
			GameState.resources[f] = {"dna": float(mission[key]["dna"]), "supplies": float(mission[key]["supplies"])}
	GameState.resources_changed.emit()

	for t in PLAYER_AMBER + ENEMY_AMBER + MID_AMBER:
		spawn_resource("amber", t)
	for t in PLAYER_CRATES + ENEMY_CRATES + MID_CRATES:
		spawn_resource("crates", t)

	var p0 := PLAYER_BASE + Vector2i(3, 3)
	for id in mission.get("player_units", MissionsScript.DEFAULT_PLAYER_UNITS):
		if Defs.UNITS[id]["kind"] == "dino":
			spawn_unit(id, "player", free_spot(Vector2i(20, 48)))  # by the hatchery's feeders
		else:
			spawn_unit(id, "player", free_spot(p0))
	var e0 := ENEMY_BASE + Vector2i(3, 3)
	for id in mission.get("enemy_units", []):
		spawn_unit(id, "poacher", free_spot(e0))
	for g in WILD_GROUPS:
		for i in int(g[2]):
			spawn_unit(g[0], "wild", free_spot(g[1]))


## World position on a walkable tile near t, with a little jitter.
func free_spot(t: Vector2i) -> Vector2:
	var w: Vector2i = map.nearest_walkable(t + Vector2i(randi_range(-1, 1), randi_range(-1, 1)))
	return Iso.tile_to_world(w) + Vector2(randf_range(-10, 10), randf_range(-5, 5))


## Warm colour grading, drifting cloud shadows and a screen vignette.
func _setup_atmosphere() -> void:
	grade = CanvasModulate.new()
	grade.color = Color(1.0, 0.96, 0.88)
	add_child(grade)

	var clouds := Node2D.new()
	clouds.name = "CloudShadows"
	clouds.z_index = 35
	var cm := ShaderMaterial.new()
	cm.shader = load("res://shaders/clouds.gdshader")
	cm.set_shader_parameter("tex_noise", load("res://assets/sprites/terrain/noise.png"))
	clouds.material = cm
	clouds.draw.connect(func():
		var span := MAP_SIZE * 32.0 + 1200.0
		clouds.draw_rect(Rect2(-span, -800.0, span * 2.0, MAP_SIZE * 32.0 + 1600.0), Color.WHITE)
	)
	add_child(clouds)
	clouds.queue_redraw()

	var layer := CanvasLayer.new()
	layer.layer = 5
	var vignette := ColorRect.new()
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var vm := ShaderMaterial.new()
	vm.shader = load("res://shaders/vignette.gdshader")
	vignette.material = vm
	layer.add_child(vignette)
	add_child(layer)
	vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


## Fences, lamps, a generator and power lines round the reserve; sandbags
## and fuel drums at the poacher camp. Purely decorative (non-blocking).
const PLAYER_PROPS := [
	["sign", Vector2i(18, 53)], ["generator", Vector2i(11, 52)], ["lamp", Vector2i(16, 52)], ["lamp", Vector2i(12, 46)],
	["lamp", Vector2i(21, 48)], ["fence_b", Vector2i(8, 46)], ["fence_b", Vector2i(8, 47)], ["fence_b", Vector2i(8, 48)],
	["fence_a", Vector2i(10, 55)], ["fence_a", Vector2i(11, 55)], ["fence_a", Vector2i(12, 55)],
]
const POACHER_PROPS := [
	["sandbags", Vector2i(46, 12)], ["sandbags", Vector2i(47, 18)], ["sandbags", Vector2i(53, 16)],
	["fuel_drums", Vector2i(52, 11)], ["fuel_drums", Vector2i(46, 15)],
]
const POLE_TILES := [Vector2i(16, 47), Vector2i(20, 50)]


func _spawn_base_props() -> void:
	for entry in PLAYER_PROPS + POACHER_PROPS:
		var t: Vector2i = entry[1]
		if not map.is_walkable(t):
			continue
		var prop := _prop(entry[0], Iso.tile_to_world(t))
		if entry[0] == "lamp":
			lamps.append(prop)
	for t in POLE_TILES:
		if map.is_walkable(t):
			poles.append(_prop("power_pole", Iso.tile_to_world(t)))
	power_lines = Node2D.new()
	power_lines.name = "PowerLines"
	power_lines.z_index = 24
	power_lines.draw.connect(_draw_power_lines)
	add_child(power_lines)
	var timer := Timer.new()
	timer.wait_time = 1.0
	timer.autostart = true
	timer.timeout.connect(power_lines.queue_redraw)
	add_child(timer)


func _prop(id: String, pos: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	var tex: Texture2D = load("res://assets/sprites/props/%s.png" % id)
	s.texture = tex
	s.position = pos
	s.offset = Vector2(0, -tex.get_height() / 2.0 + 4.0)
	entities.add_child(s)
	return s


## Sagging cables: ranger station -> poles -> hatchery (while they stand).
func _draw_power_lines() -> void:
	var pts: Array = []
	var station = find_building("player", "ranger_station")
	if station != null and station.built:
		pts.append(station.position + Vector2(-10, -78))
	for p in poles:
		pts.append(p.position + Vector2(0, -62))
	var hatch = find_building("player", "hatchery")
	if hatch != null and hatch.built:
		pts.append(hatch.position + Vector2(40, -40))
	for i in range(pts.size() - 1):
		_cable(pts[i], pts[i + 1], Vector2(0, 0))
		_cable(pts[i] + Vector2(-8, 2), pts[i + 1] + Vector2(-8, 2), Vector2(0, 0))


func _cable(a: Vector2, b: Vector2, _off: Vector2) -> void:
	var prev := a
	var sag := a.distance_to(b) * 0.08
	for k in range(1, 13):
		var t := k / 12.0
		var p := a.lerp(b, t) + Vector2(0, sin(t * PI) * sag)
		power_lines.draw_line(prev.round(), p.round(), Color(0.08, 0.07, 0.06), 1.0)
		prev = p


func spawn_corpse(u) -> void:
	var c = CorpseScript.new()
	c.setup(u)
	entities.add_child(c)


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------
func spawn_unit(id: String, faction: String, pos: Vector2):
	var u = UnitScript.new()
	u.setup(id, faction, pos, self)
	spawn_count[faction] = int(spawn_count.get(faction, 0)) + 1
	entities.add_child(u)
	return u


func spawn_building(id: String, faction: String, origin: Vector2i, complete: bool = true):
	var b = BuildingScript.new()
	b.setup(id, faction, origin, self, complete)
	entities.add_child(b)
	return b


func spawn_resource(id: String, t: Vector2i):
	var r = ResourceScript.new()
	r.setup(id, map.nearest_walkable(t), self)
	entities.add_child(r)
	return r


func spawn_projectile(from_ent, to_ent, kind: String, dmg: float, from_pos = null) -> void:
	if to_ent == null or not is_instance_valid(to_ent):
		return
	var p = ProjectileScript.new()
	var start: Vector2 = from_pos if from_pos != null else from_ent.position + Vector2(0, -12)
	p.setup(self, from_ent, to_ent, kind, dmg, start)
	projectiles.add_child(p)


func spawn_fx(kind: String, pos: Vector2, color: Color = Color.WHITE, size: float = 1.0) -> void:
	var f = FxScript.new()
	f.setup(kind, pos, color, size)
	projectiles.add_child(f)


## Flat ground mark (blood / oil / scorch); the oldest are recycled past a cap.
func spawn_decal(kind: String, pos: Vector2, size: float = 1.0) -> void:
	decals = decals.filter(func(d): return is_instance_valid(d))
	while decals.size() >= MAX_DECALS:
		var old = decals.pop_front()
		old.queue_free()
	var d = DecalScript.new()
	d.setup(kind, pos, size)
	ground_decor.add_child(d)
	decals.append(d)


func is_on_screen(pos: Vector2, margin: float = 100.0) -> bool:
	return camera != null and view_rect().grow(margin).has_point(pos)


## Rubble left where a building stood; it smoulders for a while.
func spawn_rubble(b) -> void:
	var id := "rubble_%d%s" % [b.size, "_dark" if b.faction == "poacher" else ""]
	var s := Sprite2D.new()
	var tex: Texture2D = load("res://assets/sprites/rubble/%s.png" % id)
	s.texture = tex
	s.centered = false
	s.offset = Vector2(-tex.get_width() / 2.0, -(tex.get_height() - b.size * 16.0))
	s.position = b.position
	s.z_index = -1
	s.add_to_group("rubble")
	ground_decor.add_child(s)
	var smoke = DamageFxScript.new()
	smoke.setup_rubble(self, b.size, 15.0)
	s.add_child(smoke)
	spawn_decal("scorch", b.position, b.size * 1.6)


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------
func apply_hit(attacker, target, dmg: float, kind: String) -> void:
	if target == null or not is_instance_valid(target) or target.dead:
		return
	var src = attacker if (attacker != null and is_instance_valid(attacker) and not attacker.dead) else null
	var was_alive: bool = not target.dead
	var target_faction: String = target.faction
	var target_unit: bool = target.kind_tag == "unit"
	var fx_pos: Vector2 = target.position + Vector2(0, -10)
	if target_faction == "player" or (src != null and src.faction == "player") or is_on_screen(fx_pos, 0.0):
		Audio.combat_ping()
	if not target_unit:
		play_sfx("impact_wood", fx_pos, -8.0)
	elif kind == "bullet" and randf() < 0.35:
		play_sfx("impact_flesh", fx_pos, -12.0)
	target.take_damage(dmg, src)
	if was_alive and target.dead and src != null:
		if src.faction == "player" and target_faction == "poacher":
			GameState.stats["killed"] += 1
			var key := "killed_" + String(target.def_id)
			GameState.stats[key] = int(GameState.stats.get(key, 0)) + 1
		if target_faction == "player" and target_unit:
			GameState.stats["lost"] += 1
	if not target.dead and target_unit:
		match kind:
			"venom":
				target.apply_slow(3.0)
			"net":
				if target.is_dino():
					target.apply_stun(2.2)
	match kind:
		"venom":
			spawn_fx("splat", fx_pos)
		"bullet":
			spawn_fx("spark", fx_pos)
	if not target_unit:
		spawn_fx("debris", fx_pos + Vector2(randf_range(-20, 20), -10), Color(0.5, 0.36, 0.22))
	elif kind != "net" and kind != "venom" and randf() < 0.45:
		var mark := "oil" if target.data.get("kind", "") == "vehicle" else "blood"
		spawn_decal(mark, target.position + Vector2(randf_range(-8, 8), randf_range(-3, 3)), 0.6 + target.radius / 30.0)


## Should `a` attack `b` on its own initiative?
func is_auto_hostile(a, b) -> bool:
	if b.dead or a.faction == b.faction or b.kind_tag == "resource":
		return false
	if a.faction == "wild":
		return true
	if b.faction == "wild":
		return false
	return true


## Nearest entity `a` would attack on its own within `rng` (units first).
func find_enemy(a, rng: float):
	var best = null
	var best_d := rng
	for o in units_near(a.position, rng):
		if o == a or not is_auto_hostile(a, o):
			continue
		if a.faction == "player" and not o.visible:
			continue
		var d: float = Iso.idist(a.position, o.position) - o.radius
		if d < best_d:
			best_d = d
			best = o
	if best != null:
		return best
	for b in get_tree().get_nodes_in_group("buildings"):
		if not is_auto_hostile(a, b):
			continue
		if a.faction == "player" and not b.visible:
			continue
		var d: float = Iso.idist(a.position, b.position) - b.radius
		if d < best_d:
			best_d = d
			best = b
	return best


func _physics_process(delta: float) -> void:
	alert_cd -= delta
	grid_hash.clear()
	for u in get_tree().get_nodes_in_group("units"):
		if u.dead:
			continue
		var k := Vector2i(floori(u.position.x / HASH_CELL), floori(u.position.y / HASH_CELL))
		if grid_hash.has(k):
			grid_hash[k].append(u)
		else:
			grid_hash[k] = [u]


func units_near(pos: Vector2, r: float) -> Array:
	var out: Array = []
	var cells := int(ceil(r / HASH_CELL))
	var c := Vector2i(floori(pos.x / HASH_CELL), floori(pos.y / HASH_CELL))
	for dy in range(-cells, cells + 1):
		for dx in range(-cells, cells + 1):
			var k := c + Vector2i(dx, dy)
			if grid_hash.has(k):
				out.append_array(grid_hash[k])
	return out


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
func entity_at(pos: Vector2):
	var best = null
	var best_d := 1e9
	for u in get_tree().get_nodes_in_group("units"):
		if u.dead or not u.visible:
			continue
		var d: float = pos.distance_to(u.position + Vector2(0, -u.pick_h))
		if d < maxf(u.radius * 1.6, 14.0) and d < best_d:
			best_d = d
			best = u
	if best != null:
		return best
	for r in get_tree().get_nodes_in_group("resources"):
		if r.visible and pos.distance_to(r.position + Vector2(0, -10)) < 22.0:
			return r
	for b in get_tree().get_nodes_in_group("buildings"):
		if not b.dead and b.visible and b.hit_test(pos):
			return b
	return null


func near_feeder(u) -> bool:
	for b in get_tree().get_nodes_in_group("buildings"):
		if b.def_id == "hatchery" and b.built and not b.dead and b.faction == u.faction:
			if Iso.idist(u.position, b.position) < float(b.data["feeder"]):
				return true
	return false


func nearest_dropoff(faction: String, pos: Vector2):
	var best = null
	var best_d := 1e9
	for b in get_tree().get_nodes_in_group("buildings"):
		if b.dead or not b.built or b.faction != faction or not b.data.get("dropoff", false):
			continue
		var d: float = Iso.idist(pos, b.position)
		if d < best_d:
			best_d = d
			best = b
	return best


func nearest_building(faction: String, id: String, pos: Vector2):
	var best = null
	var best_d := 1e9
	for b in get_tree().get_nodes_in_group("buildings"):
		if b.dead or b.faction != faction or b.def_id != id:
			continue
		var d: float = Iso.idist(pos, b.position)
		if d < best_d:
			best_d = d
			best = b
	return best


func find_building(faction: String, id: String):
	for b in get_tree().get_nodes_in_group("buildings"):
		if not b.dead and b.faction == faction and b.def_id == id:
			return b
	return null


func nearest_resource(pos: Vector2, res_type: String, max_d: float):
	var best = null
	var best_d := max_d
	for r in get_tree().get_nodes_in_group("resources"):
		if r.dead or r.res_type != res_type:
			continue
		var d: float = Iso.idist(pos, r.position)
		if d < best_d:
			best_d = d
			best = r
	return best


func units_of(faction: String) -> Array:
	var out: Array = []
	for e in get_tree().get_nodes_in_group("faction_" + faction):
		if e.kind_tag == "unit" and not e.dead:
			out.append(e)
	return out


func count_units(faction: String) -> int:
	return units_of(faction).size()


func can_place(id: String, origin: Vector2i) -> bool:
	var s: int = Defs.BUILDINGS[id]["size"]
	for y in s:
		for x in s:
			var t := origin + Vector2i(x, y)
			if not map.is_walkable(t) or not fog.tile_explored(t):
				return false
	# Don't build on top of units.
	var center: Vector2 = Iso.tile_to_world(Vector2(origin.x + (s - 1) / 2.0, origin.y + (s - 1) / 2.0))
	for u in units_near(center, s * 40.0):
		var g: Vector2 = Iso.world_to_grid(u.position)
		if g.x > origin.x - 0.6 and g.y > origin.y - 0.6 and g.x < origin.x + s - 0.4 and g.y < origin.y + s - 0.4:
			return false
	return true


## Production speed multiplier (the AI gets a handicap or bonus).
func build_speed(faction: String) -> float:
	if faction == "poacher":
		return [0.75, 1.0, 1.25][GameState.difficulty]
	return 1.0


func income_mult(faction: String) -> float:
	if faction == "poacher":
		return [0.6, 1.0, 1.5][GameState.difficulty] * float(mission.get("ai", {}).get("income", 1.0))
	return 1.0


func view_rect() -> Rect2:
	var sz: Vector2 = get_viewport().get_visible_rect().size / camera.zoom
	return Rect2(camera.position - sz / 2.0, sz)


func focus_home() -> void:
	var b = find_building("player", "ranger_station")
	if b == null:
		b = find_building("player", "hatchery")
	camera.focus_on(b.position if b != null else Iso.tile_to_world(PLAYER_BASE))


func alert_attack(pos: Vector2) -> void:
	if alert_cd > 0.0:
		return
	alert_cd = 12.0
	if not view_rect().grow(-40.0).has_point(pos):
		GameState.notify("Your reserve is under attack!")
		play_ui("alert")
		if hud != null:
			hud.ping_minimap(pos)


# ---------------------------------------------------------------------------
# Deaths & game end
# ---------------------------------------------------------------------------
func on_entity_died(e) -> void:
	if selection != null:
		selection.forget(e)
	if e.kind_tag == "building" and e.def_id == "egg_cage":
		# freed eggs hatch on the spot and join the reserve
		for i in 2:
			var u = spawn_unit("raptor", "player", free_spot(Iso.world_to_tile(e.position)))
			spawn_fx("hearts", u.position + Vector2(0, -16))
		GameState.stats["rescued"] = int(GameState.stats.get("rescued", 0)) + 2
		GameState.notify("Eggs rescued! Two hatchlings have joined the reserve.")
		play_sfx("hatch", e.position)
		play_sfx("raptor_call", e.position, -6.0, 1.4)
	if e.kind_tag == "building":
		_check_end()


## Losing the reserve ends the game; victory is decided by the mission's objectives.
func _check_end() -> void:
	if GameState.over:
		return
	if find_building("player", "ranger_station") == null and find_building("player", "hatchery") == null:
		GameState.end_game(false)


func _on_game_over(victory: bool) -> void:
	var idx := MissionsScript.index_of(GameState.mission_id)
	if victory and idx >= 0:
		SaveSystem.mark_completed(GameState.mission_id, idx, MissionsScript.CAMPAIGN.size())
	Audio.stinger("victory" if victory else "defeat")
	if hud != null:
		hud.show_end(victory)


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
func _setup_audio() -> void:
	Audio.attach_world(self)
	tree_exiting.connect(func(): Audio.detach_world(self))


func play_sfx(sound: String, pos: Vector2, db: float = 0.0, pitch: float = 1.0) -> void:
	Audio.play(sound, pos, db, pitch)


func play_ui(sound: String) -> void:
	Audio.ui(sound, -4.0)
