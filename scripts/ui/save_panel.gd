extends PanelContainer
## Lists save slots. In "save" mode a slot click saves the running match;
## in "load" mode it loads that save (autosave included).

signal closed

const UI = preload("res://scripts/ui/ui_style.gd")

var mode := "load"
var world = null
var list: VBoxContainer


func setup(m: String, w = null) -> void:
	mode = m
	world = w


func _ready() -> void:
	add_theme_stylebox_override("panel", UI.panel_style(20))
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	add_child(vb)
	vb.add_child(UI.label("Save Game" if mode == "save" else "Load Game", 26))
	list = VBoxContainer.new()
	list.add_theme_constant_override("separation", 6)
	vb.add_child(list)
	var close := UI.button("Back")
	close.pressed.connect(func(): closed.emit())
	vb.add_child(close)
	_refresh()


func _refresh() -> void:
	for c in list.get_children():
		c.queue_free()
	var slots: Array = SaveSystem.SLOTS.duplicate()
	if mode == "load":
		slots.push_front(SaveSystem.AUTOSAVE)
	for slot in slots:
		var info: Dictionary = SaveSystem.save_info(slot)
		var title := "Autosave" if slot == SaveSystem.AUTOSAVE else "Slot " + String(slot).trim_prefix("slot")
		var text := "%s:  (empty)" % title
		if not info.is_empty():
			var s := int(info["elapsed"])
			text = "%s:  %s  %02d:%02d   %s" % [title, info["name"], s / 60, s % 60, info["saved_at"]]
		var b := UI.button(text, 520.0)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.disabled = mode == "load" and info.is_empty()
		b.pressed.connect(_on_slot.bind(slot))
		list.add_child(b)


func _on_slot(slot: String) -> void:
	if mode == "save":
		if SaveSystem.save_game(world, slot):
			GameState.notify("Game saved.")
		else:
			GameState.notify("Could not save the game.")
		_refresh()
	else:
		SaveSystem.load_game(slot)
