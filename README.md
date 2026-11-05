# DinoTrouble

An isometric real-time strategy game about dinosaurs, in the spirit of the
classic late-90s dino RTS games. You run a dinosaur reserve on a jungle island.
When a poacher company lands, you hatch dinosaurs, lead your rangers and
engineers, and drive the poachers off the island.

Built with **Godot 4.3** (GDScript). A single project exports both a
**Windows .exe** and a **browser (HTML5)** build.

## Playing

### Download a build
Every push runs the **Build DinoTrouble** GitHub Actions workflow. Open the
latest run under the repo's **Actions** tab and download:

- `DinoTrouble-windows`: unzip it and run `DinoTrouble.exe`.
- `DinoTrouble-web`: unzip it and serve the folder with any static web server,
  for example `python3 -m http.server` inside it, then open
  `http://localhost:8000`. It also works when uploaded to itch.io as an HTML5
  game, because the web export is single-threaded and needs no special
  headers.

### Play in the browser
Pushes to the default branch publish the web build to GitHub Pages:
**https://thatadamroberts.github.io/DinoTrouble/**. This needs a one-time
setup: under **Settings → Pages → Build and deployment**, set **Source** to
**GitHub Actions**.

### Run from source
1. Install [Godot 4.3](https://godotengine.org/download/archive/4.3-stable/).
2. Open `project.godot` in the editor and press **F5**.

## Game modes

- **Campaign:** five missions, each with a briefing and objectives. Finishing
  one unlocks the next, and progress is remembered.
  1. *A New Reserve*: tutorial. Gather DNA, hatch dinosaurs, build a
     watchtower and tame a wild dinosaur.
  2. *Stolen Eggs*: a night raid on a poacher outpost to break open the egg
     cages. Each cage frees two raptor hatchlings.
  3. *Hold the Line*: survive six minutes of poacher attack waves until the
     supply boat arrives.
  4. *Jeep Raids*: poacher jeeps hunt your engineers. Destroy 8 jeeps without
     losing every engineer.
  5. *Poacher HQ*: destroy the heavily defended poacher headquarters.
- **Skirmish:** free play on a random island. Destroy the poacher camp.

**Saving:** you can save from the pause menu (Esc) into 3 slots, and the game
autosaves every 2 minutes. Load from the title screen or the pause menu. Saves,
campaign progress and settings are stored in Godot's `user://` folder on
desktop and in browser storage on the web.

**Settings:** volume, camera scroll speed, edge scrolling, fullscreen,
dinosaur hunger and difficulty.

**Day and night:** a full day lasts about 6 minutes. At night the world
darkens, windows, lamps, campfires and jeep headlights glow, fireflies come
out, and every unit's sight drops by up to 25%.

## How to play

**Goal:** destroy the Poacher Camp in the east. You lose if both your Ranger
Station and Hatchery are destroyed.

| Resource | Source | Used for |
|---|---|---|
| **DNA** | Amber deposits (gathered by Engineers) | Hatching dinosaurs |
| **Supplies** | Supply caches (Engineers), plus a trickle at the Ranger Station | Humans, buildings, big dinosaurs |

**Your units**

| Unit | Where | Notes |
|---|---|---|
| Engineer | Ranger Station | Gathers, builds, repairs, tames wild dinosaurs |
| Ranger | Ranger Station | Cheap ranged rifle support |
| Raptor | Hatchery | Fast, cheap pack hunter |
| Dilophosaurus | Hatchery | Ranged venom spit that slows |
| Triceratops | Hatchery | Tank; charges, knocking back and stunning |
| T. rex | Hatchery | Splash bite; its roar makes humans flee |

**Buildings (built by Engineers):** Watchtower (defence), Supply Depot (forward
drop-off), Hatchery.

**Dinosaur hunger:** dinosaurs get hungry and feed near a Hatchery. A starving
dinosaur goes feral, ignores orders and heads back to feed. Without a hatchery
it escapes into the jungle. You can turn hunger off in the menu.

**Taming:** right-click a wild dinosaur with Engineers to tame it. Predators
(raptors, dilophosaurus) must be wounded below half health first.

**The poachers:** Hunters (rifles), Trappers (nets that stun dinosaurs) and
Jeeps (fast raiders). They gather, build an army and send waves at your
Hatchery that grow over time.

### Controls

| Input | Action |
|---|---|
| Left-click / drag box | Select (Shift adds, double-click selects that type on screen) |
| Right-click | Move / attack / gather / build / tame (or set a building's rally point) |
| A, then click | Attack-move |
| S | Stop |
| Q W E R T | Command-card buttons (train, hatch, build) |
| Ctrl+1–9 / 1–9 | Assign / recall control group (double-tap to jump to it) |
| Delete | Cancel the last production order of the selected building |
| Space | Jump to your base |
| Arrow keys, screen edge, middle-drag | Scroll |
| Mouse wheel | Zoom |
| Esc | Pause menu |

## Project layout

```
project.godot, export_presets.cfg
scenes/                 menu.tscn, main.tscn, tests/smoke_test.tscn
scripts/core/           iso (math), defs (all balance data), game_state, map (terrain + A*)
scripts/game/           world, selection, camera, fog, ground, projectiles, fx, resources
scripts/units/unit.gd   unit state machine (move, attack, gather, build, tame, hunger, abilities)
scripts/buildings/      construction, production queues, towers
scripts/ai/             poacher AI
scripts/ui/             HUD, minimap, main menu
assets/sprites, assets/sfx   generated placeholder art & sound
tools/                  gen_sprites.py, gen_sounds.py (Pillow / stdlib)
```

Unit and building stats are all in `scripts/core/defs.gd`.

### Art and sound
All art is generated pixel art, drawn by code in `tools/`:

- `pixelkit.py` is a small pixel-art renderer. Shapes (ellipsoids, tapered
  limbs, textured iso faces) are lit by one sun from the upper left, then
  reduced to hand-picked colour ramps with ordered dithering. It adds belly
  counter-shading, patterns, coloured outlines and baked soft shadows.
- `units_art.py` has parametric rigs for each dinosaur, human and the jeep.
  A unit sheet has **13 columns × 2 rows**, all facing right. The columns are
  2 idle (breathing), 6 walk, 3 attack and 2 death frames. Row 0 is a 3/4
  front view (heading down-right) and row 1 a 3/4 back view (heading
  up-right). The game mirrors them for left-facing units.
- `world_art.py` draws the buildings, resources, foliage, and the seamless
  128 px terrain textures used by the ground shader.

In the game, `shaders/ground.gdshader` blends terrain types per pixel with
dithered edges, and animates the water's depth bands, waves and shore foam.
Other shaders add drifting cloud shadows, foliage swaying in the wind and a
vignette, and a warm colour grade sits over the whole scene.

To replace any of it, drop in a PNG with the same size and layout.

### Audio
All audio is synthesised by `tools/gen_sounds.py`, using a small numpy DSP kit
(`tools/audiokit.py`) and synth instruments (`tools/instruments.py`):

- **Sound effects** (`assets/sfx/<name>_<n>.wav`, 3–4 variations each):
  - Weapons: rifles, the jeep's machine gun, tower shots, venom spit and nets.
  - Creatures: a call for each species, small and large bites, heavy
    footsteps, deaths and hits.
  - World: hatching, building, gathering, collapses, explosions, a fire loop
    and splashes.
  - Interface: UI clicks, an objective chime, a wave-alert drum hit, and
    victory and defeat jingles.
- **Music** (`assets/music/`): looping adventure tracks built from tribal
  drums, marimba, pads and a horn lead. There's a menu theme, an exploration
  track and a combat track. The game crossfades to combat music when
  fighting starts near you and back once it's quiet.
- **Ambience** (`assets/ambience/`): jungle by day (birds, insects, wind),
  night (crickets, frogs) and surf. It follows the day/night cycle and how
  much coast is on screen.

The `Audio` autoload (`scripts/core/audio.gd`) mixes everything on separate
Music, Effects, Ambience and UI channels, each with its own volume slider in
Settings. Since the sounds are generated rather than recorded,
`tools/check_audio.py` checks for clipping, silence, loop seams and
near-identical variations, and `tools/audio_preview.py` draws spectrograms to
look at.

```bash
pip install pillow numpy
python3 tools/gen_sprites.py
python3 tools/gen_sounds.py
python3 tools/check_audio.py
```

CI also renders the game with a real (software) GPU and uploads
`DinoTrouble-screenshots`, which catches shader errors.

### Smoke test
```bash
godot --headless --import --path .
godot --headless --fixed-fps 60 --path . res://scenes/tests/smoke_test.tscn
```
The test boots a match with a fixed seed. It moves, gathers, hatches, builds,
fights, tames and starves units, simulates about four minutes of AI play, then
checks the victory condition. It exits non-zero on failure, and CI runs it
before exporting.
