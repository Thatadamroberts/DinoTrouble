extends Node
## Game data (autoload "Defs"): units, buildings and resources.
## Balance lives here so it can be tuned without touching game logic.
## Ranges are in iso pixels (one tile is roughly 45). Sight is in tiles.

const POP_CAP := 30

## Unit sprite sheet layout (all frames face right).
const SHEET_FRAMES := 13
## Rows: 0 = 3/4 front (heading down-right), 1 = 3/4 back (heading up-right).
const SHEET_ROWS := 2
const FRAMES_IDLE := [0, 1]
const FRAMES_WALK := [2, 3, 4, 5, 6, 7]
const FRAMES_ATTACK := [8, 9, 10]
const FRAMES_DEATH := [11, 12]

const UNITS := {
	# ---- Rangers (player) -------------------------------------------------
	"ranger": {
		"name": "Ranger", "kind": "human", "hp": 70, "speed": 70.0,
		"damage": 7, "range": 150.0, "cooldown": 1.0, "sight": 7,
		"cost": {"supplies": 50}, "time": 7.0, "projectile": "bullet",
		"radius": 8.0, "auto_attack": true,
		"desc": "Reserve ranger with a rifle. Cheap ranged support.",
	},
	"engineer": {
		"name": "Engineer", "kind": "human", "hp": 50, "speed": 66.0,
		"damage": 3, "range": 30.0, "cooldown": 1.2, "sight": 6,
		"cost": {"supplies": 45}, "time": 7.0,
		"radius": 8.0, "auto_attack": false, "gather": true, "build": true, "tame": true,
		"desc": "Gathers amber (DNA) and supplies, builds and repairs, and tames wild dinosaurs.",
	},
	# ---- Dinosaurs (hatched by the player) -----------------------------------
	"raptor": {
		"name": "Raptor", "kind": "dino", "hp": 85, "speed": 125.0,
		"damage": 9, "range": 34.0, "cooldown": 0.7, "sight": 7,
		"cost": {"dna": 75}, "time": 10.0,
		"radius": 11.0, "auto_attack": true, "hunger_rate": 0.55, "wild_aggro": true,
		"desc": "Fast, cheap pack hunter.",
	},
	"dilophosaurus": {
		"name": "Dilophosaurus", "kind": "dino", "hp": 90, "speed": 85.0,
		"damage": 11, "range": 140.0, "cooldown": 1.5, "sight": 7,
		"cost": {"dna": 100}, "time": 12.0, "projectile": "venom",
		"radius": 11.0, "auto_attack": true, "hunger_rate": 0.5, "wild_aggro": true,
		"desc": "Spits venom from range. Venom slows its victims.",
	},
	"triceratops": {
		"name": "Triceratops", "kind": "dino", "hp": 340, "speed": 55.0,
		"damage": 20, "range": 40.0, "cooldown": 1.6, "sight": 6,
		"cost": {"dna": 160, "supplies": 40}, "time": 18.0,
		"radius": 19.0, "auto_attack": true, "hunger_rate": 0.45, "wild_aggro": false,
		"ability": "charge",
		"desc": "Armoured tank. Charges into enemies, knocking them back and stunning them.",
	},
	"trex": {
		"name": "T. rex", "kind": "dino", "hp": 650, "speed": 68.0,
		"damage": 46, "range": 46.0, "cooldown": 2.0, "sight": 8,
		"cost": {"dna": 320, "supplies": 80}, "time": 30.0,
		"radius": 23.0, "auto_attack": true, "hunger_rate": 0.8, "wild_aggro": true,
		"ability": "roar", "splash": 50.0,
		"desc": "Apex predator. Its bite splashes nearby enemies and its roar scatters humans.",
	},
	# ---- Poachers (enemy) ---------------------------------------------------
	"hunter": {
		"name": "Hunter", "kind": "human", "hp": 75, "speed": 68.0,
		"damage": 8, "range": 150.0, "cooldown": 1.0, "sight": 7,
		"cost": {"supplies": 55}, "time": 8.0, "projectile": "bullet",
		"radius": 8.0, "auto_attack": true,
		"desc": "Poacher rifleman.",
	},
	"trapper": {
		"name": "Trapper", "kind": "human", "hp": 60, "speed": 66.0,
		"damage": 4, "range": 120.0, "cooldown": 2.0, "sight": 6,
		"cost": {"supplies": 50}, "time": 8.0, "projectile": "net",
		"radius": 8.0, "auto_attack": true, "gather": true,
		"desc": "Throws nets that stun dinosaurs. Also gathers resources for the poachers.",
	},
	"jeep": {
		"name": "Poacher Jeep", "kind": "vehicle", "hp": 180, "speed": 135.0,
		"damage": 6, "range": 135.0, "cooldown": 0.45, "sight": 8,
		"cost": {"supplies": 110, "dna": 40}, "time": 14.0, "projectile": "bullet",
		"radius": 16.0, "auto_attack": true,
		"desc": "Fast raider with a mounted gun.",
	},
}

const BUILDINGS := {
	"ranger_station": {
		"name": "Ranger Station", "hp": 1500, "size": 3, "sight": 8,
		"trains": ["engineer", "ranger"], "dropoff": true, "income": 1.0,
		"cost": {"supplies": 400}, "time": 60.0,
		"desc": "Headquarters. Trains rangers and engineers and receives resources. Supplies arrive here slowly.",
	},
	"hatchery": {
		"name": "Hatchery", "hp": 900, "size": 3, "sight": 6,
		"trains": ["raptor", "dilophosaurus", "triceratops", "trex"], "feeder": 200.0,
		"cost": {"supplies": 250}, "time": 40.0,
		"desc": "Incubates dinosaur eggs from DNA. Hungry dinosaurs feed near it.",
	},
	"watchtower": {
		"name": "Watchtower", "hp": 450, "size": 2, "sight": 9,
		"attack": {"damage": 9, "range": 230.0, "cooldown": 0.9},
		"cost": {"supplies": 120}, "time": 18.0,
		"desc": "Defensive tower with a ranger marksman.",
	},
	"supply_depot": {
		"name": "Supply Depot", "hp": 400, "size": 2, "sight": 5,
		"dropoff": true,
		"cost": {"supplies": 80}, "time": 14.0,
		"desc": "Forward drop-off point for gatherers.",
	},
	"poacher_camp": {
		"name": "Poacher Camp", "hp": 1800, "size": 3, "sight": 8,
		"trains": ["trapper", "hunter", "jeep"], "dropoff": true, "income": 1.2,
		"cost": {"supplies": 400}, "time": 60.0,
		"desc": "The poachers' base. Destroy it to win.",
	},
	"poacher_tower": {
		"name": "Poacher Tower", "hp": 450, "size": 2, "sight": 9,
		"attack": {"damage": 9, "range": 230.0, "cooldown": 0.9},
		"cost": {"supplies": 120}, "time": 18.0,
		"desc": "Poacher lookout with a sniper.",
	},
}

## What engineers can build, in command-card order.
const BUILD_MENU := ["watchtower", "supply_depot", "hatchery"]

const RESOURCES := {
	"amber": {"name": "Amber Deposit", "gives": "dna", "amount": 1200},
	"crates": {"name": "Supply Cache", "gives": "supplies", "amount": 500},
}

## Command-card hotkeys, in slot order.
const HOTKEYS := [KEY_Q, KEY_W, KEY_E, KEY_R, KEY_T, KEY_Y]
const HOTKEY_NAMES := ["Q", "W", "E", "R", "T", "Y"]

const RES_NAMES := {"dna": "DNA", "supplies": "Supplies"}


func faction_color(faction: String) -> Color:
	match faction:
		"player":
			return Color(0.35, 0.95, 0.4)
		"poacher":
			return Color(0.95, 0.3, 0.25)
		"wild":
			return Color(0.95, 0.85, 0.3)
	return Color(0.8, 0.8, 0.8)


func cost_text(cost: Dictionary) -> String:
	var parts: Array = []
	for k in cost.keys():
		parts.append("%d %s" % [int(cost[k]), RES_NAMES.get(k, k)])
	return ", ".join(parts)


var _tex_cache := {}


func unit_texture(id: String) -> Texture2D:
	return _tex("res://assets/sprites/units/%s.png" % id)


func building_texture(id: String) -> Texture2D:
	return _tex("res://assets/sprites/buildings/%s.png" % id)


## Frame 0 of a unit's sprite sheet, for portraits and buttons.
func unit_portrait(id: String) -> Texture2D:
	var key := "portrait_" + id
	if not _tex_cache.has(key):
		var sheet := unit_texture(id)
		var at := AtlasTexture.new()
		at.atlas = sheet
		at.region = Rect2(0, 0, sheet.get_width() / float(SHEET_FRAMES), sheet.get_height() / float(SHEET_ROWS))
		_tex_cache[key] = at
	return _tex_cache[key]


func _tex(path: String) -> Texture2D:
	if not _tex_cache.has(path):
		_tex_cache[path] = load(path)
	return _tex_cache[path]
