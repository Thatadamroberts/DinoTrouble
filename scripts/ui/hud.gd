extends CanvasLayer
## In-game interface: resource bar, messages, minimap, selection panel,
## command card, pause menu and end screen. Built in code.

const MinimapScript = preload("res://scripts/ui/minimap.gd")

const PANEL_BG := Color(0.12, 0.1, 0.07, 0.94)
const PANEL_BORDER := Color(0.55, 0.45, 0.25)
const TEXT := Color(0.95, 0.9, 0.75)

var world = null
var root: Control
var res_label: Label
var pop_label: Label
var time_label: Label
var msg_box: VBoxContainer
var minimap = null
var portrait: TextureRect
var name_label: Label
var stats_label: Label
var desc_label: Label
var multi_grid: GridContainer
var queue_box: HBoxContainer
var cmd_grid: GridContainer
var pause_panel: Control
var end_panel: Control
var end_title: Label
var end_stats: Label
var hunger_check: CheckButton
var actions: Array = []  # [{"key": int, "call": Callable}]
var info_t := 0.0


func setup(w) -> void:
	world = w
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	root = Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_top()
	_build_bottom()
	_build_messages()
	_build_pause()
	_build_end()
	world.selection.changed.connect(refresh_selection)
	GameState.message.connect(show_message)
	GameState.resources_changed.connect(_update_top)
	refresh_selection()
	_update_top()


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------
func _style(bg: Color = PANEL_BG) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = PANEL_BORDER
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	return sb


func _label(text: String, font_size: int = 14, color: Color = TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 3)
	return l


func _button(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(220, 38)
	b.add_theme_font_size_override("font_size", 18)
	b.pressed.connect(cb)
	return b


func _build_top() -> void:
	var top := PanelContainer.new()
	top.add_theme_stylebox_override("panel", _style())
	top.mouse_filter = Control.MOUSE_FILTER_STOP
	root.add_child(top)
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 28)
	top.add_child(hb)
	res_label = _label("", 16, Color(1.0, 0.85, 0.5))
	hb.add_child(res_label)
	pop_label = _label("", 16)
	hb.add_child(pop_label)
	var obj := _label("Objective: destroy the Poacher Camp (east)", 14, Color(0.8, 0.8, 0.7))
	hb.add_child(obj)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(spacer)
	time_label = _label("", 16)
	hb.add_child(time_label)
	var menu := Button.new()
	menu.text = "Menu (Esc)"
	menu.focus_mode = Control.FOCUS_NONE
	menu.pressed.connect(toggle_pause)
	hb.add_child(menu)


func _build_bottom() -> void:
	var bottom := PanelContainer.new()
	bottom.add_theme_stylebox_override("panel", _style())
	bottom.mouse_filter = Control.MOUSE_FILTER_STOP
	bottom.custom_minimum_size = Vector2(0, 168)
	root.add_child(bottom)
	bottom.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom.grow_vertical = Control.GROW_DIRECTION_BEGIN
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	bottom.add_child(hb)

	minimap = MinimapScript.new()
	minimap.setup(world)
	hb.add_child(minimap)
	hb.add_child(VSeparator.new())

	var info := VBoxContainer.new()
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(info)
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 10)
	info.add_child(head)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(72, 72)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	head.add_child(portrait)
	var txt := VBoxContainer.new()
	txt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(txt)
	name_label = _label("", 20)
	txt.add_child(name_label)
	stats_label = _label("", 14)
	txt.add_child(stats_label)
	queue_box = HBoxContainer.new()
	txt.add_child(queue_box)
	desc_label = _label("", 13, Color(0.8, 0.78, 0.68))
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc_label.custom_minimum_size = Vector2(300, 0)
	info.add_child(desc_label)
	multi_grid = GridContainer.new()
	multi_grid.columns = 12
	info.add_child(multi_grid)

	hb.add_child(VSeparator.new())
	cmd_grid = GridContainer.new()
	cmd_grid.columns = 4
	cmd_grid.add_theme_constant_override("h_separation", 4)
	cmd_grid.add_theme_constant_override("v_separation", 4)
	hb.add_child(cmd_grid)


func _build_messages() -> void:
	msg_box = VBoxContainer.new()
	msg_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(msg_box)
	msg_box.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	msg_box.offset_top = 44
	msg_box.offset_left = 16
	msg_box.offset_right = -16


func _overlay() -> Control:
	var c := Control.new()
	c.visible = false
	root.add_child(c)
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.55)
	c.add_child(dim)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return c


func _center_panel(parent: Control) -> VBoxContainer:
	var center := CenterContainer.new()
	parent.add_child(center)
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var panel := PanelContainer.new()
	var sb := _style()
	sb.content_margin_left = 28
	sb.content_margin_right = 28
	sb.content_margin_top = 20
	sb.content_margin_bottom = 20
	panel.add_theme_stylebox_override("panel", sb)
	center.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	panel.add_child(vb)
	return vb


func _build_pause() -> void:
	pause_panel = _overlay()
	var vb := _center_panel(pause_panel)
	var title := _label("Paused", 28)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(title)
	vb.add_child(_button("Resume", toggle_pause))
	hunger_check = CheckButton.new()
	hunger_check.text = "Dinosaur hunger"
	hunger_check.button_pressed = GameState.hunger_enabled
	hunger_check.toggled.connect(func(on): GameState.hunger_enabled = on)
	vb.add_child(hunger_check)
	vb.add_child(_button("Restart", _restart))
	vb.add_child(_button("Main Menu", _to_menu))
	if not OS.has_feature("web"):
		vb.add_child(_button("Quit", func(): get_tree().quit()))
	var help := _label(
		"Left-click / drag: select    Right-click: move, attack, gather, build, tame\n" +
		"A: attack-move    S: stop    Q/W/E/R: command card    Ctrl+1-9: set group\n" +
		"Arrow keys / screen edge / middle-drag: scroll    Wheel: zoom    Space: home", 12, Color(0.8, 0.78, 0.68))
	vb.add_child(help)


func _build_end() -> void:
	end_panel = _overlay()
	var vb := _center_panel(end_panel)
	end_title = _label("", 40)
	end_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(end_title)
	end_stats = _label("", 16)
	end_stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(end_stats)
	vb.add_child(_button("Play Again", _restart))
	vb.add_child(_button("Main Menu", _to_menu))


# ---------------------------------------------------------------------------
# Updates
# ---------------------------------------------------------------------------
func _process(delta: float) -> void:
	info_t -= delta
	if info_t <= 0.0:
		info_t = 0.25
		_update_top()
		_update_info()
	for l in msg_box.get_children():
		l.set_meta("t", float(l.get_meta("t", 0.0)) - delta)
		var t: float = l.get_meta("t")
		l.modulate.a = clampf(t, 0.0, 1.0)
		if t <= 0.0:
			l.queue_free()


func _update_top() -> void:
	if res_label == null:
		return
	res_label.text = "DNA: %d    Supplies: %d" % [GameState.get_res("player", "dna"), GameState.get_res("player", "supplies")]
	pop_label.text = "Units: %d/%d" % [world.count_units("player"), Defs.POP_CAP]
	var s := int(GameState.elapsed)
	time_label.text = "%02d:%02d" % [s / 60, s % 60]


func show_message(text: String) -> void:
	if msg_box == null:
		return
	var l := _label(text, 16)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.set_meta("t", 5.0)
	msg_box.add_child(l)
	while msg_box.get_child_count() > 4:
		var old := msg_box.get_child(0)
		msg_box.remove_child(old)
		old.queue_free()


func ping_minimap(pos: Vector2) -> void:
	if minimap != null:
		minimap.ping(pos)


func _alive(e) -> bool:
	return e != null and is_instance_valid(e) and not e.dead


func refresh_selection() -> void:
	for c in cmd_grid.get_children():
		c.queue_free()
	for c in multi_grid.get_children():
		c.queue_free()
	for c in queue_box.get_children():
		queue_box.remove_child(c)
		c.queue_free()
	actions.clear()
	var sel: Array = world.selection.selected.filter(func(e): return _alive(e))
	portrait.texture = null
	name_label.text = ""
	stats_label.text = ""
	desc_label.text = ""
	if sel.is_empty():
		desc_label.text = "Select units by left-clicking or dragging a box."
		return
	if sel.size() == 1:
		var e = sel[0]
		if e.kind_tag == "unit":
			portrait.texture = Defs.unit_portrait(e.def_id)
			desc_label.text = e.data.get("desc", "")
			if e.faction == "player":
				_unit_commands(sel)
		elif e.kind_tag == "building":
			portrait.texture = Defs.building_texture(e.def_id)
			desc_label.text = e.data.get("desc", "")
			if e.faction == "player" and e.built:
				_building_commands(e)
		else:
			portrait.texture = load("res://assets/sprites/resources/%s.png" % e.def_id)
			desc_label.text = "Right-click with Engineers to gather. Gives %s." % Defs.RES_NAMES[e.res_type]
	else:
		name_label.text = "%d units selected" % sel.size()
		for e in sel:
			var b := Button.new()
			b.icon = Defs.unit_portrait(e.def_id) if e.kind_tag == "unit" else null
			b.expand_icon = true
			b.custom_minimum_size = Vector2(34, 34)
			b.focus_mode = Control.FOCUS_NONE
			b.tooltip_text = e.display_name()
			b.pressed.connect(func(): world.selection.set_selection([e]))
			multi_grid.add_child(b)
		_unit_commands(sel.filter(func(e): return e.kind_tag == "unit" and e.faction == "player"))
	_update_info()


func _update_info() -> void:
	var sel: Array = world.selection.selected.filter(func(e): return _alive(e))
	if sel.size() != 1:
		return
	var e = sel[0]
	name_label.text = e.display_name()
	match e.kind_tag:
		"unit":
			var lines := "HP %d/%d    %s" % [int(e.hp), int(e.max_hp), e.state_text()]
			if e.is_dino() and e.faction == "player" and GameState.hunger_enabled:
				lines += "    Hunger %d%%" % int(e.hunger)
			if e.carry > 0:
				lines += "    Carrying %d %s" % [e.carry, Defs.RES_NAMES.get(e.carry_type, "")]
			lines += "\nDamage %d   Range %d   Speed %d" % [int(e.data["damage"]), int(e.data["range"]), int(e.data["speed"])]
			stats_label.text = lines
		"building":
			var lines := "HP %d/%d" % [int(e.hp), int(e.max_hp)]
			if not e.built:
				lines += "    Under construction: %d%%" % int(e.progress * 100.0)
			elif not e.queue.is_empty():
				lines += "    Producing %s: %d%%" % [Defs.UNITS[e.queue[0]]["name"], int(e.queue_progress() * 100.0)]
			stats_label.text = lines
			_update_queue(e)
		"resource":
			stats_label.text = "%d %s left" % [e.amount, Defs.RES_NAMES[e.res_type]]


func _update_queue(b) -> void:
	var ids: Array = b.queue
	if queue_box.get_child_count() == ids.size():
		return
	for c in queue_box.get_children():
		queue_box.remove_child(c)
		c.queue_free()
	for i in ids.size():
		var btn := Button.new()
		btn.icon = Defs.unit_portrait(ids[i])
		btn.expand_icon = true
		btn.custom_minimum_size = Vector2(30, 30)
		btn.focus_mode = Control.FOCUS_NONE
		btn.tooltip_text = "Click to cancel the last order (refunded)."
		btn.pressed.connect(func(): b.cancel_last())
		queue_box.add_child(btn)


func _cmd_button(icon: Texture2D, label: String, tip: String, cb: Callable) -> void:
	var slot := actions.size()
	var key: int = Defs.HOTKEYS[slot] if slot < Defs.HOTKEYS.size() else -1
	var b := Button.new()
	b.custom_minimum_size = Vector2(58, 58)
	b.focus_mode = Control.FOCUS_NONE
	if icon != null:
		b.icon = icon
		b.expand_icon = true
	else:
		b.text = label
	var key_name: String = Defs.HOTKEY_NAMES[slot] if slot < Defs.HOTKEY_NAMES.size() else ""
	b.tooltip_text = "%s  [%s]" % [tip, key_name]
	b.pressed.connect(cb)
	var hint := _label(key_name, 11, Color(1, 1, 0.6))
	hint.position = Vector2(3, 0)
	b.add_child(hint)
	cmd_grid.add_child(b)
	actions.append({"key": key, "call": cb})


func _unit_commands(units: Array) -> void:
	if units.is_empty():
		return
	var engineers := units.filter(func(u): return u.can_build())
	if not engineers.is_empty():
		for id in Defs.BUILD_MENU:
			var d: Dictionary = Defs.BUILDINGS[id]
			_cmd_button(Defs.building_texture(id), d["name"],
				"Build %s (%s)\n%s" % [d["name"], Defs.cost_text(d["cost"]), d["desc"]],
				func(): world.selection.begin_place(id))
	_cmd_button(null, "Attack\nMove", "Attack-move: click a destination; units fight anything on the way (A)",
		func(): world.selection.mode = "attack_move")
	_cmd_button(null, "Stop", "Stop (S)", _stop_units.bind(units))


func _stop_units(units: Array) -> void:
	for u in units:
		if _alive(u):
			u.cmd_stop()


func _building_commands(b) -> void:
	for id in b.trains():
		var d: Dictionary = Defs.UNITS[id]
		_cmd_button(Defs.unit_portrait(id), d["name"],
			"%s %s (%s)\n%s" % ["Hatch" if d["kind"] == "dino" else "Train", d["name"], Defs.cost_text(d["cost"]), d["desc"]],
			func(): b.train(id))


func hotkey(k: int) -> void:
	for a in actions:
		if a["key"] == k:
			a["call"].call()
			return


# ---------------------------------------------------------------------------
# Pause & end
# ---------------------------------------------------------------------------
func toggle_pause() -> void:
	if GameState.over:
		return
	var p := not get_tree().paused
	get_tree().paused = p
	pause_panel.visible = p
	hunger_check.button_pressed = GameState.hunger_enabled


func _unhandled_input(event: InputEvent) -> void:
	if get_tree().paused and pause_panel.visible and event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		toggle_pause()
		get_viewport().set_input_as_handled()


func show_end(victory: bool) -> void:
	pause_panel.visible = false
	end_title.text = "VICTORY!" if victory else "DEFEAT"
	end_title.add_theme_color_override("font_color", Color(0.5, 1.0, 0.5) if victory else Color(1.0, 0.4, 0.3))
	var s := int(GameState.elapsed)
	var st: Dictionary = GameState.stats
	var head := "The poachers have been driven off the island!" if victory else "The reserve has fallen to the poachers."
	end_stats.text = "%s\n\nTime: %02d:%02d\nDinosaurs hatched: %d    Tamed: %d\nPoachers defeated: %d    Units lost: %d" % [
		head, s / 60, s % 60, st["hatched"], st["tamed"], st["killed"], st["lost"]]
	end_panel.visible = true
	get_tree().paused = true


func _restart() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()


func _to_menu() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/menu.tscn")
