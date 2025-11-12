from flask import Flask, request, jsonify
import requests
import os

# --- CONFIGURAÇÕES (Lendo dos Secrets do Render) ---
# As variáveis devem ser definidas no painel de ambiente do Render.
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

if not MERCADO_PAGO_ACCESS_TOKEN:
    print("AVISO: MERCADO_PAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente! O webhook pode não funcionar corretamente.")
if not TELEGRAM_BOT_TOKEN:
    print("AVISO: TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente! O envio de mensagens para o Telegram pode falhar.")


# --- LISTA DE PRODUTOS FIXA ---
# O NOME do produto (em MAIÚSCULAS) será a chave.
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

# --- FUNÇÕES DE BUSCA ---

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


# --- FUNÇÃO PARA ENVIAR MENSAGENS AO TELEGRAM ---
def enviar_mensagem_telegram(chat_id, texto):
    if not TELEGRAM_BOT_TOKEN:
        print("Erro: TOKEN do Telegram não configurado para enviar mensagem.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Mensagem enviada com sucesso para o chat {chat_id}: {texto[:50]}...")
    except requests.exceptions.RequestException as e:
        print(f"ERRO CRÍTICO: Falha ao enviar mensagem para o Telegram para {chat_id}. Erro: {e}")


# ===============================================
#          ROTAS DO FLASK (WEBHOOKS)
# ===============================================

@app.route('/')
def home():
    return 'Webhook do bot de vendas ativo no Render! Pronto para receber notificações.'

# --- ROTA: RECEBE MENSAGENS DO TELEGRAM ---
@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        
        if update and 'message' in update:
            chat_id = update['message']['chat']['id']
            texto_recebido = update['message'].get('text', '').strip()
            
            # Converte para maiúsculas para verificar o produto, minúsculas para comandos
            comando = texto_recebido.upper() 
            
            if comando == "/START":
                mensagem_resposta = "👋 Olá! Seja bem-vindo à NTG Tech. Use /produtos para ver nosso catálogo e siga as instruções para iniciar o pagamento."
            
            elif comando == "/PRODUTOS":
                produtos = get_all_products_for_api()
                
                mensagem_resposta = "🛍️ <b>Nossos Produtos Disponíveis:</b>\n\n"
                for p in produtos:
                    mensagem_resposta += f"🔹 <b>{p['name']}</b> - R$ {p['price']:.2f}\n"

                mensagem_resposta += "\n💡 **Para Comprar:** Digite o nome exato do produto que deseja (Exemplo: PHOTOSHOP 2025) para receber o link de pagamento."
                
            # Verifica se a mensagem corresponde a um produto
            elif comando in PRODUCTS_DATA:
                produto_data = PRODUCTS_DATA[comando]
                link_pagamento = "LINK DE PAGAMENTO DO MERCADO PAGO AQUI" # SUBSTITUA ESTE LINK PELO SEU CHECKOUT REAL
                
                mensagem_resposta = (
                    f"🛒 Você selecionou: <b>{comando}</b> (R$ {produto_data['price']:.2f})\n\n"
                    f"Acesse o link abaixo para finalizar a compra via Mercado Pago:\n"
                    f"<a href=\"{link_pagamento}\">{link_pagamento}</a>"
                )
                
            else:
                mensagem_resposta = f"Desculpe, não entendi o comando <b>{texto_recebido}</b>. Use /start ou /produtos."
                
            enviar_mensagem_telegram(chat_id, mensagem_resposta)

        # O Telegram sempre espera 200 OK, mesmo se não houver ação.
        return jsonify({'status': 'ok'}), 200
    
    except Exception as e:
        print(f"ERRO CRÍTICO ao processar webhook do Telegram: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 200


# --- ROTA: RECEBE NOTIFICAÇÕES DO MERCADO PAGO ---
@app.route('/notificacao', methods=['POST'])
def notificacao():
    try:
        dados = request.json
        print("Webhook recebido (JSON completo):", dados)

        if dados and "type" in dados and dados["type"] == "payment":
            payment_id = dados.get("data", {}).get("id")

            if not payment_id:
                print("Erro: ID do pagamento não encontrado na notificação do Mercado Pago. Dados:", dados)
                return 'Bad Request: Payment ID missing', 400

            headers_mp = {
                "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payment_url = f"https://api.mercadopago.com/v1/payments/{payment_id}"

            try:
                response_mp = requests.get(payment_url, headers=headers_mp)
                response_mp.raise_for_status()
                payment_details = response_mp.json()
                print(f"Detalhes do pagamento {payment_id} obtidos: {payment_details.get('status')}")
            except requests.exceptions.RequestException as e:
                print(f"ERRO: Falha ao buscar detalhes do pagamento {payment_id} no Mercado Pago. Erro: {e}")
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
                    print(f"SUCESSO: Produto '{produto_nome}' (link: {link}) enviado para o usuário {telegram_user_id} via Telegram.")
                    return "OK", 200
                else:
                    print(f"ERRO: Produto '{produto_nome}' não encontrado na lista de produtos. Não foi possível entregar.")
                    enviar_mensagem_telegram(telegram_user_id, f"Desculpe, o produto '{produto_nome}' não foi encontrado. Por favor, contate o suporte.")
                    return 'Product not found in list', 404
            else:
                print(f"INFO: Pagamento '{payment_id}' não aprovado ou metadados incompletos. Status: {status}, User ID: {telegram_user_id}, Produto: {produto_nome}")
                return "No action: Payment not approved or data incomplete", 200
        else:
            print("INFO: Webhook recebido, mas não é uma notificação de pagamento ou tipo desconhecido. Dados:", dados)
            return "Not a payment notification or unhandled type", 200

    except Exception as e:
        print(f"ERRO GERAL: Ocorreu um erro inesperado ao processar o webhook /notificacao: {e}")
        return 'Internal Server Error', 500

@app.route('/produtos', methods=['GET'])
def get_products():
    """
    Rota auxiliar para o bot buscar a lista de produtos (se necessário).
    """
    try:
        products_list = get_all_products_for_api()
        return jsonify(products_list), 200
    except Exception as e:
        print(f"ERRO: Falha ao buscar produtos da lista fixa: {e}")
        return jsonify({"error": "Failed to fetch products"}), 500
