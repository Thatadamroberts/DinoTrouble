// Terrain renderer: blends terrain types per pixel with dithered, organic
// edges, animates water (depth bands, waves, shore foam), darkens wet sand
// and applies soft ambient occlusion around trees and buildings.
shader_type canvas_item;
render_mode unshaded;

// 1 texel per tile. a = (water, sand, grass, jungle), b = (dirt, rock, depth, ao)
uniform sampler2D splat_a : filter_linear, repeat_disable;
uniform sampler2D splat_b : filter_linear, repeat_disable;
uniform sampler2D tex_grass : filter_nearest, repeat_enable;
uniform sampler2D tex_jungle : filter_nearest, repeat_enable;
uniform sampler2D tex_sand : filter_nearest, repeat_enable;
uniform sampler2D tex_dirt : filter_nearest, repeat_enable;
uniform sampler2D tex_rock : filter_nearest, repeat_enable;
uniform sampler2D tex_noise : filter_linear, repeat_enable;
uniform float map_size = 64.0;

varying vec2 world;

const float BAYER[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);

float bayer(vec2 p) {
	int x = int(mod(p.x, 4.0));
	int y = int(mod(p.y, 4.0));
	return (BAYER[y * 4 + x] + 0.5) / 16.0;
}

float nz(vec2 p) {
	return texture(tex_noise, p).r;
}

vec3 water_color(float depth, vec2 px, float b) {
	// noise breaks up the tile-shaped steps of the depth field
	float d = clamp(depth + (nz(px / 210.0 + vec2(0.21, 0.53)) - 0.5) * 0.45, 0.0, 1.0) * 3.0 + (b - 0.5) * 0.6;
	vec3 c0 = vec3(0.30, 0.66, 0.66);
	vec3 c1 = vec3(0.18, 0.50, 0.60);
	vec3 c2 = vec3(0.12, 0.36, 0.52);
	vec3 c3 = vec3(0.09, 0.26, 0.42);
	vec3 col = d < 1.0 ? c0 : (d < 2.0 ? c1 : (d < 2.8 ? c2 : c3));
	// drifting wave highlights
	float w = sin(px.x * 0.09 + px.y * 0.21 + TIME * 1.4 + nz(px / 260.0) * 9.0);
	float w2 = sin(px.x * 0.05 - px.y * 0.17 - TIME * 0.9 + nz(px / 380.0 + 0.4) * 7.0);
	float patch = nz(px / 520.0 + vec2(TIME * 0.004, 0.0));
	if ((w > 0.99 && patch > 0.5) || (w2 > 0.99 && depth > 0.3)) {
		col = mix(col, vec3(0.62, 0.86, 0.90), 0.75);
	}
	return col;
}

void vertex() {
	world = VERTEX;
}

void fragment() {
	vec2 px = floor(world) + 0.5;
	vec2 grid = vec2((px.y / 16.0 + px.x / 32.0) * 0.5, (px.y / 16.0 - px.x / 32.0) * 0.5);
	vec2 suv = (grid + 0.5) / map_size;
	vec4 a = texture(splat_a, suv);
	vec4 b = texture(splat_b, suv);
	float bd = bayer(floor(world));

	// per-terrain noise so neighbouring types interlock irregularly
	float w[6];
	w[0] = a.r + (nz(px / 170.0) - 0.5) * 0.8;
	w[1] = a.g + (nz(px / 130.0 + vec2(0.31, 0.17)) - 0.5) * 0.8;
	w[2] = a.b + (nz(px / 150.0 + vec2(0.63, 0.41)) - 0.5) * 0.8;
	w[3] = a.a + (nz(px / 120.0 + vec2(0.12, 0.77)) - 0.5) * 0.85;
	w[4] = b.r + (nz(px / 140.0 + vec2(0.88, 0.29)) - 0.5) * 0.8;
	w[5] = b.g + (nz(px / 160.0 + vec2(0.47, 0.93)) - 0.5) * 0.8;
	int best = 0;
	int second = 1;
	if (w[1] > w[0]) { best = 1; second = 0; }
	for (int i = 2; i < 6; i++) {
		if (w[i] > w[best]) { second = best; best = i; }
		else if (w[i] > w[second]) { second = i; }
	}
	float margin = w[best] - w[second];

	vec2 tuv = px / 128.0;
	vec3 col;
	if (best == 0) {
		col = water_color(b.b, px, bd);
		// animated foam along the shoreline
		float shore = 1.0 - smoothstep(0.0, 0.22, margin);
		float wave = 0.45 + 0.25 * sin(TIME * 1.8 + nz(px / 200.0) * 8.0);
		if (second != 0 && shore > wave + (bd - 0.5) * 0.25) {
			col = mix(col, vec3(0.90, 0.96, 0.94), 0.85);
		}
	} else if (best == 1) {
		col = texture(tex_sand, tuv).rgb;
		if (second == 0 && margin < 0.2 + (bd - 0.5) * 0.08) {
			col *= 0.78; // wet sand
		}
	} else if (best == 2) {
		col = texture(tex_grass, tuv).rgb;
	} else if (best == 3) {
		col = texture(tex_jungle, tuv).rgb;
	} else if (best == 4) {
		col = texture(tex_dirt, tuv).rgb;
	} else {
		col = texture(tex_rock, tuv).rgb;
	}
	// darker pixel seam where two land types meet
	if (best != 0 && second != 0 && margin < 0.035) {
		col *= 0.8;
	}
	// ambient occlusion + broad light variation, posterised with dithering
	float shade_v = 1.0 - b.a * 0.45;
	shade_v *= 0.93 + 0.14 * nz(px / 2600.0 + vec2(0.5, 0.2));
	col *= shade_v;
	col = floor(col * 40.0 + bd) / 40.0;
	COLOR = vec4(col, 1.0);
}
