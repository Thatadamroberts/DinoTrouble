extends Node
## Match-wide state (autoload "GameState"): resources, settings, win/lose.

signal resources_changed
signal game_over(victory: bool)
signal message(text: String)

## Settings chosen in the main menu.
var difficulty := 1  # 0 easy, 1 normal, 2 hard
var hunger_enabled := true

## Day/night: time_of_day runs 0..1 over DAY_LENGTH seconds
## (0 dawn, ~0.1-0.55 day, ~0.6 dusk, ~0.7-0.93 night).
const DAY_LENGTH := 360.0
const NIGHT_CURVE := [[0.0, 0.5], [0.07, 0.0], [0.56, 0.0], [0.68, 1.0], [0.93, 1.0], [1.0, 0.5]]
var time_of_day := 0.15
var cycle_enabled := true

## Which mission is being played ("skirmish" or a campaign id), and a save
## to restore when the game scene starts (set by the load menu).
var mission_id := "skirmish"
var pending_save = null
var skip_briefing := false

var world = null
var resources := {}
var over := false
var victory := false
var elapsed := 0.0
var stats := {}


func reset() -> void:
	resources = {
		"player": {"dna": 200.0, "supplies": 350.0},
		"poacher": {"dna": 150.0, "supplies": 300.0},
		"wild": {"dna": 0.0, "supplies": 0.0},
	}
	over = false
	victory = false
	elapsed = 0.0
	stats = {"hatched": 0, "lost": 0, "killed": 0, "tamed": 0}
	time_of_day = 0.15
	cycle_enabled = true
	resources_changed.emit()


func _process(delta: float) -> void:
	if world != null and not over:
		elapsed += delta


func get_res(faction: String, kind: String) -> int:
	return int(resources.get(faction, {}).get(kind, 0.0))


func add(faction: String, kind: String, amount: float) -> void:
	if not resources.has(faction):
		return
	resources[faction][kind] = float(resources[faction].get(kind, 0.0)) + amount
	if faction == "player":
		resources_changed.emit()


func can_afford(faction: String, cost: Dictionary) -> bool:
	for k in cost.keys():
		if float(resources.get(faction, {}).get(k, 0.0)) < float(cost[k]):
			return false
	return true


## Deducts the cost if affordable. Tells the player what is missing otherwise.
func spend(faction: String, cost: Dictionary) -> bool:
	if not can_afford(faction, cost):
		if faction == "player":
			for k in cost.keys():
				if float(resources[faction].get(k, 0.0)) < float(cost[k]):
					notify("Not enough %s." % Defs.RES_NAMES.get(k, k))
					break
		return false
	for k in cost.keys():
		resources[faction][k] = float(resources[faction][k]) - float(cost[k])
	if faction == "player":
		resources_changed.emit()
	return true


func refund(faction: String, cost: Dictionary) -> void:
	for k in cost.keys():
		add(faction, k, float(cost[k]))


func notify(text: String) -> void:
	message.emit(text)


func end_game(won: bool) -> void:
	if over:
		return
	over = true
	victory = won
	game_over.emit(won)


## 0 in full daylight, 1 at deepest night.
func night() -> float:
	var t := fposmod(time_of_day, 1.0)
	for i in range(NIGHT_CURVE.size() - 1):
		var a: Array = NIGHT_CURVE[i]
		var b: Array = NIGHT_CURVE[i + 1]
		if t <= float(b[0]):
			return lerpf(float(a[1]), float(b[1]), (t - float(a[0])) / (float(b[0]) - float(a[0])))
	return 0.5


## Sight ranges shrink by up to a quarter at night.
func sight_mult() -> float:
	return 1.0 - 0.25 * night()


func phase_name() -> String:
	var t := fposmod(time_of_day, 1.0)
	if t < 0.07 or t >= 0.95:
		return "Dawn"
	if t < 0.55:
		return "Day"
	if t < 0.66:
		return "Dusk"
	return "Night"
