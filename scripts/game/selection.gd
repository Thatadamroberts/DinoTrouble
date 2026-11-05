extends Node2D
## Player input in the game world: selecting, commanding, building placement,
## control groups and hotkeys.

signal changed

var world = null
var selected: Array = []
var groups := {}
var dragging := false
var drag_start := Vector2.ZERO
var drag_now := Vector2.ZERO
var mode := ""  # "", "attack_move", "place"
var place_id := ""
var last_group_key := -1
var last_group_time := 0.0


func setup(w) -> void:
	world = w
	z_index = 60


func _process(_delta: float) -> void:
	if mode != "" or dragging:
		queue_redraw()


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------
func _alive(e) -> bool:
	return e != null and is_instance_valid(e) and not e.dead


func set_selection(arr: Array) -> void:
	for e in selected:
		if _alive(e):
			e.set_selected(false)
	selected = []
	for e in arr:
		if _alive(e) and not selected.has(e):
			selected.append(e)
			e.set_selected(true)
	if mode == "place" and _engineers().is_empty():
		mode = ""
	changed.emit()


func forget(e) -> void:
	if selected.has(e):
		selected.erase(e)
		changed.emit()
	for k in groups.keys():
		groups[k].erase(e)


func player_units() -> Array:
	var out: Array = []
	for e in selected:
		if _alive(e) and e.kind_tag == "unit" and e.faction == "player":
			out.append(e)
	return out


func _engineers() -> Array:
	var out: Array = []
	for u in player_units():
		if u.can_build():
			out.append(u)
	return out


func single_building():
	if selected.size() == 1 and _alive(selected[0]) and selected[0].kind_tag == "building" and selected[0].faction == "player":
		return selected[0]
	return null


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
func _unhandled_input(event: InputEvent) -> void:
	if GameState.over:
		return
	if event is InputEventMouseButton:
		var pos := get_global_mouse_position()
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				if mode == "place":
					_try_place(pos, event.shift_pressed)
					return
				if mode == "attack_move":
					_attack_move(pos)
					if not event.shift_pressed:
						mode = ""
					return
				if event.double_click:
					_select_same_type(pos)
					dragging = false
					return
				dragging = true
				drag_start = pos
				drag_now = pos
			elif dragging:
				dragging = false
				if drag_start.distance_to(pos) < 6.0:
					_click_select(pos, event.shift_pressed)
				else:
					_box_select(Rect2(drag_start, pos - drag_start).abs(), event.shift_pressed)
				queue_redraw()
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			if mode != "":
				mode = ""
				queue_redraw()
				return
			command_at(pos)
	elif event is InputEventMouseMotion:
		if dragging:
			drag_now = get_global_mouse_position()
	elif event is InputEventKey and event.pressed and not event.echo:
		_key(event)


func _key(e: InputEventKey) -> void:
	var k := e.keycode
	if k == KEY_ESCAPE:
		if mode != "":
			mode = ""
			queue_redraw()
		else:
			world.hud.toggle_pause()
		return
	if k >= KEY_1 and k <= KEY_9:
		var n := int(k - KEY_0)
		if e.ctrl_pressed or e.meta_pressed:
			groups[n] = player_units()
			GameState.notify("Group %d assigned (%d units)." % [n, groups[n].size()])
		elif groups.has(n):
			var now := Time.get_ticks_msec() / 1000.0
			var alive: Array = groups[n].filter(func(u): return _alive(u))
			set_selection(alive)
			if last_group_key == n and now - last_group_time < 0.4 and not alive.is_empty():
				world.camera.focus_on(alive[0].position)
			last_group_key = n
			last_group_time = now
		return
	match k:
		KEY_A:
			if not player_units().is_empty():
				mode = "attack_move"
		KEY_S:
			for u in player_units():
				u.cmd_stop()
		KEY_SPACE:
			world.focus_home()
		KEY_DELETE:
			var b = single_building()
			if b != null:
				b.cancel_last()
		_:
			world.hud.hotkey(k)


func _click_select(pos: Vector2, shift: bool) -> void:
	var e = world.entity_at(pos)
	if e == null:
		if not shift:
			set_selection([])
		return
	if shift and e.kind_tag == "unit" and e.faction == "player" and not selected.is_empty() and selected[0].kind_tag == "unit" and selected[0].faction == "player":
		var arr := selected.duplicate()
		if arr.has(e):
			arr.erase(e)
		else:
			arr.append(e)
		set_selection(arr)
	else:
		set_selection([e])
	if e.faction == "player":
		world.play_ui("select")


func _box_select(rect: Rect2, shift: bool) -> void:
	var arr: Array = selected.duplicate() if shift else []
	for u in get_tree().get_nodes_in_group("faction_player"):
		if u.kind_tag != "unit" or u.dead:
			continue
		if rect.has_point(u.position) or rect.has_point(u.position + Vector2(0, -u.pick_h)):
			if not arr.has(u):
				arr.append(u)
	if arr.is_empty() and not shift:
		set_selection([])
		return
	# Prefer units over buildings when mixing.
	set_selection(arr.filter(func(e): return e.kind_tag == "unit"))
	if not selected.is_empty():
		world.play_ui("select")


func _select_same_type(pos: Vector2) -> void:
	var e = world.entity_at(pos)
	if e == null or e.kind_tag != "unit" or e.faction != "player":
		_click_select(pos, false)
		return
	var view: Rect2 = world.view_rect()
	var arr: Array = []
	for u in get_tree().get_nodes_in_group("faction_player"):
		if u.kind_tag == "unit" and not u.dead and u.def_id == e.def_id and view.has_point(u.position):
			arr.append(u)
	set_selection(arr)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
func command_at(pos: Vector2) -> void:
	var units := player_units()
	if units.is_empty():
		var b = single_building()
		if b != null and b.built:
			b.rally = pos
			b.has_rally = true
			world.spawn_fx("marker", pos, Color(0.4, 0.9, 1.0))
		return
	var tgt = world.entity_at(pos)
	if tgt != null and tgt.kind_tag == "resource":
		var any_gather := false
		for u in units:
			if u.can_gather():
				u.cmd_gather(tgt)
				any_gather = true
		var rest: Array = units.filter(func(u): return not u.can_gather())
		if not rest.is_empty():
			_move_group(rest, pos)
		if any_gather:
			world.spawn_fx("marker", tgt.position, Color(1.0, 0.8, 0.3))
		return
	if tgt != null and tgt.faction == "player":
		if tgt.kind_tag == "building" and (not tgt.built or tgt.hp < tgt.max_hp):
			var builders: Array = units.filter(func(u): return u.can_build())
			for u in builders:
				u.cmd_build(tgt)
			var rest: Array = units.filter(func(u): return not u.can_build())
			if not rest.is_empty():
				_move_group(rest, pos)
			return
		_move_group(units, pos)
		return
	if tgt != null and tgt.faction == "wild":
		for u in units:
			if u.can_tame():
				u.cmd_tame(tgt)
			else:
				u.cmd_attack(tgt)
		world.spawn_fx("marker", tgt.position, Color(1.0, 0.85, 0.3))
		return
	if tgt != null:
		for u in units:
			u.cmd_attack(tgt)
		world.spawn_fx("marker", tgt.position, Color(1.0, 0.3, 0.25))
		return
	_move_group(units, pos)


func _move_group(units: Array, pos: Vector2) -> void:
	var offs := _formation(units.size())
	for i in units.size():
		units[i].cmd_move(pos + offs[i])
	world.spawn_fx("marker", pos, Color(0.4, 1.0, 0.45))


func _attack_move(pos: Vector2) -> void:
	var units := player_units()
	var offs := _formation(units.size())
	for i in units.size():
		units[i].cmd_attack_move(pos + offs[i])
	world.spawn_fx("marker", pos, Color(1.0, 0.3, 0.25))


func _formation(n: int) -> Array:
	var out: Array = []
	var cols := int(ceil(sqrt(float(n))))
	for i in n:
		var r := i / cols
		var c := i % cols
		out.append(Vector2((c - (cols - 1) / 2.0) * 26.0, (r - (cols - 1) / 2.0) * 14.0))
	return out


# ---------------------------------------------------------------------------
# Building placement
# ---------------------------------------------------------------------------
func begin_place(id: String) -> void:
	if _engineers().is_empty():
		return
	if not GameState.can_afford("player", Defs.BUILDINGS[id]["cost"]):
		GameState.spend("player", Defs.BUILDINGS[id]["cost"])  # shows the message
		return
	place_id = id
	mode = "place"


func _place_origin(pos: Vector2) -> Vector2i:
	var s: int = Defs.BUILDINGS[place_id]["size"]
	var g: Vector2 = Iso.world_to_grid(pos)
	return Vector2i(roundi(g.x - (s - 1) / 2.0), roundi(g.y - (s - 1) / 2.0))


func _try_place(pos: Vector2, keep: bool) -> void:
	var origin := _place_origin(pos)
	if not world.can_place(place_id, origin):
		GameState.notify("Can't build there.")
		return
	if not GameState.spend("player", Defs.BUILDINGS[place_id]["cost"]):
		mode = ""
		return
	var b = world.spawn_building(place_id, "player", origin, false)
	for u in _engineers():
		u.cmd_build(b)
	world.play_sfx("build", b.position)
	if not keep:
		mode = ""
	queue_redraw()


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
func _draw() -> void:
	if dragging and drag_start.distance_to(drag_now) >= 6.0:
		var r := Rect2(drag_start, drag_now - drag_start).abs()
		draw_rect(r, Color(0.4, 1.0, 0.45, 0.12))
		draw_rect(r, Color(0.4, 1.0, 0.45, 0.9), false, 1.0)
	var mouse := get_global_mouse_position()
	if mode == "place":
		var s: int = Defs.BUILDINGS[place_id]["size"]
		var origin := _place_origin(mouse)
		var ok: bool = world.can_place(place_id, origin)
		var c := Color(0.3, 1.0, 0.4, 0.35) if ok else Color(1.0, 0.25, 0.2, 0.35)
		for y in s:
			for x in s:
				var p: Vector2 = Iso.tile_to_world(origin + Vector2i(x, y))
				draw_colored_polygon(PackedVector2Array([p + Vector2(-32, 0), p + Vector2(0, 16), p + Vector2(32, 0), p + Vector2(0, -16)]), c)
		var tex: Texture2D = Defs.building_texture(place_id)
		var center: Vector2 = Iso.tile_to_world(Vector2(origin.x + (s - 1) / 2.0, origin.y + (s - 1) / 2.0))
		draw_texture(tex, center + Vector2(-tex.get_width() / 2.0, -(tex.get_height() - s * 16.0)), Color(1, 1, 1, 0.55))
	elif mode == "attack_move":
		var c := Color(1.0, 0.3, 0.25)
		draw_arc(mouse, 10.0, 0.0, TAU, 20, c, 2.0)
		draw_line(mouse + Vector2(-14, 0), mouse + Vector2(14, 0), c, 1.5)
		draw_line(mouse + Vector2(0, -14), mouse + Vector2(0, 14), c, 1.5)
	var b = single_building()
	if b != null and b.has_rally:
		draw_dashed_line(b.position, b.rally, Color(0.4, 0.9, 1.0, 0.7), 1.5, 6.0)
		draw_line(b.rally, b.rally + Vector2(0, -18), Color(0.9, 0.9, 0.9), 1.5)
		draw_colored_polygon(PackedVector2Array([b.rally + Vector2(0, -18), b.rally + Vector2(10, -15), b.rally + Vector2(0, -12)]), Color(0.4, 0.9, 1.0))
