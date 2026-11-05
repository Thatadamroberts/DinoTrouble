// Screen-space vignette with a warm tint toward the corners.
shader_type canvas_item;

uniform float strength = 0.42;

void fragment() {
	vec2 uv = UV - 0.5;
	float v = smoothstep(0.32, 0.85, length(uv * vec2(1.0, 0.9)));
	COLOR = vec4(0.06, 0.03, 0.0, v * strength);
}
