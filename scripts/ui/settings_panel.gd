extends PanelContainer
## Settings: volume, scrolling, fullscreen, hunger and difficulty.

signal closed

const UI = preload("res://scripts/ui/ui_style.gd")


func _ready() -> void:
	add_theme_stylebox_override("panel", UI.panel_style(20))
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	add_child(vb)
	vb.add_child(UI.label("Settings", 26))

	vb.add_child(UI.label("Master volume", 15, UI.DIM))
	var vol := HSlider.new()
	vol.min_value = 0.0
	vol.max_value = 1.0
	vol.step = 0.05
	vol.custom_minimum_size = Vector2(300, 24)
	vol.value = float(SaveSystem.settings["master_volume"])
	vol.value_changed.connect(func(v): SaveSystem.set_setting("master_volume", v))
	vb.add_child(vol)

	vb.add_child(UI.label("Camera scroll speed", 15, UI.DIM))
	var spd := HSlider.new()
	spd.min_value = 0.4
	spd.max_value = 2.0
	spd.step = 0.1
	spd.custom_minimum_size = Vector2(300, 24)
	spd.value = float(SaveSystem.settings["scroll_speed"])
	spd.value_changed.connect(func(v): SaveSystem.set_setting("scroll_speed", v))
	vb.add_child(spd)

	var edge := CheckButton.new()
	edge.text = "Scroll at screen edges"
	edge.button_pressed = bool(SaveSystem.settings["edge_scroll"])
	edge.toggled.connect(func(on): SaveSystem.set_setting("edge_scroll", on))
	vb.add_child(edge)

	if not OS.has_feature("web"):
		var fs := CheckButton.new()
		fs.text = "Fullscreen"
		fs.button_pressed = bool(SaveSystem.settings["fullscreen"])
		fs.toggled.connect(func(on): SaveSystem.set_setting("fullscreen", on))
		vb.add_child(fs)

	var hunger := CheckButton.new()
	hunger.text = "Dinosaur hunger"
	hunger.button_pressed = GameState.hunger_enabled
	hunger.toggled.connect(func(on):
		GameState.hunger_enabled = on
		SaveSystem.save_settings()
	)
	vb.add_child(hunger)

	var diff := OptionButton.new()
	for n in ["Difficulty: Easy", "Difficulty: Normal", "Difficulty: Hard"]:
		diff.add_item(n)
	diff.selected = GameState.difficulty
	diff.item_selected.connect(func(i):
		GameState.difficulty = i
		SaveSystem.save_settings()
	)
	vb.add_child(diff)

	var close := UI.button("Back")
	close.pressed.connect(func(): closed.emit())
	vb.add_child(close)
