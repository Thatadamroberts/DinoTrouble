extends Node
## Audio (autoload "Audio"): mixer buses, positional sound effects with
## random variations, the music state machine (menu / explore / combat with
## crossfades) and ambience that follows the day/night cycle and the coast.

const BUSES := ["Music", "SFX", "Ambience", "UI"]
const VOICES := 24
const MAX_PER_SOUND := 4
const COOLDOWN := 0.045
const MAX_VARIANTS := 8
const FADE_TIME := 2.5
const COMBAT_WINDOW := 4.0
const COMBAT_HOLD := 10.0
const ALIASES := {"bite": "bite_small", "roar": "trex_roar", "select": "ui_click"}
const MUSIC := {
	"menu": "res://assets/music/menu_theme.wav",
	"explore": "res://assets/music/explore.wav",
	"combat": "res://assets/music/combat.wav",
}
const AMBIENCE := {
	"day": "res://assets/ambience/jungle_day.wav",
	"night": "res://assets/ambience/jungle_night.wav",
	"surf": "res://assets/ambience/surf.wav",
}

var variants := {}  # sound name -> Array of streams
var last_variant := {}
var last_time := {}
var playing := {}  # player -> sound name
var pool: Array = []
var next_voice := 0
var ui_players: Array = []
var next_ui := 0

var music_players: Array = []
var music_main := 0
var music_state := ""
var fade := 1.0  # 0..1 progress of the current crossfade
var duck := 1.0
var duck_target := 1.0

var amb_players := {}
var amb_level := {"day": 0.0, "night": 0.0, "surf": 0.0}
var amb_t := 0.0

var world = null
var combat_pings: Array = []
var last_combat := -100.0
var clock := 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_buses()
	for i in VOICES:
		var p := AudioStreamPlayer2D.new()
		p.bus = "SFX"
		p.max_distance = 1700.0
		p.attenuation = 1.2
		add_child(p)
		pool.append(p)
	for i in 3:
		var u := AudioStreamPlayer.new()
		u.bus = "UI"
		add_child(u)
		ui_players.append(u)
	for i in 2:
		var m := AudioStreamPlayer.new()
		m.bus = "Music"
		m.volume_db = -80.0
		add_child(m)
		music_players.append(m)
	for k in AMBIENCE.keys():
		var a := AudioStreamPlayer.new()
		a.bus = "Ambience"
		a.volume_db = -80.0
		a.stream = loop_stream(AMBIENCE[k])
		add_child(a)
		amb_players[k] = a


func _setup_buses() -> void:
	for b in BUSES:
		if AudioServer.get_bus_index(b) == -1:
			AudioServer.add_bus()
			var i := AudioServer.bus_count - 1
			AudioServer.set_bus_name(i, b)
			AudioServer.set_bus_send(i, "Master")
	var sfx := AudioServer.get_bus_index("SFX")
	if AudioServer.get_bus_effect_count(sfx) == 0:
		var rv := AudioEffectReverb.new()
		rv.room_size = 0.35
		rv.damping = 0.6
		rv.wet = 0.1
		rv.dry = 1.0
		AudioServer.add_bus_effect(sfx, rv)


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------
## Loads a WAV and makes it loop over its whole length.
func loop_stream(path: String) -> AudioStream:
	if not ResourceLoader.exists(path):
		return null
	var s = load(path)
	if s is AudioStreamWAV:
		s = s.duplicate()
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)
	return s


func _variants(sound: String) -> Array:
	if not variants.has(sound):
		var arr: Array = []
		for i in MAX_VARIANTS:
			var p := "res://assets/sfx/%s_%d.wav" % [sound, i]
			if not ResourceLoader.exists(p):
				break
			arr.append(load(p))
		variants[sound] = arr
	return variants[sound]


func has_sound(sound: String) -> bool:
	return not _variants(ALIASES.get(sound, sound)).is_empty()


func _pick(sound: String) -> AudioStream:
	var arr := _variants(sound)
	if arr.is_empty():
		return null
	var i := randi() % arr.size()
	if arr.size() > 1 and i == int(last_variant.get(sound, -1)):
		i = (i + 1) % arr.size()
	last_variant[sound] = i
	return arr[i]


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------
func play(sound: String, pos: Vector2, db: float = 0.0, pitch: float = 1.0) -> void:
	sound = ALIASES.get(sound, sound)
	if clock - float(last_time.get(sound, -1.0)) < COOLDOWN:
		return
	if world != null and world.camera != null and not world.is_on_screen(pos, 500.0):
		return
	var count := 0
	for p in playing.keys():
		if playing[p] == sound and p.playing:
			count += 1
	if count >= MAX_PER_SOUND:
		return
	var stream := _pick(sound)
	if stream == null:
		return
	last_time[sound] = clock
	var player: AudioStreamPlayer2D = pool[next_voice]
	next_voice = (next_voice + 1) % pool.size()
	player.stream = stream
	player.global_position = pos
	player.volume_db = db
	player.pitch_scale = pitch * randf_range(0.94, 1.06)
	player.play()
	playing[player] = sound


func ui(sound: String, db: float = 0.0) -> void:
	sound = ALIASES.get(sound, sound)
	var stream := _pick(sound)
	if stream == null:
		return
	var p: AudioStreamPlayer = ui_players[next_ui]
	next_ui = (next_ui + 1) % ui_players.size()
	p.stream = stream
	p.volume_db = db
	p.pitch_scale = randf_range(0.97, 1.03)
	p.play()


## Victory / defeat jingle: the music dips while it plays.
func stinger(sound: String) -> void:
	duck_target = 0.15
	ui(sound)
	get_tree().create_timer(6.0, true, false, true).timeout.connect(func(): duck_target = 1.0)


# ---------------------------------------------------------------------------
# Music
# ---------------------------------------------------------------------------
func set_music(state: String) -> void:
	if state == music_state:
		return
	music_state = state
	var incoming: AudioStreamPlayer = music_players[1 - music_main]
	music_main = 1 - music_main
	if MUSIC.has(state):
		incoming.stream = loop_stream(MUSIC[state])
		incoming.volume_db = -80.0
		incoming.play()
	else:
		incoming.stop()
	fade = 0.0


## Called when fighting happens near the player; sustained fighting
## switches to the combat track.
func combat_ping() -> void:
	combat_pings.append(clock)
	last_combat = clock


func attach_world(w) -> void:
	world = w
	combat_pings.clear()
	last_combat = -100.0
	duck_target = 1.0
	set_music("explore")


func detach_world(w) -> void:
	if world == w:
		world = null


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
func _process(delta: float) -> void:
	clock += delta
	# music crossfade (equal power) and ducking
	duck = move_toward(duck, duck_target, delta * 0.8)
	if fade < 1.0:
		fade = minf(1.0, fade + delta / FADE_TIME)
	var a: AudioStreamPlayer = music_players[music_main]
	var b: AudioStreamPlayer = music_players[1 - music_main]
	a.volume_db = linear_to_db(maxf(sin(fade * PI / 2.0) * duck, 0.0001))
	b.volume_db = linear_to_db(maxf(cos(fade * PI / 2.0) * duck, 0.0001))
	if fade >= 1.0 and b.playing:
		b.stop()
	# combat detection
	if world != null and not GameState.over:
		combat_pings = combat_pings.filter(func(t): return clock - t < COMBAT_WINDOW)
		if combat_pings.size() >= 2 and music_state != "combat":
			set_music("combat")
		elif music_state == "combat" and clock - last_combat > COMBAT_HOLD:
			combat_pings.clear()  # stale pings must not flip straight back to combat
			set_music("explore")
	# ambience
	amb_t -= delta
	if amb_t <= 0.0:
		amb_t = 0.25
		_update_ambience()


func _update_ambience() -> void:
	var target := {"day": 0.0, "night": 0.0, "surf": 0.0}
	if world != null and world.camera != null and world.map != null:
		var n: float = GameState.night()
		target["day"] = (1.0 - n) * 0.85
		target["night"] = n * 0.9
		var view: Rect2 = world.view_rect()
		var water := 0
		for iy in 4:
			for ix in 4:
				var p := view.position + view.size * Vector2((ix + 0.5) / 4.0, (iy + 0.5) / 4.0)
				if world.map.get_tile(Iso.world_to_tile(p)) == 0:
					water += 1
		target["surf"] = clampf(water / 16.0 * 1.4, 0.0, 1.0) * 0.9
	for k in amb_players.keys():
		amb_level[k] = move_toward(float(amb_level[k]), float(target[k]), 0.08)
		var pl: AudioStreamPlayer = amb_players[k]
		if amb_level[k] > 0.001:
			if not pl.playing and pl.stream != null:
				pl.play()
			pl.volume_db = linear_to_db(float(amb_level[k]))
		elif pl.playing:
			pl.stop()
