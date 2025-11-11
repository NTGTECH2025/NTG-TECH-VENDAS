# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request
import requests
import os
import base64
from io import BytesIO
import threading
import asyncio
import time

# ------------------ Flask (health + webhook) ------------------
app_flask = Flask(__name__)

@app_flask.route('/health')
def health_check():
    return "Bot is alive!", 200

# --- NOTIFICAÇÃO (Webhook que o Mercado Pago vai chamar) ---
@app_flask.route('/notificacao', methods=['POST'])
def notificacao_pagamento():
    """
    Recebe notificações do Mercado Pago.
    Quando um pagamento estiver 'approved' e conter metadata com telegram_user_id e produto,
    envia automaticamente o link do produto para o usuário via Telegram.
    """
    try:
        payload = request.get_json(force=True, silent=True)
        if not payload:
            return "OK", 200

        # Extrai o possível id do pagamento:
        # O Mercado Pago envia diferentes formatos; tentamos várias possibilidades.
        pagamento_id = None
        if isinstance(payload.get("data"), dict):
            pagamento_id = payload["data"].get("id") or payload["data"].get("id_payment") or payload["data"].get("id_payments")
        if not pagamento_id:
            # Alguns webhooks enviam {"id": "...", "type":"payment"} no corpo
            pagamento_id = payload.get("id")

        if not pagamento_id:
            # Sem id para consultar, apenas responde OK
            return "OK", 200

        # Consulta o pagamento no Mercado Pago para saber status e metadata
        headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
        resp = requests.get(f"https://api.mercadopago.com/v1/payments/{pagamento_id}", headers=headers, timeout=15)
        if resp.status_code != 200:
            # Tenta também endpoint v0 (fallback)
            try:
                resp2 = requests.get(f"https://api.mercadopago.com/v0/payments/{pagamento_id}", headers=headers, timeout=15)
                if resp2.status_code == 200:
                    payment = resp2.json()
                else:
                    return "OK", 200
            except:
                return "OK", 200
        else:
            payment = resp.json()

        status = payment.get("status")  # ex: 'approved', 'pending', ...
        metadata = payment.get("metadata", {}) or {}
        telegram_user_id = metadata.get("telegram_user_id")
        produto_name = metadata.get("produto") or metadata.get("produto_name") or metadata.get("product")

        # Se aprovado e tiver info, envia o link
        if status == "approved" and telegram_user_id and produto_name:
            produto_info = PRODUTOS.get(produto_name)
            if produto_info:
                link = produto_info.get("link")
                try:
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    text = (f"✅ Pagamento aprovado!\n\n"
                            f"Produto: {produto_name}\n\n"
                            f"Aqui está seu link de download/entrega:\n{link}\n\n"
                            f"Qualquer dúvida, responda aqui.")
                    bot.send_message(chat_id=int(telegram_user_id), text=text)
                except Exception as e:
                    print("Erro ao enviar mensagem via Bot:", e)
        return "OK", 200

    except Exception as e:
        print("Erro no endpoint /notificacao:", e)
        return "OK", 200


# ------------------ CONFIGS ------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL")  # ex: https://seu-bot.onrender.com
PORT = int(os.environ.get("PORT", 8080))

if not TELEGRAM_BOT_TOKEN:
    print("⚠️ TELEGRAM_BOT_TOKEN não configurado nas variáveis de ambiente.")
if not MERCADO_PAGO_ACCESS_TOKEN:
    print("⚠️ MERCADO_PAGO_ACCESS_TOKEN não configurado nas variáveis de ambiente.")
if not RENDER_BASE_URL:
    # tenta montar a webhook a partir da variável, mas não é obrigatório — informativo
    print("⚠️ RENDER_BASE_URL não configurado. Configure no Render: https://seu-bot.onrender.com")

# Use WEBHOOK_URL para colocar na criação da preferência no Mercado Pago (notification_url)
if RENDER_BASE_URL:
    WEBHOOK_URL = f"{RENDER_BASE_URL}/notificacao"
else:
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # fallback se o usuário preferir colocar direto

# ------------------ PRODUTOS (fixos, R$10,00 cada) ------------------
PRODUTOS = {
    "ILLUSTRATOR 2025": {"preco": 10.00, "link": "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link"},
    "PHOTOSHOP 2024": {"preco": 10.00, "link": "https://drive.google.com/file/d/1wt3EKXIHdopKeFBLG0pEuPWJ2Of4ZrAx/view?usp=sharing"},
    "PHOTOSHOP 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing"},
    "INDESIGN 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing"},
    "PREMIERE 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=sharing"},
    "ADOBE ACROBAT DC 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/11g0c9RJoOg0qkF7ucMGN6PGL28USKnmM/view?usp=drive_link"},
    "REVIT 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/18O8AA2AKCniqqlbG4AE4qCQ2sIP5oUiF/view?usp=sharing"},
    "SKETCHUP 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/SEU_LINK_SKETCHUP_AQUI/view?usp=sharing"},
    "AFTER EFFECTS 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/1fvxYC41vLa51wO1noCy7PgFwSlaEBbad/view?usp=sharing"},
    "LIGHTROOM CLASSIC 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/19imV-3YRbViFw-EMHh4ivS9ok2Sqv0un/view?usp=sharing"},
    "PACOTE OFFICE 2025": {"preco": 10.00, "link": "https://drive.google.com/file/d/1fw1QYPgL1tPXj5_x91g6qgwLHPE6Ru8w/view?usp=drive_link"},
    "CAPCUT": {"preco": 10.00, "link": "https://drive.google.com/file/d/1EKgufKRp7eTVbAW_ViIKAMhdikHoMlLe/view?usp=drive_link"}
}

# ------------------ Funções Mercado Pago ------------------
def criar_preferencia_pagamento(produto_name, preco, telegram_user_id):
    """
    Cria preferência no Mercado Pago (checkout/preferences).
    Retorna o JSON da API.
    """
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise ValueError("MERCADO_PAGO_ACCESS_TOKEN não configurado.")

    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}", "Content-Type": "application/json"}
    body = {
        "items": [
            {
                "title": produto_name,
                "quantity": 1,
                "unit_price": float(preco),
                "currency_id": "BRL"
            }
        ],
        "notification_url": WEBHOOK_URL or "",
        "metadata": {
            "telegram_user_id": str(telegram_user_id),
            "produto": produto_name
        },
        # Podemos sugerir Pix como método, mas não garante seu aparecimento sem conta/credenciais MP corretas
        "payment_methods": {
            "excluded_payment_methods": [],
            "excluded_payment_types": [],
            "installments": 1
        }
    }

    resp = requests.post("https://api.mercadopago.com/checkout/preferences", headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()

# ------------------ Handlers Telegram ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Quero Comprar", callback_data="menu_comprar")],
        [InlineKeyboardButton("❓ Suporte", url="https://t.me/NTGTECH")]
    ]
    await update.message.reply_text("Olá! 👋 Bem-vindo à NTG TECH. Escolha uma opção:", reply_markup=InlineKeyboardMarkup(keyboard))

async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_comprar":
        keyboard = [[InlineKeyboardButton(nome, callback_data=nome)] for nome in PRODUTOS.keys()]
        await query.edit_message_text("Escolha o produto que deseja comprar:", reply_markup=InlineKeyboardMarkup(keyboard))

async def product_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    produto_name = query.data
    produto = PRODUTOS.get(produto_name)
    if not produto:
        await query.edit_message_text("Produto não encontrado. Tente novamente.")
        return

    preco = produto["preco"]
    await query.edit_message_text(f"Gerando link de pagamento para *{produto_name}* — R$ {preco:.2f}", parse_mode="Markdown")

    try:
        pref = criar_preferencia_pagamento(produto_name, preco, query.from_user.id)
    except Exception as e:
        print("Erro ao criar preferência:", e)
        await context.bot.send_message(chat_id=query.message.chat_id, text="Erro ao gerar pagamento. Verifique o token do Mercado Pago.")
        return

    # tenta extrair init_point e qr (se disponível)
    init_point = pref.get("init_point")
    qr_code_b64 = None

    poi = pref.get("point_of_interaction") or {}
    if isinstance(poi, dict):
        txn = poi.get("transaction_data") or {}
        qr_code_b64 = txn.get("qr_code_base64")

    # Envia ao usuário: QR se houver, senão init_point
    if qr_code_b64:
        try:
            img_bytes = base64.b64decode(qr_code_b64)
            img_stream = BytesIO(img_bytes)
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_stream,
                                         caption=f"📲 Escaneie o QR code para pagar {produto_name} — R$ {preco:.2f}")
            if init_point:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"Ou pague pelo link: {init_point}")
        except Exception as e:
            print("Erro ao enviar QR:", e)
            if init_point:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"Link de pagamento: {init_point}")
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Não foi possível gerar o QR. Tente pelo link.")
    elif init_point:
        await context.bot.send_message(chat_id=query.message.chat_id,
                                       text=f"🔗 Link de pagamento para *{produto_name}* — R$ {preco:.2f}:\n{init_point}",
                                       parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Não foi possível gerar o link de pagamento. Tente novamente mais tarde.")

# ------------------ Run do Telegram + Flask ------------------
def run_telegram_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("TOKEN do Telegram faltando. Saindo do run_telegram_bot.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(main_menu_button, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(product_button_handler))  # pega callbacks dos produtos

    print("Iniciando bot do Telegram (polling)...")
    app.run_polling(poll_interval=1.0)

if __name__ == "__main__":
    # inicia flask em thread separada (para o Render escutar /notificacao)
    flask_thread = threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=PORT, use_reloader=False), daemon=True)
    flask_thread.start()
    print(f"Flask rodando na porta {PORT} (thread separada).")
    # inicia bot do telegram (polling)
    run_telegram_bot()
