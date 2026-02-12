from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES (Lendo dos Secrets do Render) ---
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

# URL base do seu serviço no Render (MANTENHA ESTE)
RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com" 

if not MERCADO_PAGO_ACCESS_TOKEN:
    print("AVISO: MERCADO_PAGO_ACCESS_TOKEN ausente. A geração do checkout irá falhar.")
if not TELEGRAM_BOT_TOKEN:
    print("AVISO: TELEGRAM_BOT_TOKEN ausente. O bot não poderá responder.")


# --- LISTA DE PRODUTOS FIXA (Chave deve ser o nome em MAIÚSCULAS) ---
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

# --- FUNÇÕES DE APOIO ---

def get_product_data(product_name):
    """Busca os dados de um produto na lista fixa pelo nome."""
    return PRODUCTS_DATA.get(product_name.upper())

def enviar_mensagem_telegram(chat_id, texto, reply_markup=None): 
    """Envia uma mensagem (pode ser com Reply Keyboard ou Inline Keyboard)."""
    if not TELEGRAM_BOT_TOKEN:
        print("Erro: TELEGRAM_BOT_TOKEN ausente.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
    }
    
    if reply_markup:
         payload["reply_markup"] = reply_markup
         
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f"ERRO CRÍTICO: Falha ao enviar mensagem para o Telegram. Erro: {e}")

def enviar_link_mp(chat_id, produto_nome, message_id):
    """
    Gera o link de pagamento do Mercado Pago e EDITA a mensagem do Telegram 
    para mostrar o link e remover os botões.
    """
    produto_data = PRODUCTS_DATA.get(produto_nome.upper())

    if not produto_data:
        print(f"ERRO: Produto {produto_nome} não encontrado para gerar link.")
        mensagem_resposta = "❌ Produto não encontrado. Use /produtos para tentar novamente."
    else:
        link_pagamento = criar_preferencia_mp(
            produto_nome=produto_nome,
            preco=produto_data['price'],
            chat_id=chat_id
        )

        if link_pagamento:
            mensagem_resposta = (
                f"✅ Link Gerado: <b>{produto_nome}</b> (R$ {produto_data['price']:.2f})\n\n"
                f"Acesse o link abaixo para finalizar a compra via Mercado Pago:\n"
                f"<a href=\"{link_pagamento}\">{link_pagamento}</a>"
            )
        else:
            mensagem_resposta = "❌ Desculpe, houve um erro ao gerar o link de pagamento. Tente novamente mais tarde."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensagem_resposta,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": []} 
    }
    try:
        requests.post(url, json=payload).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao editar mensagem no Telegram: {e}")

def criar_preferencia_mp(produto_nome, preco, chat_id):
    if not MERCADO_PAGO_ACCESS_TOKEN:
        return None

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    notification_url = f"{RENDER_BASE_URL}/notificacao"

    payload = {
        "items": [{"title": produto_nome, "quantity": 1, "unit_price": preco}],
        "metadata": {"telegram_user_id": str(chat_id), "produto": produto_nome},
        "notification_url": notification_url,
        "back_urls": {"success": "https://t.me/NTGTECH_bot"},
        "auto_return": "approved"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("init_point") 
    except requests.exceptions.RequestException as e:
        print(f"ERRO no MP: {e}")
        return None

# ===============================================
#          ROTAS DO FLASK (WEBHOOKS)
# ===============================================

@app.route('/')
def home():
    return 'Webhook ativo!'

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()

        if 'callback_query' in update:
            callback_query = update['callback_query']
            callback_data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']

            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", 
                          json={"callback_query_id": callback_query['id']})
            
            # Verificação de produtos
            if callback_data.upper() in PRODUCTS_DATA:
                enviar_link_mp(chat_id, callback_data.upper(), message_id)
            
            # Resposta para o botão de Instalação
            elif callback_data == "COMO_INSTALAR":
                mensagem_instalar = (
                    "🛠️ <b>Como Instalar os Programas:</b>\n\n"
                    "Assista aos vídeos tutoriais abaixo para realizar a instalação:\n\n"
                    "• <a href='LINK_DO_SEU_VIDEO_AQUI'>Tutorial de Instalação Geral</a>\n"
                )
                enviar_mensagem_telegram(chat_id, mensagem_instalar)

            return jsonify({'status': 'ok'}), 200

        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            texto_recebido = message.get('text', '').strip().upper()
            
            hide_keyboard = {"remove_keyboard": True}

            if texto_recebido == "/START":
                # Adicionando o botão de Como Instalar no menu inicial
                inline_markup = {
                    "inline_keyboard": [
                        [{"text": "🛍️ Ver Produtos", "text": "🛍️ Ver Produtos", "callback_data": "VER_PRODUTOS_CMD"}],
                        [{"text": "🛠️ Como Instalar", "callback_data": "COMO_INSTALAR"}]
                    ]
                }
                mensagem_resposta = "👋 Olá! Seja bem-vindo à NTG Tech. Use os botões abaixo para navegar:"
                enviar_mensagem_telegram(chat_id, mensagem_resposta, reply_markup=inline_markup)
                return jsonify({'status': 'ok'}), 200

            elif texto_recebido == "/PRODUTOS" or texto_recebido == "VER_PRODUTOS_CMD":
                inline_buttons = []
                for name, data in PRODUCTS_DATA.items():
                    inline_buttons.append([{"text": f"🛒 {name} (R$ {data['price']:.2f})", "callback_data": name}])
                
                inline_markup = {"inline_keyboard": inline_buttons}
                mensagem_resposta = "🛍️ <b>Clique no produto para comprar:</b>"
                enviar_mensagem_telegram(chat_id, mensagem_resposta, reply_markup=inline_markup)
                return jsonify({'status': 'ok'}), 200
                
            else:
                enviar_mensagem_telegram(chat_id, "Use /start ou /produtos.", reply_markup=hide_keyboard)
                return jsonify({'status': 'ok'}), 200

        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"ERRO: {e}")
        return jsonify({'status': 'error'}), 200

@app.route('/notificacao', methods=['POST'])
def notificacao():
    # ... (sua lógica de notificação permanece idêntica)
    try:
        dados = request.json
        if dados and dados.get("type") == "payment":
            payment_id = dados.get("data", {}).get("id")
            headers_mp = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
            response_mp = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers_mp)
            payment_details = response_mp.json()
            
            if payment_details.get("status") == "approved":
                telegram_user_id = payment_details.get("metadata", {}).get("telegram_user_id")
                produto_nome = payment_details.get("metadata", {}).get("produto")
                product_data = get_product_data(produto_nome)
                
                if product_data:
                    link = product_data["link"]
                    mensagem = f"🎉 Pagamento confirmado!\n<b>Produto:</b> {produto_nome}\n<b>Acesse aqui:</b> {link}"
                    enviar_mensagem_telegram(telegram_user_id, mensagem) 
        return "OK", 200
    except:
        return 'Error', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
