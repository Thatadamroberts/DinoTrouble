extends Node
## Tracks the current mission's objectives, shows hints, and decides
## victory (all objectives complete) or mission-specific defeat.

signal changed

const CHECK_INTERVAL := 0.5

var world = null
var mission: Dictionary = {}
var objectives: Array = []  # [{def, done, progress}]
var check_t := 0.0
var hinted := {}
var totals := {}


func setup(w, m: Dictionary) -> void:
	world = w
	mission = m
	objectives.clear()
	for o in m.get("objectives", []):
		objectives.append({"def": o, "done": false, "progress": ""})
	# how many buildings each "destroy" objective starts with
	for e in m.get("enemy_buildings", []) + (m.get("hard_extra", []) if GameState.difficulty >= 2 else []):
		totals[e[0]] = int(totals.get(e[0], 0)) + 1
	_evaluate_all(false)


func is_sequential() -> bool:
	return bool(mission.get("sequential", false))


## Objectives the HUD should list (sequential missions reveal them one by one).
func visible_objectives() -> Array:
	if not is_sequential():
		return objectives
	var out: Array = []
	for o in objectives:
		out.append(o)
		if not o["done"]:
			break
	return out


func _process(delta: float) -> void:
	if GameState.over or world == null:
		return
	check_t -= delta
	if check_t > 0.0:
		return
	check_t = CHECK_INTERVAL
	_evaluate_all(true)
	if bool(mission.get("lose_no_engineers", false)):
		var eng := 0
		for u in world.units_of("player"):
			if u.def_id == "engineer":
				eng += 1
		if eng == 0:
			GameState.notify("All engineers lost. The reserve can't keep running.")
			GameState.end_game(false)


func _evaluate_all(announce: bool) -> void:
	var all_done := true
	for o in objectives:
		if o["done"]:
			continue
		var r: Array = _evaluate(o["def"])
		o["progress"] = r[1]
		if r[0]:
			o["done"] = true
			if announce:
				GameState.notify("Objective complete: " + String(o["def"]["text"]))
				Audio.ui("objective")
		else:
			all_done = false
			if is_sequential():
				if announce and not hinted.has(o["def"]["text"]) and o["def"].has("hint"):
					hinted[o["def"]["text"]] = true
					GameState.notify("Next: " + String(o["def"]["hint"]))
				break
	changed.emit()
	if announce and all_done and not objectives.is_empty():
		GameState.end_game(true)


## Returns [done: bool, progress text].
func _evaluate(o: Dictionary) -> Array:
	var st: Dictionary = GameState.stats
	match String(o["type"]):
		"gather":
			var v := int(st.get("gathered_" + String(o["res"]), 0))
			return [v >= int(o["amount"]), "%d/%d" % [mini(v, int(o["amount"])), int(o["amount"])]]
		"hatch":
			var v2 := int(st.get("hatched", 0))
			return [v2 >= int(o["count"]), "%d/%d" % [mini(v2, int(o["count"])), int(o["count"])]]
		"build":
			var v3 := int(st.get("built_" + String(o["id"]), 0))
			return [v3 >= int(o["count"]), "%d/%d" % [mini(v3, int(o["count"])), int(o["count"])]]
		"tame":
			var v4 := int(st.get("tamed", 0))
			return [v4 >= int(o["count"]), "%d/%d" % [mini(v4, int(o["count"])), int(o["count"])]]
		"kill":
			var v5 := int(st.get("killed_" + String(o["id"]), 0))
			return [v5 >= int(o["count"]), "%d/%d" % [mini(v5, int(o["count"])), int(o["count"])]]
		"destroy":
			var alive := 0
			for b in get_tree().get_nodes_in_group("buildings"):
				if not b.dead and b.faction != "player" and b.def_id == String(o["id"]):
					alive += 1
			var total := maxi(int(totals.get(String(o["id"]), alive)), alive)
			return [alive == 0, "%d/%d" % [total - alive, total]]
		"survive":
			var left := maxf(0.0, float(o["seconds"]) - GameState.elapsed)
			var s := int(ceil(left))
			return [left <= 0.0, "%d:%02d left" % [s / 60, s % 60]]
	return [false, ""]
