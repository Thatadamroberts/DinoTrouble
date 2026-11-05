extends Control
## Title screen: start a match, pick difficulty, toggle hunger, read controls.

const TEXT := Color(0.98, 0.92, 0.75)
const MissionSelect = preload("res://scripts/ui/mission_select.gd")
const SettingsPanel = preload("res://scripts/ui/settings_panel.gd")
const SavePanel = preload("res://scripts/ui/save_panel.gd")

var help_panel: PanelContainer
var main_box: VBoxContainer
var dialog: Control
var parade: Array = []


func _ready() -> void:
	get_tree().paused = false
	var bg := TextureRect.new()
	bg.texture = load("res://assets/sprites/ui/menu_bg.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	add_child(bg)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var vb := VBoxContainer.new()
	main_box = vb
	vb.add_theme_constant_override("separation", 12)
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	add_child(vb)
	vb.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	vb.grow_horizontal = Control.GROW_DIRECTION_BOTH
	vb.grow_vertical = Control.GROW_DIRECTION_BOTH

	var title := _label("DinoTrouble", 72)
	title.add_theme_constant_override("outline_size", 14)
	title.add_theme_color_override("font_color", Color(1.0, 0.82, 0.35))
	vb.add_child(title)
	var sub := _label("Hatch dinosaurs. Lead your rangers. Save the island.", 20)
	vb.add_child(sub)
	vb.add_child(_spacer(16))

	var campaign := _button("Campaign")
	campaign.pressed.connect(func(): _open(MissionSelect.new()))
	vb.add_child(campaign)
	campaign.grab_focus()

	var skirmish := _button("Skirmish")
	skirmish.pressed.connect(_start)
	vb.add_child(skirmish)

	var load_btn := _button("Load Game")
	load_btn.pressed.connect(func():
		var p = SavePanel.new()
		p.setup("load")
		_open(p)
	)
	vb.add_child(load_btn)

	var settings := _button("Settings")
	settings.pressed.connect(func(): _open(SettingsPanel.new()))
	vb.add_child(settings)

	var help := _button("How to Play")
	help.pressed.connect(func(): help_panel.visible = not help_panel.visible)
	vb.add_child(help)

	if not OS.has_feature("web"):
		var quit := _button("Quit")
		quit.pressed.connect(func(): get_tree().quit())
		vb.add_child(quit)

	_build_help()
	_build_parade()


func _label(text: String, font_size: int) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", TEXT)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.05, 0.05))
	l.add_theme_constant_override("outline_size", 6)
	return l


func _button(text: String) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(280, 46)
	b.add_theme_font_size_override("font_size", 22)
	return b


func _spacer(h: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	return c


func _build_help() -> void:
	help_panel = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.08, 0.06, 0.94)
	sb.border_color = Color(0.55, 0.45, 0.25)
	sb.set_border_width_all(2)
	sb.set_content_margin_all(16)
	help_panel.add_theme_stylebox_override("panel", sb)
	help_panel.visible = false
	add_child(help_panel)
	help_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_RIGHT)
	help_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	help_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	help_panel.offset_right = -24
	var l := Label.new()
	l.add_theme_font_size_override("font_size", 15)
	l.add_theme_color_override("font_color", TEXT)
	l.text = """HOW TO PLAY

Poachers have landed on your dinosaur reserve.
Destroy their camp in the east to win. Lose your
Ranger Station and Hatchery and the reserve falls.

ECONOMY
- Engineers gather Amber (DNA) and Supply Caches.
- Hatch dinosaurs at the Hatchery with DNA.
- Train Rangers and Engineers at the Ranger Station.
- Engineers build Watchtowers, Supply Depots and
  new Hatcheries.

DINOSAURS
- Raptor: fast pack hunter.
- Dilophosaurus: venom spit slows enemies.
- Triceratops: charges, knocking enemies back.
- T. rex: splash bite; its roar scatters humans.
- Dinosaurs get hungry. Starving ones go feral and
  head back to the Hatchery to feed.
- Engineers can tame wild dinosaurs. Predators must
  be wounded below half health first.

CONTROLS
Left-click / drag: select     Double-click: select type
Right-click: move / attack / gather / build / tame
A: attack-move   S: stop   Q W E R: command card
Ctrl+1-9: set group   1-9: select group   Space: home
Arrows / screen edge / middle-drag: scroll   Wheel: zoom
Esc: pause"""
	help_panel.add_child(l)


## A few dinosaurs strolling along the bottom of the title screen.
func _build_parade() -> void:
	var ids := ["raptor", "raptor", "triceratops", "dilophosaurus", "trex"]
	for i in ids.size():
		var s := Sprite2D.new()
		s.texture = Defs.unit_texture(ids[i])
		s.hframes = Defs.SHEET_FRAMES
		s.vframes = Defs.SHEET_ROWS
		s.scale = Vector2(2, 2)
		s.position = Vector2(-120.0 - i * 170.0, 0)
		add_child(s)
		parade.append(s)


func _process(delta: float) -> void:
	var w := size.x
	var t := Time.get_ticks_msec() / 1000.0
	for i in parade.size():
		var s: Sprite2D = parade[i]
		s.position.x += delta * 70.0
		if s.position.x > w + 120.0:
			s.position.x = -150.0
		s.position.y = size.y - 40.0 - s.texture.get_height() / float(Defs.SHEET_ROWS)
		s.frame = Defs.FRAMES_WALK[int(t * 10.0 + i) % Defs.FRAMES_WALK.size()]


func _start() -> void:
	GameState.mission_id = "skirmish"
	GameState.pending_save = null
	get_tree().change_scene_to_file("res://scenes/main.tscn")


## Shows a panel (mission select, settings, load) in place of the main buttons.
func _open(panel: Control) -> void:
	main_box.visible = false
	help_panel.visible = false
	dialog = CenterContainer.new()
	add_child(dialog)
	dialog.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dialog.add_child(panel)
	panel.closed.connect(func():
		dialog.queue_free()
		dialog = null
		main_box.visible = true
	)
