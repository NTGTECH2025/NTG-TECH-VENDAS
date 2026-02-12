from flask import Flask, request, jsonify
import requests
import os

MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com"

# =============================
# PRODUTOS
# =============================

PRODUCTS_DATA = {
    "ILLUSTRATOR 2025": {"price": 9.00, "link": "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link"},
    "ILLUSTRATOR 2026": {"price": 14.00, "link": "https://drive.google.com/drive/folders/1-CRR3E51FI2hxXgPoFF2EOZgeJNJ2nex?usp=sharing"},
    "AUTOCAD 2026": {"price": 10.00, "link": "https://drive.google.com/file/d/1ajnOUzxLDfSOeXTJHCLJ1DiGjYDeW6o8/view?usp=drive_link"},
    "PHOTOSHOP 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"},
    "INDESIGN 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing"},
    "PREMIERE 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=drive_link"},
    "ADOBE ACROBAT DC 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/11g0c9RJoOg0qkF7ucMGN6PGL28USKnmM/view?usp=drive_link"},
    "REVIT 2026": {"price": 10.00, "link": "https://drive.google.com/file/d/1BaYFpzNPLWRAiqcX6qQYxAJijF8k2Do2/view?usp=drive_link"},
    "SKETCHUP 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/16me_DDq2UTwSI3hT0Q55F7JhLBi0ykW-/view?usp=sharing"},
    "AFTER EFFECTS 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1fvxYC41vLa51wO1noCy7PgFwSlaEBbad/view?usp=sharing"},
    "LIGHTROOM CLASSIC 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/19imV-3YRbViFw-EMHh4ivS9ok2Sqv0un/view?usp=sharing"}
}

# =============================
# VÍDEOS
# =============================

INSTALL_VIDEOS = {
    "INSTALAR_PS": {
        "nome": "PHOTOSHOP 2025",
        "link": "https://www.youtube.com/watch?v=apkQG3PTt-0"
    },
    "INSTALAR_AI": {
        "nome": "ILLUSTRATOR 2025",
        "link": "https://link-do-youtube"
    },
    "INSTALAR_PREMIERE": {
        "nome": "PREMIERE 2025",
        "link": "https://link-do-youtube"
    },
    "INSTALAR_AE": {
        "nome": "AFTER EFFECTS 2025",
        "link": "https://link-do-youtube"
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
# ENVIAR MENSAGEM
# =============================

def enviar(chat_id, texto, markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
        "reply_markup": markup or menu_principal()
    }

    requests.post(url, json=payload)

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

            enviar(chat_id, "🛍️ <b>Escolha o produto:</b>", {
                "inline_keyboard": botoes
            })

        elif data == "MENU_INSTALAR":
            botoes = []

            for chave, v in INSTALL_VIDEOS.items():
                botoes.append([
                    {"text": f"📦 {v['nome']}", "callback_data": chave}
                ])

            botoes.append([{"text": "⬅️ Voltar", "callback_data": "MENU"}])

            enviar(chat_id, "📦 <b>Escolha o tutorial:</b>", {
                "inline_keyboard": botoes
            })

        elif data == "MENU":
            enviar(chat_id, "🏠 <b>Menu principal:</b>", menu_principal())

        elif data in PRODUCTS_DATA:
            p = PRODUCTS_DATA[data]
            link = criar_preferencia(data, p["price"], chat_id)

            enviar(
                chat_id,
                f"✅ <b>{data}</b>\n<a href=\"{link}\">Clique aqui para pagar</a>"
            )

        elif data in INSTALL_VIDEOS:
            v = INSTALL_VIDEOS[data]

            enviar(
                chat_id,
                f"📦 <b>{v['nome']}</b>\n<a href=\"{v['link']}\">Assistir tutorial</a>"
            )

        return jsonify(ok=True)

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        enviar(chat_id, "👋 <b>Bem-vindo!</b>\nEscolha uma opção:")

    return jsonify(ok=True)

# =============================
# PAGAMENTO
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

        enviar(
            chat_id,
            f"🎉 Pagamento confirmado!\n\n{produto}\n<a href=\"{link}\">Baixar aqui</a>"
        )

    return "OK"

@app.route('/')
def home():
    return "Bot ativo!"
