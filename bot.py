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
    "PHOTOSHOP 2024": {"price": 8.00, "link": "https://drive.google.com/file/d/1wt3EKXIHdopKeFBLG0pEuPWJ2Of4ZrAx/view?usp=sharing"},
    "PHOTOSHOP 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"},
    "INDESIGN 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing"},
    "PREMIERE 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=drive_link"},
    "ADOBE ACROBAT DC 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/11g0c9RJoOg0qkF7ucMGN6PGL28USKnmM/view?usp=drive_link"},
    "REVIT 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/SEU_LINK_REVIT_AQUI/view?usp=sharing"},
    "SKETCHUP 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/SEU_LINK_SKETCHUP_AQUI/view?usp=sharing"},
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
        link_pagamento = None
    else:
        # 1. Tenta criar o link de pagamento dinamicamente
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

    # 2. Edita a mensagem anterior (que tinha os botões)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensagem_resposta,
        "parse_mode": "HTML",
        # Remove o teclado inline após gerar o link
        "reply_markup": {"inline_keyboard": []} 
    }
    try:
        requests.post(url, json=payload).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao editar mensagem no Telegram: {e}")

def criar_preferencia_mp(produto_nome, preco, chat_id):
    """Cria uma preferência de pagamento dinamicamente no Mercado Pago."""
    # (Lógica do MP permanece a mesma, pois já estava correta)
    if not MERCADO_PAGO_ACCESS_TOKEN:
        return None

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    notification_url = f"{RENDER_BASE_URL}/notificacao"

    payload = {
        "items": [
            {
                "title": produto_nome,
                "quantity": 1,
                "unit_price": preco,
            }
        ],
        "metadata": {
            "telegram_user_id": str(chat_id),
            "produto": produto_nome            
        },
        "notification_url": notification_url,
        "back_urls": {
            "success": "https://t.me/NTGTECH_bot",
            "pending": "https://t.me/NTGTECH_bot",
            "failure": "https://t.me/NTGTECH_bot"
        },
        "auto_return": "approved"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        preferencia = response.json()
        return preferencia.get("init_point") 

    except requests.exceptions.RequestException as e:
        print(f"ERRO ao criar preferência de pagamento no MP: {e}")
        return None

# ===============================================
#          ROTAS DO FLASK (WEBHOOKS)
# ===============================================

@app.route('/')
def home():
    return 'Webhook do bot de vendas ativo no Render! Aguardando mensagens e notificações.'

# --- ROTA PRINCIPAL: RECEBE MENSAGENS E CLIQUES DE BOTÕES ---
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()

        # 1. PROCESSA CLIQUES NOS BOTÕES INLINE (callback_query)
        if 'callback_query' in update:
            callback_query = update['callback_query']
            callback_data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']

            comando = callback_data.upper() 
            
            # Avisa o Telegram que a query foi recebida (remove o "loading" no botão)
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", 
                json={"callback_query_id": callback_query['id']}
            )
            
            if comando in PRODUCTS_DATA:
                # Chama a função para gerar o link MP e editar a mensagem
                enviar_link_mp(chat_id, comando, message_id)
                
            return jsonify({'status': 'ok - callback handled'}), 200


        # 2. PROCESSA MENSAGENS DE TEXTO (/start, /produtos)
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            texto_recebido = message.get('text', '').strip()
            
            comando = texto_recebido.upper() 
            
            # Estrutura para esconder teclados Reply antigos
            hide_keyboard = {"remove_keyboard": True}

            if comando == "/START":
                mensagem_resposta = "👋 Olá! Seja bem-vindo à NTG Tech. Use /produtos para ver nosso catálogo e clique no botão do produto para gerar seu link de pagamento."
                
                enviar_mensagem_telegram(chat_id, mensagem_resposta, reply_markup=hide_keyboard)
                return jsonify({'status': 'ok'}), 200

            # === BLOCO CHAVE: CRIA E MOSTRA OS BOTÕES INLINE ===
            elif comando == "/PRODUTOS":
                # 1. Constrói a lista de botões INLINE
                inline_buttons = []
                for name, data in PRODUCTS_DATA.items():
                    # Cada botão tem o texto visível e o 'callback_data' que é enviado ao backend
                    inline_buttons.append([
                        {"text": f"🛒 {name} (R$ {data['price']:.2f})", "callback_data": name}
                    ])
                
                # 2. Monta o objeto Inline Keyboard (NOVO FORMATO)
                inline_markup = {
                    "inline_keyboard": inline_buttons
                }

                mensagem_resposta = "🛍️ <b>Clique no botão do produto para gerar seu link de pagamento no Mercado Pago:</b>"

                # 3. Envia a mensagem COM o teclado INLINE
                enviar_mensagem_telegram(chat_id, mensagem_resposta, reply_markup=inline_markup)
                return jsonify({'status': 'ok'}), 200
                
            else:
                mensagem_resposta = f"Desculpe, não entendi o comando <b>{texto_recebido}</b>. Use /start ou /produtos."
                
                enviar_mensagem_telegram(chat_id, mensagem_resposta, reply_markup=hide_keyboard)
                return jsonify({'status': 'ok'}), 200

        return jsonify({'status': 'ok'}), 200
    
    except Exception as e:
        print(f"ERRO CRÍTICO ao processar webhook do Telegram: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 200


# --- ROTA: RECEBE NOTIFICAÇÕES DO MERCADO PAGO ---
@app.route('/notificacao', methods=['POST'])
def notificacao():
    """Recebe a notificação de pagamento do Mercado Pago e envia o produto."""
    try:
        dados = request.json

        if dados and dados.get("type") == "payment":
            payment_id = dados.get("data", {}).get("id")

            if not payment_id:
                return 'Bad Request: Payment ID missing', 400

            headers_mp = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
            payment_url = f"https://api.mercadopago.com/v1/payments/{payment_id}"

            try:
                response_mp = requests.get(payment_url, headers=headers_mp)
                response_mp.raise_for_status()
                payment_details = response_mp.json()
            except requests.exceptions.RequestException as e:
                print(f"ERRO: Falha ao buscar detalhes do pagamento {payment_id}. Erro: {e}")
                return 'Error fetching payment details from MP', 500

            status = payment_details.get("status")
            metadata = payment_details.get("metadata", {})
            telegram_user_id = metadata.get("telegram_user_id")
            produto_nome = metadata.get("produto")

            if status == "approved" and telegram_user_id and produto_nome:
                # --- Busca o link do produto na lista fixa (PRODUCTS_DATA) ---
                product_data = get_product_data(produto_nome)
                
                if product_data:
                    link = product_data["link"]
                    mensagem = f"🎉 Pagamento confirmado! Seu produto já está disponível:\n\n<b>Produto:</b> {produto_nome}\n<b>Acesse aqui:</b> <a href=\"{link}\">{link}</a>"
                    enviar_mensagem_telegram(telegram_user_id, mensagem) 
                    return "OK", 200
                else:
                    print(f"ERRO: Produto '{produto_nome}' não encontrado na lista. Entrega manual necessária.")
                    return 'Product not found in list', 200 

            return "No action: Payment not approved or data incomplete", 200
        else:
            return "Not a payment notification or unhandled type", 200

    except Exception as e:
        print(f"ERRO GERAL ao processar o webhook /notificacao: {e}")
        return 'Internal Server Error', 500

@app.route('/produtos', methods=['GET'])
def get_products():
    """Rota auxiliar para listagem."""
    # ... código ...
