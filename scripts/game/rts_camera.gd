extends Camera2D
## RTS camera: arrow keys, screen-edge scrolling, middle-drag pan, wheel zoom.

const EDGE := 8.0
const PAN_SPEED := 900.0

var world = null
var mouse_in := false
var dragging := false
var bounds := Rect2()


func setup(w) -> void:
	world = w
	var s: float = w.map.size
	bounds = Rect2(-s * 32.0, -32.0, s * 64.0, s * 32.0 + 64.0)


func _ready() -> void:
	make_current()


func _process(delta: float) -> void:
	var dir := Vector2.ZERO
	if Input.is_key_pressed(KEY_LEFT):
		dir.x -= 1
	if Input.is_key_pressed(KEY_RIGHT):
		dir.x += 1
	if Input.is_key_pressed(KEY_UP):
		dir.y -= 1
	if Input.is_key_pressed(KEY_DOWN):
		dir.y += 1
	if mouse_in and not dragging and bool(SaveSystem.settings["edge_scroll"]) and DisplayServer.window_is_focused():
		var vp := get_viewport()
		var m := vp.get_mouse_position()
		var sz := vp.get_visible_rect().size
		if m.x >= 0 and m.y >= 0 and m.x <= sz.x and m.y <= sz.y:
			if m.x < EDGE:
				dir.x -= 1
			elif m.x > sz.x - EDGE:
				dir.x += 1
			if m.y < EDGE:
				dir.y -= 1
			elif m.y > sz.y - EDGE:
				dir.y += 1
	if dir != Vector2.ZERO:
		position += dir.normalized() * PAN_SPEED * float(SaveSystem.settings["scroll_speed"]) * delta / zoom.x
		_clamp()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		mouse_in = true
		if dragging:
			position -= event.relative / zoom.x
			_clamp()
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_MIDDLE:
			dragging = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom_by(1.1)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom_by(1.0 / 1.1)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_MOUSE_EXIT or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		mouse_in = false


func _zoom_by(f: float) -> void:
	var z := clampf(zoom.x * f, 0.5, 2.0)
	zoom = Vector2(z, z)


func focus_on(p: Vector2) -> void:
	position = p
	_clamp()


func _clamp() -> void:
	position.x = clampf(position.x, bounds.position.x, bounds.end.x)
	position.y = clampf(position.y, bounds.position.y, bounds.end.y)
