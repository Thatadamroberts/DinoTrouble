extends RefCounted
## Shared look for menus and panels.

const PANEL_BG := Color(0.12, 0.1, 0.07, 0.96)
const PANEL_BORDER := Color(0.55, 0.45, 0.25)
const TEXT := Color(0.95, 0.9, 0.75)
const DIM := Color(0.75, 0.72, 0.62)


static func panel_style(margin: int = 16) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = PANEL_BG
	sb.border_color = PANEL_BORDER
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(3)
	sb.set_content_margin_all(margin)
	return sb


static func label(text: String, font_size: int = 16, color: Color = TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 3)
	return l


static func button(text: String, width: float = 260.0) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(width, 38)
	b.add_theme_font_size_override("font_size", 18)
	b.pressed.connect(func(): Audio.ui("ui_click"))
	return b
