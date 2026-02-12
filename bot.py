from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES ---
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com" 

app = Flask(__name__)

# --- LISTA DE PRODUTOS ---
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

# --- FUNÇÕES DE COMUNICAÇÃO ---

def enviar_mensagem_telegram(chat_id, texto, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML", "reply_markup": reply_markup}
    return requests.post(url, json=payload)

def editar_mensagem_telegram(chat_id, message_id, texto, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": texto, "parse_mode": "HTML", "reply_markup": reply_markup}
    return requests.post(url, json=payload)

def criar_preferencia_mp(produto_nome, preco, chat_id):
    if not MERCADO_PAGO_ACCESS_TOKEN: return None
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "items": [{"title": produto_nome, "quantity": 1, "unit_price": preco}],
        "metadata": {"telegram_user_id": str(chat_id), "produto": produto_nome},
        "notification_url": f"{RENDER_BASE_URL}/notificacao",
        "back_urls": {"success": "https://t.me/NTGTECH_bot"},
        "auto_return": "approved"
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.json().get("init_point") if res.status_code == 201 else None

# --- WEBHOOK PRINCIPAL ---

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    # MENU INICIAL (START)
    menu_principal = {
        "inline_keyboard": [
            [{"text": "🛍️ Ver Produtos", "callback_data": "MENU_PRODUTOS"}],
            [{"text": "🛠️ Como Instalar (Tutoriais)", "callback_data": "MENU_INSTALAR"}]
        ]
    }

    # 1. PROCESSA CLIQUES NOS BOTÕES
    if 'callback_query' in update:
        query = update['callback_query']
        chat_id = query['message']['chat']['id']
        message_id = query['message']['message_id']
        data = query['data']

        # Responde o clique para tirar o reloginho do botão
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": query['id']})

        if data == "MENU_INSTALAR":
            markup = {
                "inline_keyboard": [
                    [{"text": "📺 Tutorial Geral", "url": "https://youtube.com/LINK_AQUI"}],
                    [{"text": "🔙 Voltar ao Início", "callback_data": "VOLTAR"}]
                ]
            }
            texto = "<b>🛠️ Central de Ajuda</b>\n\nClique no botão abaixo para assistir ao vídeo de como instalar os programas corretamente:"
            editar_mensagem_telegram(chat_id, message_id, texto, markup)

        elif data == "MENU_PRODUTOS":
            buttons = [[{"text": f"🛒 {n} (R$ {d['price']:.2f})", "callback_data": f"BUY_{n}"}] for n, d in PRODUCTS_DATA.items()]
            buttons.append([{"text": "🔙 Voltar", "callback_data": "VOLTAR"}])
            editar_mensagem_telegram(chat_id, message_id, "🛍️ <b>Selecione um produto:</b>", {"inline_keyboard": buttons})

        elif data == "VOLTAR":
            editar_mensagem_telegram(chat_id, message_id, "👋 Olá! Seja bem-vindo à NTG Tech. O que deseja fazer?", menu_principal)

        elif data.startswith("BUY_"):
            prod_name = data.replace("BUY_", "")
            link = criar_preferencia_mp(prod_name, PRODUCTS_DATA[prod_name]['price'], chat_id)
            if link:
                msg = f"✅ Link Gerado: <b>{prod_name}</b>\n\n<a href='{link}'>Clique aqui para pagar</a>"
                editar_mensagem_telegram(chat_id, message_id, msg, {"inline_keyboard": [[{"text": "🔙 Voltar", "callback_data": "MENU_PRODUTOS"}]]})

        return jsonify({'status': 'ok'}), 200

    # 2. PROCESSA MENSAGENS DIGITADAS
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '').upper()

        if text == "/START" or text == "/PRODUTOS":
            enviar_mensagem_telegram(chat_id, "👋 Olá! Seja bem-vindo à NTG Tech. Escolha uma opção:", menu_principal)

    return jsonify({'status': 'ok'}), 200

# --- ROTA DE NOTIFICAÇÃO (MANTIDA) ---
@app.route('/notificacao', methods=['POST'])
def notificacao():
    dados = request.json
    if dados and dados.get("type") == "payment":
        p_id = dados.get("data", {}).get("id")
        res = requests.get(f"https://api.mercadopago.com/v1/payments/{p_id}", headers={"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"})
        pay = res.json()
        if pay.get("status") == "approved":
            u_id = pay.get("metadata", {}).get("telegram_user_id")
            p_nome = pay.get("metadata", {}).get("produto")
            link = PRODUCTS_DATA.get(p_nome, {}).get("link")
            if link:
                enviar_mensagem_telegram(u_id, f"🎉 Pagamento aprovado!\n\n<b>Produto:</b> {p_nome}\n<b>Link:</b> {link}")
    return "OK", 200

@app.route('/')
def home(): return "Bot Online"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
