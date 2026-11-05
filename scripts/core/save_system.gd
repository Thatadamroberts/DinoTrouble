extends Node
## Persistence (autoload "SaveSystem"): campaign progress, settings and
## mid-mission save games. Everything lives under user://, which is a real
## folder for the desktop build and browser storage (IndexedDB) on the web.

const PROGRESS_PATH := "user://progress.cfg"
const SETTINGS_PATH := "user://settings.cfg"
const SAVE_DIR := "user://saves"
const SLOTS := ["slot1", "slot2", "slot3"]
const AUTOSAVE := "autosave"
const VERSION := 1

var unlocked := 1  # campaign missions available
var completed := {}  # mission id -> true
var settings := {
	"master_volume": 0.8,
	"music_volume": 0.6,
	"sfx_volume": 0.9,
	"ambience_volume": 0.7,
	"edge_scroll": true,
	"scroll_speed": 1.0,
	"fullscreen": false,
	"hunger": true,
	"difficulty": 1,
}
var pending_ai = null  # restored AI timers, consumed by the AI on setup
var pending_camera = null


func _ready() -> void:
	load_progress()
	load_settings()
	apply_settings()


# ---------------------------------------------------------------------------
# Campaign progress
# ---------------------------------------------------------------------------
func load_progress() -> void:
	var cf := ConfigFile.new()
	if cf.load(PROGRESS_PATH) == OK:
		unlocked = int(cf.get_value("campaign", "unlocked", 1))
		completed = cf.get_value("campaign", "completed", {})


func save_progress() -> void:
	var cf := ConfigFile.new()
	cf.set_value("campaign", "unlocked", unlocked)
	cf.set_value("campaign", "completed", completed)
	cf.save(PROGRESS_PATH)


func mark_completed(mission_id: String, index: int, total: int) -> void:
	completed[mission_id] = true
	unlocked = clampi(maxi(unlocked, index + 2), 1, total)
	save_progress()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(SETTINGS_PATH) == OK:
		for k in settings.keys():
			settings[k] = cf.get_value("settings", k, settings[k])
	GameState.hunger_enabled = bool(settings["hunger"])
	GameState.difficulty = int(settings["difficulty"])


func save_settings() -> void:
	settings["hunger"] = GameState.hunger_enabled
	settings["difficulty"] = GameState.difficulty
	var cf := ConfigFile.new()
	for k in settings.keys():
		cf.set_value("settings", k, settings[k])
	cf.save(SETTINGS_PATH)


func apply_settings() -> void:
	var bus := AudioServer.get_bus_index("Master")
	var v := clampf(float(settings["master_volume"]), 0.0, 1.0)
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(v, 0.0001)))
	AudioServer.set_bus_mute(bus, v <= 0.001)
	for pair in [["Music", "music_volume"], ["SFX", "sfx_volume"], ["UI", "sfx_volume"], ["Ambience", "ambience_volume"]]:
		var bi := AudioServer.get_bus_index(pair[0])
		if bi >= 0:
			var lv := clampf(float(settings[pair[1]]), 0.0, 1.0)
			AudioServer.set_bus_volume_db(bi, linear_to_db(maxf(lv, 0.0001)))
			AudioServer.set_bus_mute(bi, lv <= 0.001)
	if not OS.has_feature("web") and DisplayServer.get_name() != "headless":
		var fs := bool(settings["fullscreen"])
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fs else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != mode:
			DisplayServer.window_set_mode(mode)


func set_setting(key: String, value) -> void:
	settings[key] = value
	apply_settings()
	save_settings()


# ---------------------------------------------------------------------------
# Save games
# ---------------------------------------------------------------------------
func _path(slot: String) -> String:
	return "%s/%s.json" % [SAVE_DIR, slot]


func has_save(slot: String) -> bool:
	return FileAccess.file_exists(_path(slot))


## Summary for the load menu: {mission, name, elapsed, saved_at} or {} if empty.
func save_info(slot: String) -> Dictionary:
	var data = read_save(slot)
	if data == null:
		return {}
	return {"mission": data.get("mission", "skirmish"), "name": data.get("mission_name", "Skirmish"),
		"elapsed": float(data.get("elapsed", 0.0)), "saved_at": String(data.get("saved_at", ""))}


func read_save(slot: String):
	if not has_save(slot):
		return null
	var f := FileAccess.open(_path(slot), FileAccess.READ)
	if f == null:
		return null
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY or int(data.get("version", 0)) != VERSION:
		return null
	return data


func save_game(world, slot: String) -> bool:
	if world == null or GameState.over:
		return false
	DirAccess.make_dir_recursive_absolute(SAVE_DIR)
	var f := FileAccess.open(_path(slot), FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(serialize(world)))
	f.close()
	return true


## Starts the game scene with a saved match (from the menu or the pause menu).
func load_game(slot: String) -> bool:
	var data = read_save(slot)
	if data == null:
		return false
	GameState.mission_id = String(data.get("mission", "skirmish"))
	GameState.difficulty = int(data.get("difficulty", 1))
	GameState.hunger_enabled = bool(data.get("hunger", true))
	GameState.pending_save = data
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/main.tscn")
	return true


static func _v(v: Vector2) -> Array:
	return [v.x, v.y]


static func _vi(v: Vector2i) -> Array:
	return [v.x, v.y]


func serialize(world) -> Dictionary:
	var buildings: Array = []
	for b in world.get_tree().get_nodes_in_group("buildings"):
		if b.dead:
			continue
		buildings.append({"id": b.def_id, "faction": b.faction, "origin": _vi(b.origin), "hp": b.hp,
			"built": b.built, "progress": b.progress, "queue": b.queue.duplicate(), "queue_t": b.queue_t,
			"rally": _v(b.rally), "has_rally": b.has_rally})
	var units: Array = []
	for u in world.get_tree().get_nodes_in_group("units"):
		if u.dead:
			continue
		units.append({"id": u.def_id, "faction": u.faction, "pos": _v(u.position), "hp": u.hp,
			"hunger": u.hunger, "carry": u.carry, "carry_type": u.carry_type, "home": _v(u.home)})
	var nodes: Array = []
	for r in world.get_tree().get_nodes_in_group("resources"):
		if not r.dead:
			nodes.append({"id": r.def_id, "tile": _vi(r.tile), "amount": r.amount})
	return {
		"version": VERSION,
		"mission": GameState.mission_id,
		"mission_name": String(world.mission.get("name", "Skirmish")),
		"seed": world.map_seed,
		"difficulty": GameState.difficulty,
		"hunger": GameState.hunger_enabled,
		"time_of_day": GameState.time_of_day,
		"cycle": GameState.cycle_enabled,
		"elapsed": GameState.elapsed,
		"stats": GameState.stats,
		"resources": GameState.resources,
		"buildings": buildings,
		"units": units,
		"nodes": nodes,
		"explored": Marshalls.raw_to_base64(world.fog.explored),
		"ai": {"wave_t": world.ai.wave_t, "wave_n": world.ai.wave_n, "min_wave": world.ai.min_wave},
		"camera": _v(world.camera.position),
		"saved_at": Time.get_datetime_string_from_system(false, true),
	}


## Rebuilds a match inside a freshly generated world (same seed => same map).
func restore(world, data: Dictionary) -> void:
	GameState.time_of_day = float(data.get("time_of_day", 0.15))
	GameState.cycle_enabled = bool(data.get("cycle", true))
	GameState.elapsed = float(data.get("elapsed", 0.0))
	GameState.stats = data.get("stats", GameState.stats)
	var res: Dictionary = data.get("resources", {})
	for f in res.keys():
		GameState.resources[f] = {"dna": float(res[f].get("dna", 0.0)), "supplies": float(res[f].get("supplies", 0.0))}
	for n in data.get("nodes", []):
		var node = world.spawn_resource(String(n["id"]), Vector2i(int(n["tile"][0]), int(n["tile"][1])))
		node.amount = int(n["amount"])
	for bd in data.get("buildings", []):
		var b = world.spawn_building(String(bd["id"]), String(bd["faction"]), Vector2i(int(bd["origin"][0]), int(bd["origin"][1])), bool(bd["built"]))
		b.hp = float(bd["hp"])
		b.progress = float(bd["progress"])
		if not b.built:
			b.sprite.modulate = Color(1, 1, 1, 0.4 + 0.6 * b.progress)
		b.queue = Array(bd.get("queue", []))
		b.queue_t = float(bd.get("queue_t", 0.0))
		b.rally = Vector2(float(bd["rally"][0]), float(bd["rally"][1]))
		b.has_rally = bool(bd.get("has_rally", false))
	for ud in data.get("units", []):
		var u = world.spawn_unit(String(ud["id"]), String(ud["faction"]), Vector2(float(ud["pos"][0]), float(ud["pos"][1])))
		u.hp = float(ud["hp"])
		u.hunger = float(ud.get("hunger", 100.0))
		u.carry = int(ud.get("carry", 0))
		u.carry_type = String(ud.get("carry_type", ""))
		u.home = Vector2(float(ud["home"][0]), float(ud["home"][1]))
	var explored := Marshalls.base64_to_raw(String(data.get("explored", "")))
	if explored.size() == world.fog.explored.size():
		world.fog.explored = explored
	pending_ai = data.get("ai", null)
	var cam: Array = data.get("camera", [])
	pending_camera = Vector2(float(cam[0]), float(cam[1])) if cam.size() == 2 else null
	GameState.resources_changed.emit()
