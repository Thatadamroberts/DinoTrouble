extends PanelContainer
## Campaign mission list with briefings. Locked missions open in order.

signal closed

const UI = preload("res://scripts/ui/ui_style.gd")
const Missions = preload("res://scripts/core/missions.gd")

var briefing: Label
var title: Label
var start: Button
var chosen := ""


func _ready() -> void:
	add_theme_stylebox_override("panel", UI.panel_style(20))
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 20)
	add_child(hb)

	var left := VBoxContainer.new()
	left.add_theme_constant_override("separation", 8)
	hb.add_child(left)
	left.add_child(UI.label("Campaign", 26))
	for i in Missions.CAMPAIGN.size():
		var m: Dictionary = Missions.CAMPAIGN[i]
		var done: bool = SaveSystem.completed.has(m["id"])
		var locked := i >= SaveSystem.unlocked
		var b := UI.button(("[done] " if done else "") + String(m["name"]) + ("  (locked)" if locked else ""), 300.0)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.disabled = locked
		b.pressed.connect(_select.bind(String(m["id"])))
		left.add_child(b)
	var back := UI.button("Back", 300.0)
	back.pressed.connect(func(): closed.emit())
	left.add_child(back)

	var right := VBoxContainer.new()
	right.custom_minimum_size = Vector2(420, 0)
	right.add_theme_constant_override("separation", 12)
	hb.add_child(right)
	title = UI.label("", 22, Color(1.0, 0.85, 0.45))
	right.add_child(title)
	briefing = UI.label("Choose a mission.", 15)
	briefing.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	briefing.custom_minimum_size = Vector2(420, 220)
	right.add_child(briefing)
	start = UI.button("Start Mission", 420.0)
	start.disabled = true
	start.pressed.connect(_start)
	right.add_child(start)
	var first: Dictionary = Missions.CAMPAIGN[mini(SaveSystem.unlocked, Missions.CAMPAIGN.size()) - 1]
	_select(String(first["id"]))


func _select(id: String) -> void:
	chosen = id
	var m: Dictionary = Missions.get_mission(id)
	title.text = String(m["name"])
	var objs := ""
	for o in m.get("objectives", []):
		objs += "\n  - " + String(o["text"])
	briefing.text = String(m["briefing"]) + "\n\nObjectives:" + objs
	start.disabled = false


func _start() -> void:
	GameState.mission_id = chosen
	GameState.pending_save = null
	get_tree().change_scene_to_file("res://scenes/main.tscn")
