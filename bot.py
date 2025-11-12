from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES (Lendo dos Secrets do Render) ---
# O Render carrega estas variáveis do seu painel de ambiente.
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

# URL base do seu serviço no Render (necessário para o Webhook do Mercado Pago)
# Esta URL é fixa com base no seu domínio: https://ntg-tech-vendas.onrender.com
RENDER_BASE_URL = "https://ntg-tech-vendas.onrender.com" 

if not MERCADO_PAGO_ACCESS_TOKEN:
    print("AVISO: MERCADO_PAGO_ACCESS_TOKEN não encontrado. A geração do checkout irá falhar.")
if not TELEGRAM_BOT_TOKEN:
    print("AVISO: TELEGRAM_BOT_TOKEN não encontrado. O bot não poderá responder.")


# --- LISTA DE PRODUTOS FIXA (Chave deve ser o nome em MAIÚSCULAS) ---
PRODUCTS_DATA = {
    "ILLUSTRATOR 2025": {"price": 9.00, "link": "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link"},
    "PHOTOSHOP 2024": {"price": 8.00, "link": "https://drive.google.com/file/d/1wt3EKXIHdopKeFBLG0pEuPWJ2Of4ZrAx/view?usp=sharing"},
    "PHOTOSHOP 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"},
    "INDESIGN 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing"},
    "PREMIERE 2025": {"price": 10.00, "link": "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=sharing"},
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

def get_all_products_for_api():
    """Formata todos os produtos da lista fixa para a resposta JSON."""
    products_list = []
    for name, data in PRODUCTS_DATA.items():
        products_list.append({
            "name": name,
            "price": data["price"],
            "link": data["link"]
        })
    return products_list

def enviar_mensagem_telegram(chat_id, texto):
    if not TELEGRAM_BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERRO CRÍTICO: Falha ao enviar mensagem para o Telegram. Erro: {e}")

def criar_preferencia_mp(produto_nome, preco, chat_id):
    """Cria uma preferência de pagamento dinamicamente no Mercado Pago."""
    if not MERCADO_PAGO_ACCESS_TOKEN:
        return None

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # URL de notificação completa (para avisar o Render sobre o pagamento)
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
            "telegram_user_id": str(chat_id), # ID do usuário para entrega
            "produto": produto_nome            # Nome do produto para buscar o link do Drive
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

# --- ROTA: RECEBE MENSAGENS DO TELEGRAM ---
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        
        if update and 'message' in update:
            chat_id = update['message']['chat']['id']
            texto_recebido = update['message'].get('text', '').strip()
            
            comando = texto_recebido.upper() 
            
            if comando == "/START":
                mensagem_resposta = "👋 Olá! Seja bem-vindo à NTG Tech. Use /produtos para ver nosso catálogo e siga as instruções para iniciar o pagamento."
            
            elif comando == "/PRODUTOS":
                produtos = get_all_products_for_api()
                
                mensagem_resposta = "🛍️ <b>Nossos Produtos Disponíveis:</b>\n\n"
                for p in produtos:
                    mensagem_resposta += f"🔹 <b>{p['name']}</b> - R$ {p['price']:.2f}\n"

                mensagem_resposta += "\n💡 **Para Comprar:** Digite o nome exato do produto que deseja (Exemplo: PHOTOSHOP 2025) para receber o link de pagamento."
                
            # === LÓGICA DE GERAÇÃO DE CHECKOUT MP ===
            elif comando in PRODUCTS_DATA:
                produto_data = PRODUCTS_DATA[comando]
                
                # 1. Tenta criar o link de pagamento dinamicamente
                link_pagamento = criar_preferencia_mp(
                    produto_nome=comando,
                    preco=produto_data['price'],
                    chat_id=chat_id
                )
                
                if link_pagamento:
                    mensagem_resposta = (
                        f"🛒 Você selecionou: <b>{comando}</b> (R$ {produto_data['price']:.2f})\n\n"
                        f"Acesse o link abaixo para finalizar a compra via Mercado Pago:\n"
                        f"<a href=\"{link_pagamento}\">{link_pagamento}</a>"
                    )
                else:
                    mensagem_resposta = "❌ Desculpe, houve um erro ao gerar o link de pagamento. Por favor, verifique o Token do Mercado Pago (ACCESS_TOKEN) ou contate o suporte."
                
            else:
                mensagem_resposta = f"Desculpe, não entendi o comando <b>{texto_recebido}</b>. Use /start ou /produtos."
                
            enviar_mensagem_telegram(chat_id, mensagem_resposta)

        # Retorno 200 OK é obrigatório para o Telegram
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
    try:
        return jsonify(get_all_products_for_api()), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch products"}), 500
