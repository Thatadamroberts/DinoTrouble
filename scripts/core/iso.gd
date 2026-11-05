extends Node
## Isometric helpers (autoload "Iso").
## Tiles are 64x32 diamonds. Grid (x, y) maps to world space so that the
## tile centre of (0, 0) sits at the world origin.

const HALF_W := 32.0
const HALF_H := 16.0
## Iso distance of one grid step (see idist()).
const TILE_DIST := 45.25


## Grid coordinate (Vector2 or Vector2i, may be fractional) -> world position.
func tile_to_world(t) -> Vector2:
	return Vector2((t.x - t.y) * HALF_W, (t.x + t.y) * HALF_H)


## World position -> fractional grid coordinate.
func world_to_grid(p: Vector2) -> Vector2:
	var fx: float = p.x / HALF_W
	var fy: float = p.y / HALF_H
	return Vector2((fy + fx) * 0.5, (fy - fx) * 0.5)


## World position -> the tile that contains it.
func world_to_tile(p: Vector2) -> Vector2i:
	var g: Vector2 = world_to_grid(p)
	return Vector2i(roundi(g.x), roundi(g.y))


## Distance in "ground" terms: vertical screen distance counts double so
## ranges and sight form ellipses that match the isometric ground plane.
func idist(a: Vector2, b: Vector2) -> float:
	return Vector2(b.x - a.x, (b.y - a.y) * 2.0).length()
