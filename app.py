"""
GORILLAS Web — Flask Backend
Física original do QBasic Gorillas + IA via Groq
"""

from flask import Flask, jsonify, request, send_from_directory
import math, random, os, json
from groq import Groq

app = Flask(__name__, static_folder="static", static_url_path="")

GROQ_CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# ─── FÍSICA ────────────────────────────────────────────────────────────────
CANVAS_W        = 800
CANVAS_H        = 500
GROUND_Y        = CANVAS_H - 20
DEFAULT_GRAVITY = 17
SUN_X = CANVAS_W // 2
SUN_Y = 60
SCALE_Y         = CANVAS_H / 350   # mesma escala usada em calculate_trajectory
DT              = 0.12              # passo de tempo idêntico ao do frontend


# ─── CIDADE ────────────────────────────────────────────────────────────────
def make_cityscape():
    buildings = []
    x = 0
    slope_type = random.randint(1, 6)
    new_ht  = 260 if slope_type in (2, 6) else 60
    ht_inc  = 20
    def_bw  = 74
    rnd_ht  = 240
    min_h   = 60
    colors  = ["#4a6fa5","#6b8cba","#3d5a8a","#5c7aaa",
               "#7b9cc4","#8fafd0","#2d4a7a","#556b9f"]

    while x < CANVAS_W:
        if   slope_type == 1: new_ht = min(new_ht + ht_inc, GROUND_Y - 80)
        elif slope_type == 2: new_ht = max(new_ht - ht_inc, min_h)
        elif slope_type in (3, 4, 5):
            new_ht = (min(new_ht + ht_inc*2, GROUND_Y-80) if x < CANVAS_W//2
                      else max(new_ht - ht_inc*2, min_h))
        elif slope_type == 6:
            new_ht = (max(new_ht - ht_inc*2, min_h) if x < CANVAS_W//2
                      else min(new_ht + ht_inc*2, GROUND_Y-80))

        bw = random.randint(def_bw, def_bw * 2)
        if x + bw > CANVAS_W: bw = CANVAS_W - x
        bh = max(min_h, min(GROUND_Y-80, random.randint(min_h, new_ht + rnd_ht)))

        windows = []
        col = x + 8
        while col + 6 < x + bw - 4:
            row = GROUND_Y - bh + 12
            while row + 10 < GROUND_Y - 8:
                windows.append({
                    "x": col, "y": row, "w": 6, "h": 10,
                    "lit": random.random() > 0.3
                })
                row += 22
            col += 16

        buildings.append({
            "x": x, "y": GROUND_Y - bh, "w": bw, "h": bh,
            "color": random.choice(colors), "windows": windows
        })
        x += bw + 2
    return buildings


def place_gorillas(buildings):
    b1 = buildings[random.randint(1, 2)]
    b2 = buildings[len(buildings) - random.randint(2, 3)]
    return [{"x": b["x"] + b["w"]//2 - 15, "y": b["y"] - 35} for b in (b1, b2)]


# ─── FÍSICA DO PROJÉTIL ────────────────────────────────────────────────────
def calculate_trajectory(start_x, start_y, angle_deg, velocity, player_num,
                         buildings, gorilla_positions, gravity, wind):
    if player_num == 2:
        angle_deg = 180 - angle_deg
    rad = angle_deg * math.pi / 180
    vx  = math.cos(rad) * velocity
    vy  = math.sin(rad) * velocity
    sx  = start_x + (20 if player_num == 1 else -5)
    sy  = start_y + 5

    points, t, hit_result, hit_x, hit_y = [], 0.0, None, None, None

    for _ in range(1000):
        t += DT
        x = sx + vx*t + 0.5*(wind/5)*t**2
        y = sy - (vy*t - 0.5*gravity*t**2) * SCALE_Y
        points.append({"x": round(x, 2), "y": round(y, 2)})

        if x < -30 or x > CANVAS_W + 30: break
        if y >= GROUND_Y: break

        for idx, g in enumerate(gorilla_positions):
            if g["x"]-5 <= x <= g["x"]+30 and g["y"]-5 <= y <= g["y"]+36:
                hit_result, hit_x, hit_y = f"gorilla{idx+1}", round(x, 2), round(y, 2)
                break
        if hit_result: break

        for b in buildings:
            if b["x"] <= x <= b["x"]+b["w"] and b["y"] <= y <= GROUND_Y:
                hit_result, hit_x, hit_y = "building", round(x, 2), round(y, 2)
                break
        if hit_result: break

    return {"points": points, "hit": hit_result, "hit_x": hit_x, "hit_y": hit_y}


# ─── FALLBACK DE FÍSICA (usa EXATAMENTE a mesma física do calculate_trajectory) ──
def _sim_trajectory(sx, sy, angle_deg, velocity, wind, gravity):
    """Simula a trajetória para a direção original (sem espelhar)."""
    rad = angle_deg * math.pi / 180
    vx  = math.cos(rad) * velocity
    vy  = math.sin(rad) * velocity
    t   = 0.0
    for _ in range(1000):
        t  += DT
        x   = sx + vx*t + 0.5*(wind/5)*t**2
        y   = sy - (vy*t - 0.5*gravity*t**2) * SCALE_Y
        if x < -30 or x > CANVAS_W + 30 or y >= GROUND_Y:
            return x, y, True   # saiu fora
        yield x, y


def _fallback_aim(ai_pos, target_pos, wind, gravity, difficulty):
    """
    Busca exaustiva de ângulo usando a mesma equação física do backend.
    O jogador 2 lança para a esquerda; o backend já aplica (180 - angle),
    portanto buscamos o ângulo *antes* do espelhamento.
    """
    # Ponto de lançamento do gorila 2 (igual ao usado em calculate_trajectory p/ player=2)
    sx = ai_pos["x"] + (-5)   # player_num==2 → sx = start_x - 5
    sy = ai_pos["y"] + 5
    tx = target_pos["x"] + 15  # centro do gorila alvo
    ty = target_pos["y"] + 20

    dist = math.hypot(target_pos["x"] - ai_pos["x"], target_pos["y"] - ai_pos["y"])
    # Estima velocidade inicial proporcional à distância
    vel_base = max(50, min(190, dist * 0.55 + 20))

    best_angle  = 135
    best_dist   = float("inf")
    best_vel    = vel_base

    # Busca em grade de ângulo × velocidade
    for a in range(5, 176, 2):
        # O backend espelha: effective_angle = 180 - a para player 2
        eff_angle = 180 - a
        for vel_mult in (0.85, 1.0, 1.15):
            vel = vel_base * vel_mult
            rad = eff_angle * math.pi / 180
            vx  = math.cos(rad) * vel
            vy  = math.sin(rad) * vel
            t   = 0.0
            for _ in range(1000):
                t  += DT
                x   = sx + vx*t + 0.5*(wind/5)*t**2
                y   = sy - (vy*t - 0.5*gravity*t**2) * SCALE_Y
                if x < -30 or x > CANVAS_W + 30 or y >= GROUND_Y:
                    break
                d = math.hypot(x - tx, y - ty)
                if d < best_dist:
                    best_dist  = d
                    best_angle = a
                    best_vel   = vel

    errors = {"easy": 28, "medium": 10, "hard": 2}
    err = errors.get(difficulty, 10)
    final_a = max(5,  min(175, round(best_angle + random.uniform(-err, err))))
    final_v = max(20, min(200, round(best_vel   + random.uniform(-err * 2, err * 2))))
    return final_a, final_v, ""


# ─── MENSAGENS ─────────────────────────────────────────────────────────────
MISS_MSGS = [
    "Isso foi um tantinho longe, não foi?", "Parece que exagerou um pouco.",
    "Acho que precisa de óculos.", "Hmm... isso não foi bom.",
    "Que fraqueza essa foi.", "Você consegue melhor que isso!",
    "Um pouco mais perto e talvez você tenha chance.",
    '"Oi? Estou aqui!"', "Uau! Vai com calma!",
    "Não era pra botar em órbita.", "O QUÊ? Foi MILHAS longe!",
    "O QUE VOCÊ TÁ FAZENDO?", "Não era pra jogar assim!",
    "Calma, calma…", "Nope. Longe demais.",
]
WIN_MSGS = [
    "CERTEIRO! 🍌", "ACERTOU EM CHEIO! 💥", "JUSTIÇA DE BANANA! 🦍",
    "BOOM! 💣", "É ASSIM QUE FAZ! 🎯",
]


# ─── ROTAS ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/new_game", methods=["POST"])
def new_game():
    data      = request.get_json(force=True, silent=True) or {}
    gravity   = max(1, min(int(data.get("gravity", DEFAULT_GRAVITY)), 99))
    buildings = make_cityscape()
    gorillas  = place_gorillas(buildings)
    wind = random.randint(-10, 10)
    if random.random() < 0.33:
        wind += random.choice([-1, 1]) * random.randint(0, 10)
    wind = max(-20, min(20, wind))

    return jsonify({
        "buildings": buildings, "gorillas": gorillas,
        "wind": wind, "gravity": gravity,
        "canvas_w": CANVAS_W, "canvas_h": CANVAS_H,
        "ground_y": GROUND_Y, "sun": {"x": SUN_X, "y": SUN_Y},
    })


@app.route("/api/throw", methods=["POST"])
def throw():
    data   = request.get_json(force=True)
    result = calculate_trajectory(
        start_x=float(data["gorilla_x"]), start_y=float(data["gorilla_y"]),
        angle_deg=float(data["angle"]),   velocity=float(data["velocity"]),
        player_num=int(data["player"]),   buildings=data["buildings"],
        gorilla_positions=data["gorillas"],
        gravity=float(data.get("gravity", DEFAULT_GRAVITY)),
        wind=float(data.get("wind", 0)),
    )
    hit = result["hit"]
    result["message"] = (random.choice(WIN_MSGS)  if hit and "gorilla" in hit
                         else random.choice(MISS_MSGS))
    return jsonify(result)


@app.route("/api/ai_throw", methods=["POST"])
def ai_throw():
    """
    Usa o Groq (llama-3.3-70b-versatile) para decidir ângulo e velocidade da IA.
    Se o Groq falhar, usa o fallback de física local corrigido.
    """
    data       = request.get_json(force=True)
    gorillas   = data["gorillas"]       # lista [g1, g2]
    buildings  = data["buildings"]
    wind       = float(data.get("wind", 0))
    gravity    = float(data.get("gravity", DEFAULT_GRAVITY))
    difficulty = data.get("difficulty", "medium")

    ai_pos     = gorillas[1]    # IA = índice 1 (direita)
    target_pos = gorillas[0]    # Jogador = índice 0 (esquerda)

    dx   = target_pos["x"] - ai_pos["x"]   # negativo (alvo à esquerda)
    dist = math.hypot(dx, target_pos["y"] - ai_pos["y"])

    # Calcula fallback antes de chamar a IA (garante valores válidos)
    angle, velocity, comment = _fallback_aim(ai_pos, target_pos, wind, gravity, difficulty)

    # Contexto físico para o modelo
    prompt = f"""Você é o jogador 2 de Gorillas (o clássico jogo do DOS).
Você está no lado DIREITO do mapa. Seu gorila está em x={ai_pos['x']}, y={ai_pos['y']}.
O alvo (jogador humano) está em x={target_pos['x']}, y={target_pos['y']}.
Distância horizontal: {abs(dx):.0f} pixels (alvo à SUA ESQUERDA).
Vento: {wind} (positivo = empurra para a direita, negativo = para a esquerda).
Gravidade: {gravity}. Canvas: {CANVAS_W}x{CANVAS_H}. Dificuldade: {difficulty}.

Regras físicas exatas:
- O backend espelha o ângulo: angulo_efetivo = 180 - angle_informado.
- Informe o ângulo como se fosse lançar para a DIREITA (o espelhamento é automático).
- Velocidade entre 20 e 200. Quanto maior a distância, maior a velocidade necessária.
- Para dist≈{abs(dx):.0f}px, velocidade sugerida ≈ {min(200,max(20,abs(dx)*0.55+20)):.0f}.
- Ângulo sugerido pelo fallback: {angle}° vel: {velocity}.

Responda SOMENTE com JSON válido neste formato:
{{"angle": <inteiro 5-175>, "velocity": <inteiro 20-200>, "comment": "<frase curta de provocação em português>"}}"""

    try:
        if GROQ_CLIENT.api_key:
            resp = GROQ_CLIENT.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=120,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences se presentes
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            parsed   = json.loads(raw)
            angle    = max(5,  min(175, int(parsed["angle"])))
            velocity = max(20, min(200, int(parsed["velocity"])))
            comment  = parsed.get("comment", "")
    except Exception as e:
        print(f"[Groq fallback] {e}")

    return jsonify({"angle": angle, "velocity": velocity, "comment": comment})


# ─── ENTRY POINT ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
