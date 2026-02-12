from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES ---
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com"

# --- PRODUTOS ---
PRODUCTS_DATA = {
    "ILLUSTRATOR 2025": {"price": 9.00, "link": "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link"},
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

# --- VÍDEOS DE INSTALAÇÃO (COLOQUE SEUS LINKS AQUI) ---
INSTALL_VIDEOS = {
    "PHOTOSHOP 2025": "https://link-do-seu-video",
    "ILLUSTRATOR 2025": "https://link-do-seu-video",
    "PREMIERE 2025": "https://link-do-seu-video",
    "AFTER EFFECTS 2025": "https://link-do-seu-video"
}

# --- FUNÇÕES ---

def get_product_data(product_name):
    return PRODUCTS_DATA.get(product_name.upper())

def enviar_mensagem_telegram(chat_id, texto, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload)

def enviar_link_mp(chat_id, produto_nome, message_id):
    produto_data = PRODUCTS_DATA.get(produto_nome.upper())

    if not produto_data:
        return

    link_pagamento = criar_preferencia_mp(
        produto_nome=produto_nome,
        preco=produto_data['price'],
        chat_id=chat_id
    )

    if not link_pagamento:
        return

    mensagem = (
        f"✅ Link Gerado: <b>{produto_nome}</b>\n\n"
        f"<a href=\"{link_pagamento}\">{link_pagamento}</a>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensagem,
        "parse_mode": "HTML"
    }

    requests.post(url, json=payload)

def criar_preferencia_mp(produto_nome, preco, chat_id):
    url = "https://api.mercadopago.com/checkout/preferences"

    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "items": [{
            "title": produto_nome,
            "quantity": 1,
            "unit_price": preco
        }],
        "metadata": {
            "telegram_user_id": str(chat_id),
            "produto": produto_nome
        },
        "notification_url": f"{RENDER_BASE_URL}/notificacao"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        return response.json().get("init_point")

    return None

# --- WEBHOOK TELEGRAM ---

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    # CALLBACK DOS BOTÕES
    if 'callback_query' in update:
        query = update['callback_query']
        data = query['data'].upper()
        chat_id = query['message']['chat']['id']
        message_id = query['message']['message_id']

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": query['id']}
        )

        if data in PRODUCTS_DATA:
            enviar_link_mp(chat_id, data, message_id)

        elif data in INSTALL_VIDEOS:
            link = INSTALL_VIDEOS[data]

            mensagem = (
                f"📦 <b>Tutorial de instalação:</b>\n\n"
                f"<b>{data}</b>\n"
                f"<a href=\"{link}\">Clique aqui para assistir</a>"
            )

            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": mensagem,
                    "parse_mode": "HTML"
                }
            )

        return jsonify({'ok': True})

    # MENSAGENS
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        texto = msg.get('text', '').upper()

        if texto == "/START":
            mensagem = (
                "👋 <b>Bem-vindo à NTG Tech</b>\n\n"
                "/produtos — Comprar programas\n"
                "/instalar — Tutoriais de instalação"
            )
            enviar_mensagem_telegram(chat_id, mensagem)

        elif texto == "/PRODUTOS":
            botoes = []

            for nome, dados in PRODUCTS_DATA.items():
                botoes.append([
                    {"text": f"🛒 {nome} (R$ {dados['price']:.2f})", "callback_data": nome}
                ])

            enviar_mensagem_telegram(
                chat_id,
                "🛍️ <b>Escolha um produto:</b>",
                {"inline_keyboard": botoes}
            )

        elif texto == "/INSTALAR":
            botoes = []

            for nome in INSTALL_VIDEOS.keys():
                botoes.append([
                    {"text": f"📦 {nome}", "callback_data": nome}
                ])

            enviar_mensagem_telegram(
                chat_id,
                "📦 <b>Escolha o tutorial:</b>",
                {"inline_keyboard": botoes}
            )

    return jsonify({'ok': True})

# --- NOTIFICAÇÃO MERCADO PAGO ---

@app.route('/notificacao', methods=['POST'])
def notificacao():
    dados = request.json

    if dados.get("type") != "payment":
        return "OK"

    payment_id = dados["data"]["id"]

    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"

    r = requests.get(url, headers=headers)
    pagamento = r.json()

    if pagamento.get("status") != "approved":
        return "OK"

    meta = pagamento.get("metadata", {})
    chat_id = meta.get("telegram_user_id")
    produto = meta.get("produto")

    produto_data = get_product_data(produto)

    if produto_data:
        link = produto_data["link"]

        mensagem = (
            f"🎉 <b>Pagamento confirmado!</b>\n\n"
            f"<b>{produto}</b>\n"
            f"<a href=\"{link}\">Clique aqui para baixar</a>"
        )

        enviar_mensagem_telegram(chat_id, mensagem)

    return "OK"

@app.route('/')
def home():
    return "Bot ativo!"
