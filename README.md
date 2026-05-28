# 🦍 GORILLAS — Web Edition

Conversão moderna do clássico QBasic Gorillas 2.2 para Python + HTML5, pronto para deploy no Render.

## Estrutura do Projeto

```
gorillas_web/
├── app.py              # Backend Flask (física, geração de cidade, API)
├── requirements.txt    # Dependências Python
├── render.yaml         # Configuração de deploy no Render
└── static/
    └── index.html      # Frontend completo (HTML5 Canvas + JS)
```

## Como Funciona

### Backend (`app.py`)
- **`/api/new_game`** — Gera cenário aleatório: prédios, posições dos gorilas, vento
- **`/api/throw`** — Calcula a trajetória da banana com física real (parábola + vento)

### Frontend (`static/index.html`)
- Canvas HTML5 para renderização do jogo
- Animação suave da banana frame a frame
- Efeito de explosão ao acertar
- Sol animado que reage aos eventos
- Guia de trajetória preditiva
- HUD com placar, turno e vento

### Física (porta fiel do BASIC original)
- Trajetória balística: `x = vx·t + ½·(wind/5)·t²`
- Altura: `y = vy·t - ½·gravity·t²` com escala para canvas
- Vento aleatório entre -20 e +20
- Gravidade configurável (padrão: 17 m/s²)
- Bounce quando a banana atinge o chão

## Deploy no Render

### Opção 1 — Via Render.com (recomendado)

1. Faça upload do projeto para um repositório GitHub/GitLab
2. Acesse [render.com](https://render.com) → **New Web Service**
3. Conecte o repositório
4. Render detectará automaticamente o `render.yaml`
5. Clique em **Deploy**

### Opção 2 — Configuração manual no Render

| Campo | Valor |
|-------|-------|
| Environment | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2` |

### Rodando Localmente

```bash
pip install flask gunicorn
python app.py
# Acesse: http://localhost:5000
```

## Como Jogar

1. Digite os nomes dos jogadores
2. Configure rodadas e gravidade
3. Clique em **▶ JOGAR**
4. Use os sliders de **Ângulo** e **Velocidade**
5. Clique em **🍌 LANÇAR** ou pressione **Enter**
6. A guia tracejada mostra a trajetória aproximada
7. O primeiro a marcar a maioria das rodadas vence!

### Controles de Teclado
- `←/→` — Ajusta o ângulo
- `↑/↓` — Ajusta a velocidade  
- `Enter` — Lança a banana

## Diferenças em Relação ao Original

| Original (QBasic) | Web Edition |
|---|---|
| Gráficos EGA/CGA | Canvas HTML5 com neon |
| Som via PLAY | Sem áudio (pode adicionar Web Audio API) |
| Modo texto na config | Modal visual moderno |
| Dois jogadores no mesmo teclado | Dois jogadores no mesmo browser |
| Windows 3.x / DOS | Qualquer navegador moderno |
