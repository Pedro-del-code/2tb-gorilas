"""
GORILLAS Web - Flask Backend
Converted from QBasic Gorillas 2.2 to Python/Flask for Render deployment.
Physics engine and game state management live here.
"""

from flask import Flask, jsonify, request, send_from_directory
import math
import random
import os

app = Flask(__name__, static_folder="static", static_url_path="")


# ─────────────────────────────────────────────
#  PHYSICS CONSTANTS  (mirrors the BASIC logic)
# ─────────────────────────────────────────────
CANVAS_W = 800
CANVAS_H = 500
GROUND_Y = CANVAS_H - 20       # bottom horizon line
DEFAULT_GRAVITY = 17
SUN_X = CANVAS_W // 2
SUN_Y = 60


# ─────────────────────────────────────────────
#  CITY GENERATOR  (MakeCityScape)
# ─────────────────────────────────────────────
def make_cityscape():
    """Generate random building data. Returns list of building dicts."""
    buildings = []
    x = 0
    slope_type = random.randint(1, 6)   # 1=up, 2=down, 3-5=V, 6=invV

    if slope_type == 2:
        new_ht = 260
    elif slope_type == 6:
        new_ht = 260
    else:
        new_ht = 60

    ht_inc = 20
    def_bwidth = 74
    random_height = 240
    min_building_h = 60

    colors = ["#4a6fa5", "#6b8cba", "#3d5a8a", "#5c7aaa", "#7b9cc4",
              "#8fafd0", "#2d4a7a", "#556b9f"]

    while x < CANVAS_W:
        if slope_type == 1:
            new_ht = min(new_ht + ht_inc, GROUND_Y - 80)
        elif slope_type == 2:
            new_ht = max(new_ht - ht_inc, min_building_h)
        elif slope_type in (3, 4, 5):
            if x > CANVAS_W // 2:
                new_ht = max(new_ht - ht_inc * 2, min_building_h)
            else:
                new_ht = min(new_ht + ht_inc * 2, GROUND_Y - 80)
        elif slope_type == 6:
            if x > CANVAS_W // 2:
                new_ht = min(new_ht + ht_inc * 2, GROUND_Y - 80)
            else:
                new_ht = max(new_ht - ht_inc * 2, min_building_h)

        bwidth = random.randint(def_bwidth, def_bwidth * 2)
        if x + bwidth > CANVAS_W:
            bwidth = CANVAS_W - x

        bheight = random.randint(min_building_h, new_ht + random_height)
        bheight = max(bheight, min_building_h)
        bheight = min(bheight, GROUND_Y - 80)

        color = random.choice(colors)

        # Windows
        windows = []
        ww, wh = 6, 10
        wdh, wdv = 16, 22
        col = x + 8
        while col + ww < x + bwidth - 4:
            row = GROUND_Y - bheight + 12
            while row + wh < GROUND_Y - 8:
                lit = random.random() > 0.3
                windows.append({
                    "x": col, "y": row, "w": ww, "h": wh,
                    "lit": lit
                })
                row += wdv
            col += wdh

        buildings.append({
            "x": x,
            "y": GROUND_Y - bheight,
            "w": bwidth,
            "h": bheight,
            "color": color,
            "windows": windows
        })
        x += bwidth + 2

    return buildings


# ─────────────────────────────────────────────
#  GORILLA PLACEMENT  (PlaceGorillas)
# ─────────────────────────────────────────────
def place_gorillas(buildings):
    """Returns (gorilla1_pos, gorilla2_pos) as {x,y} dicts."""
    gorillas = []
    # Player 1: 2nd or 3rd building from left
    b1 = buildings[random.randint(1, 2)]
    # Player 2: 2nd or 3rd building from right
    b2 = buildings[len(buildings) - random.randint(2, 3)]

    for b in (b1, b2):
        gx = b["x"] + b["w"] // 2 - 15
        gy = b["y"] - 35
        gorillas.append({"x": gx, "y": gy})

    return gorillas


# ─────────────────────────────────────────────
#  TRAJECTORY CALCULATION  (PlotShot physics)
# ─────────────────────────────────────────────
def calculate_trajectory(
    start_x, start_y, angle_deg, velocity, player_num,
    buildings, gorilla_positions, gravity, wind
):
    """
    Returns a list of {x, y} positions for the banana arc,
    plus hit_result: None | 'gorilla1' | 'gorilla2' | 'building'
    """
    pi = math.pi

    # Player 2 fires leftward: mirror the angle
    if player_num == 2:
        angle_deg = 180 - angle_deg

    angle_rad = angle_deg * pi / 180
    vx = math.cos(angle_rad) * velocity
    vy = math.sin(angle_rad) * velocity

    # Offset start so banana comes from gorilla's hand
    sx = start_x + (20 if player_num == 1 else -5)
    sy = start_y + 5

    points = []
    t = 0.0
    dt = 0.12
    hit_result = None
    hit_x = None
    hit_y = None

    max_steps = 1000
    steps = 0

    while steps < max_steps:
        steps += 1
        t += dt
        x = sx + vx * t + 0.5 * (wind / 5) * t ** 2
        # Y grows downward on canvas; physics uses up-positive, so flip
        y = sy - (vy * t - 0.5 * gravity * t ** 2) * (CANVAS_H / 350)

        points.append({"x": round(x, 2), "y": round(y, 2)})

        # Off screen left/right
        if x < -30 or x > CANVAS_W + 30:
            break

        # Hit the ground
        if y >= GROUND_Y:
            break

        # Check gorilla hits (generous 28×36 bounding box)
        for idx, g in enumerate(gorilla_positions):
            if (g["x"] - 5 <= x <= g["x"] + 30 and
                    g["y"] - 5 <= y <= g["y"] + 36):
                hit_result = f"gorilla{idx + 1}"
                hit_x = round(x, 2)
                hit_y = round(y, 2)
                break

        if hit_result:
            break

        # Check building hits
        for b in buildings:
            if (b["x"] <= x <= b["x"] + b["w"] and
                    b["y"] <= y <= GROUND_Y):
                hit_result = "building"
                hit_x = round(x, 2)
                hit_y = round(y, 2)
                break

        if hit_result:
            break

    return {
        "points": points,
        "hit": hit_result,
        "hit_x": hit_x,
        "hit_y": hit_y
    }


# ─────────────────────────────────────────────
#  MISS MESSAGES  (FailureMessage / DoMessage)
# ─────────────────────────────────────────────
MISS_MESSAGES = [
    "That went a wee bit far, didn't it?",
    "It seems you overdid that a little.",
    "I think you need glasses.",
    "Hmmm...that wasn't good.",
    "Now that was feeble.",
    "You can do better than that!",
    "A little nearer and you might stand a chance.",
    '"Hello? I\'m over here!"',
    "Whoa! Go easy with it!",
    "You weren't supposed to put it into orbit.",
    "WHAT? That went MILES OFF!",
    "WHAT ARE YOU PLAYING AT?",
    "You're not supposed to throw it that way.",
    "Don't throw it that way!",
    "Temper temper…",
    "Nope. That was too far off.",
]

WIN_MESSAGES = [
    "BULLSEYE! 🍌",
    "DIRECT HIT! 💥",
    "BANANA JUSTICE! 🦍",
    "BOOM GOES THE DYNAMITE! 💣",
    "NOW THAT'S HOW YOU DO IT! 🎯",
]


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/new_game", methods=["POST"])
def new_game():
    """Generate a fresh game board: buildings, gorilla positions, wind."""
    data = request.get_json(force=True, silent=True) or {}
    gravity = int(data.get("gravity", DEFAULT_GRAVITY))
    gravity = max(1, min(gravity, 99))

    buildings = make_cityscape()
    gorillas = place_gorillas(buildings)
    wind = random.randint(-10, 10)
    if random.random() < 0.33:
        wind = wind + random.choice([-1, 1]) * random.randint(0, 10)
    wind = max(-20, min(20, wind))

    return jsonify({
        "buildings": buildings,
        "gorillas": gorillas,
        "wind": wind,
        "gravity": gravity,
        "canvas_w": CANVAS_W,
        "canvas_h": CANVAS_H,
        "ground_y": GROUND_Y,
        "sun": {"x": SUN_X, "y": SUN_Y},
    })


@app.route("/api/throw", methods=["POST"])
def throw():
    """Compute the banana trajectory for a given throw."""
    data = request.get_json(force=True)

    result = calculate_trajectory(
        start_x=float(data["gorilla_x"]),
        start_y=float(data["gorilla_y"]),
        angle_deg=float(data["angle"]),
        velocity=float(data["velocity"]),
        player_num=int(data["player"]),
        buildings=data["buildings"],
        gorilla_positions=data["gorillas"],
        gravity=float(data.get("gravity", DEFAULT_GRAVITY)),
        wind=float(data.get("wind", 0)),
    )

    msg = ""
    if result["hit"] and "gorilla" in result["hit"]:
        msg = random.choice(WIN_MESSAGES)
    elif not result["hit"] or result["hit"] == "building":
        msg = random.choice(MISS_MESSAGES)

    result["message"] = msg
    return jsonify(result)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
