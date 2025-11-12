from flask import Flask, request, jsonify  # Importe jsonify também
import requests
import os
import sqlite3  # Importe a biblioteca SQLite3

app = Flask(__name__)
 
# --- CONFIGURAÇÕES (Lendo dos Secrets do Replit) ---
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not MERCADO_PAGO_ACCESS_TOKEN:
    print("AVISO: MERCADO_PAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente! O webhook pode não funcionar corretamente.")
if not TELEGRAM_BOT_TOKEN:
    print("AVISO: TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente! O envio de mensagens para o Telegram pode falhar.")

# --- Configuração do Banco de Dados ---
DATABASE_FILE = 'products.db'  # O ficheiro da base de dados será criado neste mesmo projeto do Replit

def init_db():
    """Inicializa a base de dados, criando a tabela 'products' se não existir."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            price REAL NOT NULL,
            link TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de dados inicializada ou já existente.")

def get_product_from_db(product_name):
    """Busca um produto na base de dados pelo nome."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, link FROM products WHERE name = ?", (product_name,))
    product_data = cursor.fetchone()
    conn.close()
    if product_data:
        # Retorna um dicionário para fácil acesso
        return {"name": product_data[0], "price": product_data[1], "link": product_data[2]}
    return None

def get_all_products_from_db():
    """Busca todos os produtos na base de dados."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, link FROM products")
    products = []
    for row in cursor.fetchall():
        products.append({"name": row[0], "price": row[1], "link": row[2]})
    conn.close()
    return products

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

# --- ROTAS DA APLICAÇÃO WEBHOOK ---

@app.route('/')
def home():
    return 'Webhook do bot de vendas ativo no Replit! Aguardando notificações em /notificacao'

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
                # --- Busca o link do produto na base de dados ---
                product_data = get_product_from_db(produto_nome)
                if product_data:
                    link = product_data["link"]
                    mensagem = f"🎉 Pagamento confirmado! Seu produto já está disponível:\n\n<b>Produto:</b> {produto_nome}\n<b>Acesse aqui:</b> <a href=\"{link}\">{link}</a>"
                    enviar_mensagem_telegram(telegram_user_id, mensagem)
                    print(f"SUCESSO: Produto '{produto_nome}' (link: {link}) enviado para o usuário {telegram_user_id} via Telegram.")
                    return "OK", 200
                else:
                    print(f"ERRO: Produto '{produto_nome}' não encontrado na base de dados. Não foi possível entregar.")
                    enviar_mensagem_telegram(telegram_user_id, f"Desculpe, o produto '{produto_nome}' não foi encontrado. Por favor, contate o suporte.")
                    return 'Product not found in DB', 404
            else:
                print(f"INFO: Pagamento '{payment_id}' não aprovado ou metadados incompletos. Status: {status}, User ID: {telegram_user_id}, Produto: {produto_nome}")
                return "No action: Payment not approved or data incomplete", 200
        else:
            print("INFO: Webhook recebido, mas não é uma notificação de pagamento ou tipo desconhecido. Dados:", dados)
            return "Not a payment notification or unhandled type", 200

    except Exception as e:
        print(f"ERRO GERAL: Ocorreu um erro inesperado ao processar o webhook /notificacao: {e}")
        return 'Internal Server Error', 500

@app.route('/produtos', methods=['GET'])  # NOVA ROTA PARA O BOT BUSCAR PRODUTOS
def get_products():
    """
    Rota para o bot do Telegram buscar a lista de produtos.
    Retorna todos os produtos da base de dados como JSON.
    """
    try:
        products_list = get_all_products_from_db()  # Função para buscar todos os produtos
        return jsonify(products_list), 200  # Retorna a lista como JSON
    except Exception as e:
        print(f"ERRO: Falha ao buscar produtos da base de dados: {e}")
        return jsonify({"error": "Failed to fetch products"}), 500  # Retorna erro em formato JSON

if __name__ == "__main__":
    init_db()  # Inicializa a base de dados (cria a tabela se não existir)

    # --- Adicionar produtos de exemplo na base de dados ---
    # ESTAS LINHAS SÓ DEVEM SER EXECUTADAS UMA VEZ PARA POPULAR A BASE DE DADOS.
    # APÓS A PRIMEIRA EXECUÇÃO BEM-SUCEDIDA, COMENTE OU REMOVA ESTE BLOCO PARA NÃO DUPLICAR PRODUTOS.
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    products_to_add = [
        ("ILLUSTRATOR 2025", 9.00, "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link"),
        ("PHOTOSHOP 2024", 8.00, "https://drive.google.com/file/d/1wt3EKXIHdopKeFBLG0pEuPWJ2Of4ZrAx/view?usp=sharing"),
        ("PHOTOSHOP 2025", 10.00, "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"),
        ("INDESIGN 2025", 10.00, "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing"),
        ("PREMIERE 2025", 10.00, "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=sharing"),
        ("ADOBE ACROBAT DC 2025", 10.00, "https://drive.google.com/file/d/11g0c9RJoOg0qkF7ucMGN6PGL28USKnmM/view?usp=drive_link"),
        ("REVIT 2025", 10.00, "https://drive.google.com/file/d/SEU_LINK_REVIT_AQUI/view?usp=sharing"),  # ATENÇÃO: VERIFIQUE ESTE LINK NOVAMENTE!
        ("SKETCHUP 2025", 10.00, "https://drive.google.com/file/d/SEU_LINK_SKETCHUP_AQUI/view?usp=sharing"),  # ATENÇÃO: VERIFIQUE ESTE LINK NOVAMENTE!
        ("AFTER EFFECTS 2025", 10.00, "https://drive.google.com/file/d/1fvxYC41vLa51wO1noCy7PgFwSlaEBbad/view?usp=sharing"),
        ("LIGHTROOM CLASSIC 2025", 10.00, "https://drive.google.com/file/d/19imV-3YRbViFw-EMHh4ivS9ok2Sqv0un/view?usp=sharing")
    ]
    for p_name, p_price, p_link in products_to_add:
        try:
            cursor.execute("INSERT INTO products (name, price, link) VALUES (?, ?, ?)", (p_name, p_price, p_link))
            print(f"Produto '{p_name}' adicionado com sucesso.")
        except sqlite3.IntegrityError:
            print(f"Produto '{p_name}' já existe na base de dados. Pulando inserção.")
            # Se quiser, pode adicionar uma lógica para ATUALIZAR o produto aqui:
            # cursor.execute("UPDATE products SET price = ?, link = ? WHERE name = ?", (p_price, p_link, p_name))
    conn.commit()
    conn.close()
    print("Produtos de exemplo inseridos (se não existissem).")
    # --- Fim da adição de produtos de exemplo ---

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
    print(f"Flask App (Webhook) rodando no Replit na porta {port}...")
