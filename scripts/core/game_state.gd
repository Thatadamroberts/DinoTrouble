extends Node
## Match-wide state (autoload "GameState"): resources, settings, win/lose.

signal resources_changed
signal game_over(victory: bool)
signal message(text: String)

## Settings chosen in the main menu.
var difficulty := 1  # 0 easy, 1 normal, 2 hard
var hunger_enabled := true

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
