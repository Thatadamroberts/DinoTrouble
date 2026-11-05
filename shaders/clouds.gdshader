// Slowly drifting cloud shadows with dithered edges.
shader_type canvas_item;
render_mode unshaded;

uniform sampler2D tex_noise : filter_linear, repeat_enable;
uniform float strength = 0.2;
uniform vec2 wind = vec2(0.010, 0.004);

varying vec2 world;

const float BAYER[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);

void vertex() {
	world = VERTEX;
}

void fragment() {
	vec2 px = floor(world);
	vec2 p = px / vec2(2600.0, 1300.0) + wind * TIME;
	float n = texture(tex_noise, p).r * 0.65 + texture(tex_noise, p * 2.7 + vec2(0.3, 0.7)).r * 0.35;
	float cover = smoothstep(0.55, 0.66, n);
	int x = int(mod(px.x, 4.0));
	int y = int(mod(px.y, 4.0));
	float b = (BAYER[y * 4 + x] + 0.5) / 16.0;
	COLOR = vec4(0.02, 0.05, 0.10, step(b, cover) * strength);
}
