from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES (Lendo dos Secrets do Render) ---
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

# URL base do seu serviço no Render
RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com" 

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

def enviar_mensagem_telegram(chat_id, texto, reply_markup=None): 
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def enviar_link_mp(chat_id, produto_nome, message_id):
    produto_data = PRODUCTS_DATA.get(produto_nome.upper())
    if produto_data:
        # Lógica de geração de link simplificada para o exemplo
        url_mp = "https://api.mercadopago.com/checkout/preferences"
        headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
        payload = {
            "items": [{"title": produto_nome, "quantity": 1, "unit_price": produto_data['price']}],
            "metadata": {"telegram_user_id": str(chat_id), "produto": produto_nome},
            "notification_url": f"{RENDER_BASE_URL}/notificacao"
        }
        res = requests.post(url_mp, headers=headers, json=payload).json()
        link = res.get("init_point", "Erro ao gerar link")
        
        texto = f"✅ Link Gerado: <b>{produto_nome}</b>\n\n<a href='{link}'>Clique aqui para pagar</a>"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": texto, "parse_mode": "HTML"
        })

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    # 1. TRATA OS CLIQUES NOS BOTÕES
    if 'callback_query' in update:
        query = update['callback_query']
        data = query['data']
        chat_id = query['message']['chat']['id']
        message_id = query['message']['message_id']

        # Remove o ícone de carregamento do botão
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": query['id']})

        if data == "BOTAO_TUTORIAIS":
            texto_tutoriais = "🛠️ <b>Tutoriais de Instalação:</b>\n\nAssista ao vídeo abaixo para aprender a instalar:\n\n<a href='SEU_LINK_DO_YOUTUBE_AQUI'>👉 CLIQUE AQUI PARA VER O VÍDEO</a>"
            enviar_mensagem_telegram(chat_id, texto_tutoriais)
        
        elif data == "BOTAO_PRODUTOS":
            buttons = [[{"text": f"🛒 {n}", "callback_data": n}] for n in PRODUCTS_DATA.keys()]
            enviar_mensagem_telegram(chat_id, "🛍️ <b>Selecione o produto abaixo:</b>", reply_markup={"inline_keyboard": buttons})

        elif data in PRODUCTS_DATA:
            enviar_link_mp(chat_id, data, message_id)

        return jsonify({'status': 'ok'}), 200

    # 2. TRATA OS COMANDOS DIGITADOS (/START)
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        texto = msg.get('text', '').upper()

        if texto == "/START":
            # Aqui criamos o menu principal com as duas abas
            markup = {
                "inline_keyboard": [
                    [{"text": "🛍️ Ver Produtos", "callback_data": "BOTAO_PRODUTOS"}],
                    [{"text": "🛠️ Como Instalar (Tutoriais)", "callback_data": "BOTAO_TUTORIAIS"}]
                ]
            }
            enviar_mensagem_telegram(chat_id, "👋 Olá! Bem-vindo à NTG Tech.\n\nEscolha uma das opções abaixo:", reply_markup=markup)

    return jsonify({'status': 'ok'}), 200

# Mantive o restante das rotas (notificacao, home) conforme seu original...
@app.route('/')
def home(): return "Bot Online"

@app.route('/notificacao', methods=['POST'])
def notificacao():
    # Sua lógica de notificação original aqui...
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
