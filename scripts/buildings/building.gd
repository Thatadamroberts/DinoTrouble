extends Node2D
## A building: HQ, hatchery, tower, depot or poacher camp.
## Handles construction, production queues, income and tower attacks.

const HpBar = preload("res://scripts/game/hp_bar.gd")
const DamageFx = preload("res://scripts/buildings/damage_fx.gd")
const QUEUE_MAX := 5

var kind_tag := "building"
var def_id := ""
var data: Dictionary = {}
var faction := "player"
var hp := 1.0
var max_hp := 1.0
var radius := 40.0
var size := 2
var origin := Vector2i.ZERO
var dead := false
var selected := false

var built := true
var progress := 1.0
var queue: Array = []
var queue_t := 0.0
var rally := Vector2.ZERO
var has_rally := false
var attack_cd := 0.0
var scan_t := 0.0
var target = null
var pop_warned := false

var sprite: Sprite2D
var bar: Node2D
var damage_fx: Node2D
var world = null
var map = null


func setup(id: String, fac: String, origin_tile: Vector2i, w, complete: bool = true) -> void:
	def_id = id
	data = Defs.BUILDINGS[id]
	faction = fac
	world = w
	map = w.map
	size = int(data["size"])
	origin = origin_tile
	max_hp = float(data["hp"])
	hp = max_hp
	radius = size * 22.6
	position = Iso.tile_to_world(Vector2(origin.x + (size - 1) / 2.0, origin.y + (size - 1) / 2.0))

	sprite = Sprite2D.new()
	sprite.texture = Defs.building_texture(id)
	sprite.centered = false
	var tw: float = sprite.texture.get_width()
	var th: float = sprite.texture.get_height()
	sprite.offset = Vector2(-tw / 2.0, -(th - size * 16.0))
	add_child(sprite)

	bar = HpBar.new()
	bar.ent = self
	bar.width = size * 20.0
	bar.position = Vector2(0, -(th - size * 16.0) - 6.0)
	add_child(bar)

	damage_fx = DamageFx.new()
	add_child(damage_fx)
	damage_fx.setup_building(self)

	if not complete:
		built = false
		progress = 0.0
		hp = max_hp * 0.1
		sprite.modulate = Color(1, 1, 1, 0.4)

	map.set_footprint(origin, size, true)
	add_to_group("buildings")
	add_to_group("entities")
	add_to_group("faction_" + faction)


func display_name() -> String:
	return data["name"]


func set_selected(value: bool) -> void:
	selected = value
	queue_redraw()


## Rough click test against the sprite's bounding box.
func hit_test(p: Vector2) -> bool:
	var r := Rect2(sprite.offset, sprite.texture.get_size())
	r = r.grow_individual(-8, -6, -8, -4)
	return r.has_point(p - position)


func trains() -> Array:
	return data.get("trains", [])


func queue_progress() -> float:
	if queue.is_empty():
		return 0.0
	return clampf(queue_t / float(Defs.UNITS[queue[0]]["time"]), 0.0, 1.0)


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------
func train(id: String) -> bool:
	if dead or not built or not trains().has(id):
		return false
	if queue.size() >= QUEUE_MAX:
		if faction == "player":
			GameState.notify("Production queue is full.")
		return false
	if not GameState.spend(faction, Defs.UNITS[id]["cost"]):
		return false
	queue.append(id)
	return true


func cancel_last() -> void:
	if queue.is_empty():
		return
	var id: String = queue.pop_back()
	if queue.is_empty():
		queue_t = 0.0
	GameState.refund(faction, Defs.UNITS[id]["cost"])


func _update_production(delta: float) -> void:
	if queue.is_empty():
		return
	var id: String = queue[0]
	var need := float(Defs.UNITS[id]["time"])
	queue_t = minf(queue_t + delta * world.build_speed(faction), need)
	if queue_t < need:
		return
	if world.count_units(faction) >= Defs.POP_CAP:
		if faction == "player" and not pop_warned:
			pop_warned = true
			GameState.notify("Population limit reached (%d)." % Defs.POP_CAP)
		return
	pop_warned = false
	queue.pop_front()
	queue_t = 0.0
	var u = world.spawn_unit(id, faction, spawn_point())
	if Defs.UNITS[id]["kind"] == "dino":
		world.play_sfx("hatch", position)
		u._call(-6.0)
		world.spawn_fx("hearts", u.position + Vector2(0, -16))
		if faction == "player":
			GameState.stats["hatched"] += 1
	if has_rally:
		u.cmd_move(rally)
	elif u.can_gather() and faction == "player":
		var node = world.nearest_resource(u.position, "dna", 600.0)
		if node != null:
			u.cmd_gather(node)


## A free spot just outside the front corner of the footprint.
func spawn_point() -> Vector2:
	var front := Vector2i(origin.x + size, origin.y + size)
	var t: Vector2i = map.nearest_walkable(front)
	return Iso.tile_to_world(t) + Vector2(randf_range(-8, 8), randf_range(-4, 4))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
func add_build_progress(delta: float) -> void:
	if built:
		return
	var step := delta / float(data["time"])
	progress = minf(1.0, progress + step)
	hp = minf(max_hp, hp + max_hp * 0.9 * step)
	sprite.modulate = Color(1, 1, 1, 0.4 + 0.6 * progress)
	if progress >= 1.0:
		built = true
		sprite.modulate = Color.WHITE
		queue_redraw()
		if faction == "player":
			GameState.notify("%s complete." % data["name"])
			Audio.ui("ui_confirm", -6.0)
			var key := "built_" + def_id
			GameState.stats[key] = int(GameState.stats.get(key, 0)) + 1


func repair(delta: float) -> void:
	hp = minf(max_hp, hp + max_hp * 0.03 * delta)


# ---------------------------------------------------------------------------
# Damage
# ---------------------------------------------------------------------------
func take_damage(amount: float, _source) -> void:
	if dead:
		return
	hp -= amount
	if faction == "player":
		world.alert_attack(position)
	if hp <= 0.0:
		die()


func die() -> void:
	if dead:
		return
	dead = true
	hp = 0.0
	remove_from_group("buildings")
	remove_from_group("entities")
	remove_from_group("faction_" + faction)
	map.set_footprint(origin, size, false)
	world.spawn_fx("collapse", position)
	world.spawn_rubble(self)
	world.play_sfx("collapse", position)
	world.on_entity_died(self)
	queue_free()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
func _physics_process(delta: float) -> void:
	if dead or not built or world == null:
		return
	var income: float = data.get("income", 0.0)
	if income > 0.0:
		GameState.add(faction, "supplies", income * delta * world.income_mult(faction))
	_update_production(delta)
	if data.has("attack"):
		_update_attack(delta)


func _update_attack(delta: float) -> void:
	attack_cd -= delta
	scan_t -= delta
	var atk: Dictionary = data["attack"]
	var rng: float = atk["range"]
	if target == null or not is_instance_valid(target) or target.dead or Iso.idist(position, target.position) - target.radius > rng:
		target = null
		if scan_t <= 0.0:
			scan_t = 0.4
			target = world.find_enemy(self, rng)
	if target != null and attack_cd <= 0.0:
		attack_cd = float(atk["cooldown"])
		var from := position + Vector2(0, -60)
		world.spawn_projectile(self, target, "bullet", float(atk["damage"]), from)
		if world.is_on_screen(from):
			world.spawn_fx("flash", from + Vector2(signf(target.position.x - position.x) * 6.0, 0), Color(1.0, 0.85, 0.5), 0.8)
		world.play_sfx("tower_shot", position, -6.0)


func _draw() -> void:
	var hw := size * 32.0
	var hh := size * 16.0
	var pts := PackedVector2Array([Vector2(-hw, 0), Vector2(0, hh), Vector2(hw, 0), Vector2(0, -hh), Vector2(-hw, 0)])
	if not built:
		draw_colored_polygon(PackedVector2Array([Vector2(-hw, 0), Vector2(0, hh), Vector2(hw, 0), Vector2(0, -hh)]), Color(0.45, 0.35, 0.2, 0.5))
		for i in range(1, size * 2):
			var f := float(i) / (size * 2)
			draw_line(Vector2(-hw, 0).lerp(Vector2(0, -hh), f), Vector2(0, hh).lerp(Vector2(hw, 0), f), Color(0.8, 0.65, 0.3, 0.6), 1.0)
	if selected:
		var col: Color = Defs.faction_color(faction)
		draw_polyline(pts, col, 2.0)
		if data.has("feeder") and faction == "player":
			_ellipse(float(data["feeder"]), Color(1.0, 0.65, 0.2, 0.5))
		if data.has("attack"):
			_ellipse(float(data["attack"]["range"]), Color(col, 0.35))


func _ellipse(r: float, c: Color) -> void:
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
	draw_arc(Vector2.ZERO, r, 0.0, TAU, 64, c, 2.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
