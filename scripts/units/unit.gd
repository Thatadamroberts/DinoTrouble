extends Node2D
## A mobile unit: human, vehicle or dinosaur. Driven by a small state machine.

enum S { IDLE, MOVE, ATTACK_MOVE, ATTACK, GATHER, RETURN, BUILD, TAME, FLEE, FEED }

const HpBar = preload("res://scripts/game/hp_bar.gd")
const STATE_NAMES := ["Idle", "Moving", "Attack-moving", "Attacking", "Gathering", "Returning cargo", "Building", "Taming", "Fleeing", "Starving: heading to feed"]
const SCAN_INTERVAL := 0.4
const GATHER_TIME := 1.6
const CARRY_AMOUNT := 10
const WILD_LEASH := 420.0

var kind_tag := "unit"
var def_id := ""
var data: Dictionary = {}
var faction := "player"
var hp := 1.0
var max_hp := 1.0
var radius := 8.0
var dead := false
var selected := false

var state: int = S.IDLE
var target = null  # entity being attacked / built / tamed
var am_active := false  # true when an attack-move should resume after a fight
var move_goal := Vector2.ZERO
var path := PackedVector2Array()
var path_i := 0
var repath_t := 0.0
var scan_t := 0.0
var attack_cd := 0.0
var attack_anim_t := 0.0

var gather_node = null
var drop_target = null
var last_res := "dna"
var carry := 0
var carry_type := ""
var gather_t := 0.0

var slow_t := 0.0
var stun_t := 0.0
var flee_t := 0.0
var flee_from := Vector2.ZERO
var ability_cd := 0.0
var charge_t := 0.0
var hunger := 100.0
var feral := false
var tame_t := 0.0
var tame_needed := 5.0
var home := Vector2.ZERO
var wander_t := 2.0

var sprite: Sprite2D
var bar: Node2D
var pick_h := 10.0
var anim_t := 0.0
var last_frame := -1
var trail_t := 0.0
var breath_phase := randf() * 2.0
var facing_left := false
var facing_back := false
var prev_pos := Vector2.ZERO
var world = null
var map = null


func setup(id: String, fac: String, pos: Vector2, w) -> void:
	def_id = id
	data = Defs.UNITS[id]
	faction = fac
	world = w
	map = w.map
	max_hp = float(data["hp"])
	hp = max_hp
	radius = float(data.get("radius", 8.0))
	position = pos
	prev_pos = pos
	home = pos
	wander_t = randf_range(1.0, 5.0)

	sprite = Sprite2D.new()
	sprite.texture = Defs.unit_texture(id)
	sprite.hframes = Defs.SHEET_FRAMES
	sprite.vframes = Defs.SHEET_ROWS
	var fh: float = sprite.texture.get_height() / float(Defs.SHEET_ROWS)
	sprite.offset = Vector2(0, -fh / 2.0 + 3.0)
	add_child(sprite)
	pick_h = fh / 2.0 - 3.0

	bar = HpBar.new()
	bar.ent = self
	bar.width = clampf(radius * 2.6, 20.0, 40.0)
	bar.position = Vector2(0, -fh - 2.0)
	add_child(bar)

	add_to_group("units")
	add_to_group("entities")
	add_to_group("faction_" + faction)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
func is_dino() -> bool:
	return data.get("kind", "") == "dino"


func is_idle() -> bool:
	return state == S.IDLE and not feral


func can_gather() -> bool:
	return bool(data.get("gather", false))


func can_build() -> bool:
	return bool(data.get("build", false))


func can_tame() -> bool:
	return bool(data.get("tame", false))


func display_name() -> String:
	var n: String = data["name"]
	if faction == "wild":
		return "Wild " + n
	return n


func state_text() -> String:
	if stun_t > 0.0:
		return "Stunned"
	if feral:
		return STATE_NAMES[S.FEED]
	return STATE_NAMES[state]


func set_selected(value: bool) -> void:
	selected = value
	queue_redraw()


func _valid(e) -> bool:
	return e != null and is_instance_valid(e) and not e.dead


# ---------------------------------------------------------------------------
# Commands (from the player or AI)
# ---------------------------------------------------------------------------
func _obeys() -> bool:
	return not dead and not feral and faction != "wild"


func _reset_orders() -> void:
	target = null
	am_active = false
	gather_t = 0.0
	tame_t = 0.0
	path = PackedVector2Array()
	path_i = 0


func cmd_stop() -> void:
	if not _obeys():
		return
	_reset_orders()
	state = S.IDLE


func cmd_move(pos: Vector2) -> void:
	if not _obeys():
		return
	_reset_orders()
	state = S.MOVE
	move_to(pos)


func cmd_attack_move(pos: Vector2) -> void:
	if not _obeys():
		return
	_reset_orders()
	state = S.ATTACK_MOVE
	am_active = true
	move_to(pos)


func cmd_attack(e) -> void:
	if not _obeys() or not _valid(e) or e == self:
		return
	if float(data["damage"]) <= 0.0:
		return
	_reset_orders()
	target = e
	state = S.ATTACK
	repath_t = 0.0


func cmd_gather(node) -> void:
	if not _obeys() or not can_gather() or not _valid(node):
		return
	_reset_orders()
	gather_node = node
	last_res = node.res_type
	if carry > 0 and carry_type != node.res_type:
		carry = 0
	if carry >= CARRY_AMOUNT:
		state = S.RETURN
		drop_target = null
	else:
		state = S.GATHER
		move_to(node.position)


func cmd_build(b) -> void:
	if not _obeys() or not can_build() or not _valid(b):
		return
	_reset_orders()
	target = b
	state = S.BUILD
	move_to(b.position)


func cmd_tame(dino) -> void:
	if not _obeys() or not can_tame() or not _valid(dino):
		return
	if dino.faction != "wild" or not dino.is_dino():
		return
	if dino.data.get("wild_aggro", false) and dino.hp > dino.max_hp * 0.5:
		if faction == "player":
			GameState.notify("Wound the %s below half health before taming it." % dino.data["name"])
		return
	_reset_orders()
	target = dino
	state = S.TAME
	move_to(dino.position)


# ---------------------------------------------------------------------------
# Damage & effects
# ---------------------------------------------------------------------------
func take_damage(amount: float, source) -> void:
	if dead:
		return
	hp -= amount
	tame_t = 0.0
	if faction == "player":
		world.alert_attack(position)
	if source != null and is_instance_valid(source) and not source.dead and source.faction != faction:
		_retaliate(source)
	if hp <= 0.0:
		die()


func _retaliate(source) -> void:
	if feral or float(data["damage"]) <= 0.0:
		return
	if faction == "wild":
		if state != S.ATTACK or not _valid(target):
			target = source
			state = S.ATTACK
		return
	if state == S.IDLE and bool(data.get("auto_attack", true)):
		target = source
		state = S.ATTACK
		am_active = false


func apply_slow(sec: float) -> void:
	slow_t = maxf(slow_t, sec)


func apply_stun(sec: float) -> void:
	stun_t = maxf(stun_t, sec)


func knockback(v: Vector2) -> void:
	var np := position + v
	if map.is_walkable(Iso.world_to_tile(np)):
		position = np


func scare(from: Vector2, sec: float) -> void:
	if is_dino() or dead:
		return
	flee_from = from
	flee_t = sec
	state = S.FLEE
	target = null
	var away := (position - from).normalized()
	if away == Vector2.ZERO:
		away = Vector2.RIGHT
	move_to(position + away * 160.0)


## Calms a wild dinosaur so it can be tamed (stops fighting for a moment).
func calm() -> void:
	if faction != "wild":
		return
	if bool(data.get("wild_aggro", false)) and hp > max_hp * 0.5:
		return
	target = null
	state = S.IDLE
	path = PackedVector2Array()
	wander_t = 1.5


func convert_to(fac: String) -> void:
	remove_from_group("faction_" + faction)
	faction = fac
	add_to_group("faction_" + faction)
	hunger = 100.0
	feral = false
	target = null
	state = S.IDLE
	path = PackedVector2Array()
	home = position
	queue_redraw()


func die() -> void:
	if dead:
		return
	dead = true
	hp = 0.0
	remove_from_group("units")
	remove_from_group("entities")
	remove_from_group("faction_" + faction)
	world.spawn_fx("puff", position, Color(0.6, 0.5, 0.4) if not is_dino() else Color(0.6, 0.15, 0.1))
	world.spawn_corpse(self)
	match data.get("kind", ""):
		"vehicle":
			world.spawn_decal("scorch", position, 1.4)
			world.spawn_fx("collapse", position)
		"dino":
			world.spawn_decal("blood", position, 0.8 + radius / 15.0)
		_:
			world.spawn_decal("blood", position, 0.8)
	world.on_entity_died(self)
	queue_free()


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------
func move_to(goal: Vector2) -> void:
	move_goal = goal
	path = map.find_path(position, goal)
	path_i = 0


func path_done() -> bool:
	return path_i >= path.size()


func speed() -> float:
	var s: float = data["speed"]
	if slow_t > 0.0:
		s *= 0.5
	if charge_t > 0.0:
		s *= 2.6
	if map.is_jungle(Iso.world_to_tile(position)):
		s *= 0.6 if data.get("kind", "") == "vehicle" else 0.85
	return s


## Moves toward p. Speed is measured along the ground plane so vertical
## (screen) movement is slower, as it covers more ground.
func _step_toward(p: Vector2, delta: float) -> bool:
	var to := p - position
	if to.length() < 0.5:
		return true
	var dir := to.normalized()
	var ground := Vector2(dir.x, dir.y * 2.0).length()
	var step := speed() * delta / maxf(ground, 0.001)
	if to.length() <= step:
		position = p
		return true
	position += dir * step
	return false


func _step_path(delta: float) -> bool:
	if path_i >= path.size():
		return true
	if _step_toward(path[path_i], delta):
		path_i += 1
	return path_i >= path.size()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
func _physics_process(delta: float) -> void:
	if dead or world == null:
		return
	attack_cd -= delta
	attack_anim_t -= delta
	ability_cd -= delta
	slow_t -= delta
	charge_t -= delta
	scan_t -= delta
	repath_t -= delta

	if is_dino() and faction == "player":
		_update_hunger(delta)

	if stun_t > 0.0:
		stun_t -= delta
		_animate(delta)
		return

	match state:
		S.IDLE:
			_do_idle(delta)
		S.MOVE:
			if _step_path(delta):
				state = S.IDLE
		S.ATTACK_MOVE:
			_do_attack_move(delta)
		S.ATTACK:
			_do_attack(delta)
		S.GATHER:
			_do_gather(delta)
		S.RETURN:
			_do_return(delta)
		S.BUILD:
			_do_build(delta)
		S.TAME:
			_do_tame(delta)
		S.FLEE:
			flee_t -= delta
			if _step_path(delta) or flee_t <= 0.0:
				state = S.IDLE
		S.FEED:
			_do_feed(delta)

	_separate(delta)
	_animate(delta)


func _update_hunger(delta: float) -> void:
	if not GameState.hunger_enabled:
		hunger = 100.0
		feral = false
		return
	hunger = maxf(0.0, hunger - float(data.get("hunger_rate", 0.5)) * delta)
	if world.near_feeder(self):
		hunger = minf(100.0, hunger + 25.0 * delta)
	if not feral and hunger <= 0.0:
		feral = true
		_reset_orders()
		state = S.FEED
		GameState.notify("A starving %s has gone feral! It is heading for the hatchery." % data["name"])
	elif feral and hunger >= 70.0:
		feral = false
		state = S.IDLE


func _scan(range_px: float):
	return world.find_enemy(self, range_px)


func _sight_px() -> float:
	return float(data["sight"]) * Iso.TILE_DIST


func _do_idle(delta: float) -> void:
	if not map.is_walkable(Iso.world_to_tile(position)):
		var t: Vector2i = map.nearest_walkable(Iso.world_to_tile(position))
		_step_toward(Iso.tile_to_world(t), delta)
		return
	if faction == "wild":
		_wild_idle(delta)
		return
	if scan_t <= 0.0:
		scan_t = SCAN_INTERVAL
		if bool(data.get("auto_attack", true)) and float(data["damage"]) > 0.0:
			var e = _scan(_sight_px())
			if e != null:
				target = e
				state = S.ATTACK
				am_active = false


func _wild_idle(delta: float) -> void:
	if scan_t <= 0.0:
		scan_t = SCAN_INTERVAL
		if bool(data.get("wild_aggro", false)):
			var e = _scan(_sight_px() * 0.6)
			if e != null and Iso.idist(home, e.position) < WILD_LEASH * 0.6:
				target = e
				state = S.ATTACK
				return
	wander_t -= delta
	if wander_t <= 0.0:
		wander_t = randf_range(4.0, 9.0)
		var off := Vector2(randf_range(-90.0, 90.0), randf_range(-45.0, 45.0))
		state = S.MOVE
		move_to(home + off)


func _do_attack_move(delta: float) -> void:
	if scan_t <= 0.0:
		scan_t = SCAN_INTERVAL
		var e = _scan(_sight_px())
		if e != null:
			target = e
			state = S.ATTACK
			return
	if _step_path(delta):
		am_active = false
		state = S.IDLE


func _end_attack() -> void:
	target = null
	charge_t = 0.0
	scan_t = 0.0
	if am_active:
		state = S.ATTACK_MOVE
		move_to(move_goal)
	elif faction == "wild":
		state = S.MOVE
		move_to(home)
	else:
		state = S.IDLE


func _do_attack(delta: float) -> void:
	if not _valid(target) or target.faction == faction:
		_end_attack()
		return
	if faction == "wild" and Iso.idist(position, home) > WILD_LEASH:
		_end_attack()
		return
	# Units hidden by fog can't be chased forever by the player.
	if faction == "player" and not target.visible:
		_end_attack()
		return
	var d: float = Iso.idist(position, target.position) - target.radius
	var rng: float = data["range"]
	var ability: String = data.get("ability", "")

	if ability == "roar" and ability_cd <= 0.0 and d < 200.0:
		_roar()

	if d <= rng + (6.0 if charge_t > 0.0 else 0.0):
		path = PackedVector2Array()
		path_i = 0
		_face(target.position)
		if charge_t > 0.0:
			_charge_hit()
		if attack_cd <= 0.0:
			_attack()
		return

	if ability == "charge" and ability_cd <= 0.0 and d > 60.0 and d < 240.0:
		charge_t = 1.2
		ability_cd = 10.0
		world.play_sfx("roar", position, -10.0, 1.6)
	if d < 110.0 and map.line_clear(position, target.position):
		_step_toward(target.position, delta)
	elif path_done() and d < rng + 70.0:
		# Path ended just short (e.g. next to a building): close the gap directly.
		_step_toward(target.position, delta)
	else:
		if repath_t <= 0.0 or path_done():
			repath_t = 0.6
			move_to(target.position)
		_step_path(delta)


func _attack() -> void:
	attack_cd = float(data["cooldown"])
	attack_anim_t = 0.3
	var dmg: float = data["damage"]
	var proj: String = data.get("projectile", "")
	if proj != "":
		world.spawn_projectile(self, target, proj, dmg)
		if world.is_on_screen(position):
			var fw: float = sprite.texture.get_width() / float(Defs.SHEET_FRAMES)
			var muzzle := position + Vector2((-1.0 if facing_left else 1.0) * fw * 0.42, -pick_h * 1.1)
			match proj:
				"bullet":
					world.spawn_fx("flash", muzzle, Color(1.0, 0.85, 0.5), 0.7 if data.get("kind", "") == "human" else 0.9)
				"venom":
					world.spawn_fx("flash", muzzle, Color(0.5, 1.0, 0.35), 0.5)
		match proj:
			"venom":
				world.play_sfx("spit", position)
			"net":
				world.play_sfx("net", position)
			_:
				world.play_sfx("shot", position, -6.0)
		return
	var tpos: Vector2 = target.position
	world.apply_hit(self, target, dmg, "melee")
	world.play_sfx("bite", position, -4.0)
	var splash: float = data.get("splash", 0.0)
	if splash > 0.0:
		for o in world.units_near(tpos, splash):
			if o == target or o.dead or o.faction == faction:
				continue
			if Iso.idist(tpos, o.position) <= splash:
				world.apply_hit(self, o, dmg * 0.5, "melee")


func _charge_hit() -> void:
	charge_t = 0.0
	if not _valid(target):
		return
	world.apply_hit(self, target, float(data["damage"]) * 1.5, "melee")
	if _valid(target) and target.kind_tag == "unit":
		var dir: Vector2 = (target.position - position).normalized()
		target.knockback(dir * 30.0)
		target.apply_stun(0.8)
	world.spawn_fx("dust", position)
	attack_cd = float(data["cooldown"])
	attack_anim_t = 0.3


func _roar() -> void:
	ability_cd = 18.0
	world.spawn_fx("roar", position + Vector2(0, -20))
	world.play_sfx("roar", position)
	for o in world.units_near(position, 200.0):
		if o.dead or o.faction == faction or o.faction == "wild":
			continue
		if Iso.idist(position, o.position) <= 200.0:
			o.scare(position, 2.5)


func _arrived_at(e, reach: float) -> bool:
	var d: float = Iso.idist(position, e.position) - e.radius
	return d <= reach or (path_done() and d <= reach + 45.0)


func _approach(e, delta: float) -> void:
	if path_done():
		if repath_t <= 0.0:
			repath_t = 1.0
			move_to(e.position)
	_step_path(delta)


func _do_gather(delta: float) -> void:
	if not _valid(gather_node):
		gather_node = world.nearest_resource(position, last_res, 700.0)
		if gather_node == null:
			if carry > 0:
				state = S.RETURN
				drop_target = null
			else:
				state = S.IDLE
			return
		move_to(gather_node.position)
	if _arrived_at(gather_node, 40.0):
		gather_t += delta
		if fmod(gather_t, 0.5) < delta:
			attack_anim_t = 0.25
		_face(gather_node.position)
		if gather_t >= GATHER_TIME:
			gather_t = 0.0
			var got: int = gather_node.take(CARRY_AMOUNT)
			if got > 0:
				carry = got
				carry_type = gather_node.res_type
				last_res = carry_type
			state = S.RETURN
			drop_target = null
	else:
		_approach(gather_node, delta)


func _do_return(delta: float) -> void:
	if carry <= 0:
		state = S.GATHER
		return
	if not _valid(drop_target):
		drop_target = world.nearest_dropoff(faction, position)
		if drop_target == null:
			state = S.IDLE
			return
		move_to(drop_target.position)
	if _arrived_at(drop_target, 30.0):
		GameState.add(faction, carry_type, carry)
		carry = 0
		drop_target = null
		state = S.GATHER
		if _valid(gather_node):
			move_to(gather_node.position)
	else:
		_approach(drop_target, delta)


func _do_build(delta: float) -> void:
	if not _valid(target) or target.kind_tag != "building" or target.faction != faction:
		_reset_orders()
		state = S.IDLE
		return
	if target.built and target.hp >= target.max_hp:
		_reset_orders()
		state = S.IDLE
		return
	if _arrived_at(target, 30.0):
		_face(target.position)
		if fmod(GameState.elapsed, 0.6) < delta:
			attack_anim_t = 0.25
			world.play_sfx("build", position, -14.0)
		if not target.built:
			target.add_build_progress(delta)
		else:
			target.repair(delta)
	else:
		_approach(target, delta)


func _do_tame(delta: float) -> void:
	if not _valid(target) or target.faction != "wild":
		_reset_orders()
		state = S.IDLE
		return
	var d: float = Iso.idist(position, target.position) - target.radius
	if d <= 40.0:
		target.calm()
		_face(target.position)
		tame_t += delta
		if tame_t >= tame_needed:
			target.convert_to(faction)
			if faction == "player":
				GameState.stats["tamed"] += 1
				GameState.notify("%s tamed! It has joined your reserve." % target.data["name"])
			world.play_sfx("hatch", position)
			world.spawn_fx("hearts", target.position + Vector2(0, -20))
			_reset_orders()
			state = S.IDLE
	else:
		if d < 110.0 and map.line_clear(position, target.position):
			_step_toward(target.position, delta)
		else:
			_approach(target, delta)


func _do_feed(delta: float) -> void:
	var h = world.nearest_building(faction, "hatchery", position)
	if h == null:
		GameState.notify("A starving %s escaped into the jungle!" % data["name"])
		convert_to("wild")
		return
	if Iso.idist(position, h.position) > float(h.data["feeder"]) * 0.6:
		_approach(h, delta)


func _face(p: Vector2) -> void:
	if absf(p.x - position.x) > 1.0:
		facing_left = p.x < position.x
	if absf(p.y - position.y) > 2.0:
		facing_back = p.y < position.y


func _separate(delta: float) -> void:
	var push := Vector2.ZERO
	for o in world.units_near(position, radius + 20.0):
		if o == self or o.dead:
			continue
		var dv: Vector2 = position - o.position
		var min_d: float = radius + o.radius
		var dist := dv.length()
		if dist < min_d:
			if dist < 0.01:
				dv = Vector2(randf_range(-1, 1), randf_range(-1, 1))
				dist = 1.0
			push += dv / dist * (min_d - dist)
	if push != Vector2.ZERO:
		var np := position + push * clampf(delta * 6.0, 0.0, 0.5)
		if map.is_walkable(Iso.world_to_tile(np)):
			position = np


func _animate(delta: float) -> void:
	var moved := position - prev_pos
	prev_pos = position
	var moving := moved.length() > 0.05 * 60.0 * delta
	if moving and absf(moved.x) > 0.02:
		facing_left = moved.x < 0.0
	if moving and absf(moved.y) > 0.02:
		facing_back = moved.y < 0.0
	if attack_anim_t > 0.0:
		var k := clampi(int((0.3 - attack_anim_t) / 0.1), 0, 2)
		_set_col(Defs.FRAMES_ATTACK[k])
	elif moving:
		anim_t += delta * clampf(float(data["speed"]) / 8.0, 8.0, 14.0)
		_set_col(Defs.FRAMES_WALK[int(anim_t) % Defs.FRAMES_WALK.size()])
	else:
		var breath := int((GameState.elapsed + breath_phase) / 0.7) % 2
		_set_col(Defs.FRAMES_IDLE[breath])
	sprite.flip_h = facing_left
	_footsteps(moving, delta)


func _set_col(col: int) -> void:
	sprite.frame_coords = Vector2i(col, 1 if facing_back else 0)


## Dust where heavy feet land, and a dust trail behind vehicles.
func _footsteps(moving: bool, delta: float) -> void:
	var f := sprite.frame_coords.x
	var k: String = data.get("kind", "")
	if moving and k == "dino" and f != last_frame and (f == Defs.FRAMES_WALK[1] or f == Defs.FRAMES_WALK[4]):
		if world.is_on_screen(position):
			world.spawn_fx("dust", position + Vector2(randf_range(-3, 3) + (radius * 0.4 if f == Defs.FRAMES_WALK[1] else -radius * 0.2), 1),
				Color.WHITE, clampf(radius / 12.0, 0.6, 2.0))
	elif moving and k == "vehicle":
		trail_t -= delta
		if trail_t <= 0.0:
			trail_t = 0.12
			if world.is_on_screen(position):
				world.spawn_fx("dust", position + Vector2((radius if facing_left else -radius), 0), Color.WHITE, 1.2)
	last_frame = f


func _draw() -> void:
	var col: Color = Defs.faction_color(faction)
	var r := radius * 1.3
	draw_set_transform(Vector2(3, 1), 0.0, Vector2(1.0, 0.45))
	draw_circle(Vector2.ZERO, r * 1.1, Color(0.02, 0.05, 0.02, 0.18))
	draw_circle(Vector2.ZERO, r * 0.8, Color(0.02, 0.05, 0.02, 0.2))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.5))
	if selected:
		draw_arc(Vector2.ZERO, r + 2.0, 0.0, TAU, 28, col, 2.5)
	elif faction != "wild":
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 24, Color(col, 0.4), 1.5)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
