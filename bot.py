from flask import Flask, request, jsonify
import requests
import os

MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com"

# =============================
# CONTROLE DE MENSAGENS
# =============================

ULTIMA_MSG = {}

# =============================
# PRODUTOS
# =============================

PRODUCTS_DATA = {
    "PHOTOSHOP 2025": {
        "price": 10.00,
        "link": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"
    }
}

# =============================
# VÍDEOS
# =============================

INSTALL_VIDEOS = {
    "INSTALAR_PS": {
        "nome": "PHOTOSHOP 2025",
        "link": "https://www.youtube.com/watch?v=apkQG3PTt-0"
    }
}

# =============================
# MENU PRINCIPAL
# =============================

def menu_principal():
    return {
        "inline_keyboard": [
            [{"text": "🛒 Produtos", "callback_data": "MENU_PRODUTOS"}],
            [{"text": "📦 Instalar", "callback_data": "MENU_INSTALAR"}]
        ]
    }

# =============================
# ENVIAR MENSAGEM (AUTO LIMPEZA)
# =============================

def enviar(chat_id, texto, markup=None):
    global ULTIMA_MSG

    # apagar mensagem anterior
    if chat_id in ULTIMA_MSG:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": ULTIMA_MSG[chat_id]
            }
        )

    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "reply_markup": markup or menu_principal()
        }
    )

    if r.status_code == 200:
        ULTIMA_MSG[chat_id] = r.json()["result"]["message_id"]

# =============================
# ENVIAR GIF
# =============================

def enviar_gif(chat_id):
    gif_url = "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif"

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAnimation",
        json={
            "chat_id": chat_id,
            "animation": gif_url
        }
    )

# =============================
# MERCADO PAGO
# =============================

def criar_preferencia(produto, preco, chat_id):
    url = "https://api.mercadopago.com/checkout/preferences"

    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "items": [{
            "title": produto,
            "quantity": 1,
            "unit_price": preco
        }],
        "metadata": {
            "telegram_user_id": str(chat_id),
            "produto": produto
        },
        "notification_url": f"{RENDER_BASE_URL}/notificacao"
    }

    r = requests.post(url, headers=headers, json=payload)

    if r.status_code == 201:
        return r.json()["init_point"]

    return None

# =============================
# TELEGRAM WEBHOOK
# =============================

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    if "callback_query" in update:
        q = update["callback_query"]
        data = q["data"]
        chat_id = q["message"]["chat"]["id"]

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": q["id"]}
        )

        if data == "MENU_PRODUTOS":
            botoes = []

            for nome, d in PRODUCTS_DATA.items():
                botoes.append([
                    {"text": f"🛒 {nome} (R$ {d['price']:.2f})", "callback_data": nome}
                ])

            botoes.append([{"text": "⬅️ Voltar", "callback_data": "MENU"}])

            enviar(chat_id, "🛍️ Escolha o produto:", {
                "inline_keyboard": botoes
            })

        elif data == "MENU_INSTALAR":
            botoes = []

            for chave, v in INSTALL_VIDEOS.items():
                botoes.append([
                    {"text": f"📦 {v['nome']}", "callback_data": chave}
                ])

            botoes.append([{"text": "⬅️ Voltar", "callback_data": "MENU"}])

            enviar(chat_id, "📦 Escolha o tutorial:", {
                "inline_keyboard": botoes
            })

        elif data == "MENU":
            enviar(chat_id, "🏠 Menu principal:", menu_principal())

        elif data in PRODUCTS_DATA:
            p = PRODUCTS_DATA[data]
            link = criar_preferencia(data, p["price"], chat_id)

            enviar(chat_id, f"✅ {data}\nClique para pagar:\n{link}")

        elif data in INSTALL_VIDEOS:
            v = INSTALL_VIDEOS[data]
            enviar(chat_id, f"📦 {v['nome']}\n{v['link']}")

        return jsonify(ok=True)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        enviar(chat_id, "👋 Bem-vindo! Escolha uma opção:")

    return jsonify(ok=True)

# =============================
# PAGAMENTO APROVADO
# =============================

@app.route('/notificacao', methods=['POST'])
def notificacao():
    dados = request.json

    if dados.get("type") != "payment":
        return "OK"

    payment_id = dados["data"]["id"]

    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}

    r = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers=headers
    )

    pagamento = r.json()

    if pagamento.get("status") != "approved":
        return "OK"

    meta = pagamento.get("metadata", {})
    chat_id = meta.get("telegram_user_id")
    produto = meta.get("produto")

    if produto in PRODUCTS_DATA:
        link = PRODUCTS_DATA[produto]["link"]

        enviar_gif(chat_id)

        enviar(
            chat_id,
            f"🎉 Pagamento confirmado!\n\n{produto}\nBaixar:\n{link}"
        )

    return "OK"

@app.route('/')
def home():
    return "Bot ativo!"
