// Gentle wind sway for foliage: the top of the sprite shifts by whole
// pixels while the base stays planted.
shader_type canvas_item;

uniform float amount = 1.5;
uniform float speed = 1.2;

void vertex() {
	float top = 1.0 - UV.y;
	float phase = (MODEL_MATRIX[3].x * 0.031 + MODEL_MATRIX[3].y * 0.047);
	VERTEX.x += round(sin(TIME * speed + phase) * amount * top);
}
