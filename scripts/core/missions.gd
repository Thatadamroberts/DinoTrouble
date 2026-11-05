extends RefCounted
## Campaign data. Every mission shares the reserve's starting position (south-
## west) but gets its own island seed, enemy layout, time of day, poacher AI
## behaviour and objectives. "skirmish" is the free-play map.
##
## Objective types:
##   gather  {res, amount}   resources delivered by gatherers
##   hatch   {count}         dinosaurs hatched
##   build   {id, count}     buildings of a type completed
##   tame    {count}         wild dinosaurs tamed
##   destroy {id}            every enemy building of that type destroyed
##   kill    {id, count}     enemy units of that type killed
##   survive {seconds}       hold out until the timer runs out

const DEFAULT_PLAYER_UNITS := ["engineer", "engineer", "engineer", "ranger", "ranger", "raptor", "raptor"]

const SKIRMISH := {
	"id": "skirmish", "name": "Skirmish",
	"briefing": "Free play: destroy the poacher camp in the east before they overrun the reserve.",
	"seed": -1, "time": 0.15, "cycle": true,
	"enemy_buildings": [["poacher_camp", Vector2i(48, 13)], ["poacher_tower", Vector2i(44, 16)]],
	"hard_extra": [["poacher_tower", Vector2i(51, 18)]],
	"enemy_units": ["trapper", "trapper", "trapper", "hunter", "hunter", "hunter", "jeep"],
	"objectives": [{"type": "destroy", "id": "poacher_camp", "text": "Destroy the Poacher Camp (east)"}],
	"ai": {"waves": true},
}

const CAMPAIGN := [
	{
		"id": "m1", "name": "1. A New Reserve",
		"briefing": "Welcome, Warden. The reserve is yours to run. Get the hatchery working, " +
			"fortify the station and win over the island's wild residents.\n\n" +
			"Engineers gather amber (DNA) and supplies. The hatchery turns DNA into dinosaurs.",
		"seed": 1101, "time": 0.12, "cycle": true, "sequential": true,
		"enemy_buildings": [], "enemy_units": [],
		"objectives": [
			{"type": "gather", "res": "dna", "amount": 60, "text": "Gather DNA from an amber deposit",
				"hint": "Select Engineers and right-click an amber deposit."},
			{"type": "hatch", "count": 2, "text": "Hatch dinosaurs at the Hatchery",
				"hint": "Select the Hatchery and press Q to hatch a Raptor."},
			{"type": "build", "id": "watchtower", "count": 1, "text": "Build a Watchtower",
				"hint": "Select an Engineer, press Q, then click open ground."},
			{"type": "tame", "count": 1, "text": "Tame a wild dinosaur",
				"hint": "Right-click a wild Triceratops with an Engineer. Predators must be wounded first."},
		],
		"ai": {"waves": false},
	},
	{
		"id": "m2", "name": "2. Stolen Eggs",
		"briefing": "Poachers raided the hatchery overnight and caged our eggs at an outpost in the northeast. " +
			"Strike under cover of darkness, break open the cages and bring the hatchlings home.\n\n" +
			"There is no camp to resupply them, so every guard you defeat stays down.",
		"seed": 2207, "time": 0.70, "cycle": true,
		"player_units": ["engineer", "engineer", "ranger", "ranger", "raptor", "raptor", "raptor", "dilophosaurus"],
		"enemy_buildings": [["egg_cage", Vector2i(45, 17)], ["egg_cage", Vector2i(52, 11)], ["egg_cage", Vector2i(48, 19)],
			["poacher_tower", Vector2i(47, 13)], ["poacher_tower", Vector2i(50, 16)]],
		"enemy_units": ["hunter", "hunter", "hunter", "hunter", "trapper", "trapper"],
		"objectives": [{"type": "destroy", "id": "egg_cage", "text": "Break open the egg cages"}],
		"ai": {"waves": false},
	},
	{
		"id": "m3", "name": "3. Hold the Line",
		"briefing": "A supply boat is on its way with reinforcements, but the poachers know it. " +
			"Their main force is coming in waves. Hold the reserve until the boat arrives.",
		"seed": 3313, "time": 0.30, "cycle": true,
		"player_units": ["engineer", "engineer", "engineer", "ranger", "ranger", "ranger", "ranger", "raptor", "raptor", "triceratops"],
		"player_res": {"dna": 300, "supplies": 500},
		"enemy_buildings": [["poacher_camp", Vector2i(48, 13)], ["poacher_tower", Vector2i(44, 16)]],
		"enemy_units": ["trapper", "trapper", "trapper", "hunter", "hunter", "hunter", "hunter"],
		"enemy_res": {"dna": 400, "supplies": 700},
		"objectives": [{"type": "survive", "seconds": 360, "text": "Hold out until the supply boat arrives"}],
		"ai": {"waves": true, "first_wave": 50.0, "interval": 40.0, "min_wave": 3, "income": 1.6},
	},
	{
		"id": "m4", "name": "4. Jeep Raids",
		"briefing": "Poacher jeeps are hunting our engineers in the field. Hunt the hunters: " +
			"destroy their jeeps before they cripple the reserve's economy.\n\n" +
			"Don't lose all your engineers, or the reserve can't be kept running.",
		"seed": 4421, "time": 0.40, "cycle": true,
		"player_units": ["engineer", "engineer", "engineer", "engineer", "ranger", "ranger", "raptor", "raptor", "dilophosaurus"],
		"enemy_buildings": [["poacher_camp", Vector2i(48, 13)], ["poacher_tower", Vector2i(44, 16)], ["poacher_tower", Vector2i(51, 18)]],
		"enemy_units": ["trapper", "trapper", "trapper", "jeep", "jeep"],
		"enemy_res": {"dna": 400, "supplies": 600},
		"objectives": [{"type": "kill", "id": "jeep", "count": 8, "text": "Destroy poacher jeeps"}],
		"lose_no_engineers": true,
		"ai": {"waves": true, "first_wave": 70.0, "interval": 45.0, "min_wave": 2, "mix": ["jeep"], "target": "gatherers", "income": 1.4},
	},
	{
		"id": "m5", "name": "5. Poacher HQ",
		"briefing": "We've found their headquarters. It's heavily guarded, with sniper towers and a standing army. " +
			"Build up, hatch your strongest dinosaurs and end the poaching for good.",
		"seed": 5531, "time": 0.55, "cycle": true,
		"player_res": {"dna": 350, "supplies": 450},
		"enemy_buildings": [["poacher_camp", Vector2i(48, 13)], ["poacher_tower", Vector2i(44, 16)], ["poacher_tower", Vector2i(51, 18)],
			["poacher_tower", Vector2i(44, 11)], ["poacher_tower", Vector2i(52, 10)]],
		"enemy_units": ["trapper", "trapper", "trapper", "hunter", "hunter", "hunter", "hunter", "hunter", "jeep", "jeep"],
		"enemy_res": {"dna": 500, "supplies": 800},
		"objectives": [{"type": "destroy", "id": "poacher_camp", "text": "Destroy the Poacher HQ"}],
		"ai": {"waves": true, "first_wave": 150.0, "interval": 75.0, "min_wave": 4, "income": 1.4},
	},
]


static func get_mission(id: String) -> Dictionary:
	for m in CAMPAIGN:
		if m["id"] == id:
			return m
	return SKIRMISH


static func index_of(id: String) -> int:
	for i in CAMPAIGN.size():
		if CAMPAIGN[i]["id"] == id:
			return i
	return -1


static func next_id(id: String) -> String:
	var i := index_of(id)
	if i >= 0 and i + 1 < CAMPAIGN.size():
		return CAMPAIGN[i + 1]["id"]
	return ""
