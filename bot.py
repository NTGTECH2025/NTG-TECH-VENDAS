from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
import os
import base64
from io import BytesIO
import threading
from flask import Flask
import asyncio
  
# ================== SERVIDOR FLASK (HEALTH CHECK) ==================
app_flask = Flask(__name__)

@app_flask.route('/health')
def health_check():
    return 'Bot is alive!', 200

@app_flask.route('/')
def home():
    return 'Bot backend is running.', 200

# ================== TOKEN E MERCADO PAGO ==================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")

if not TOKEN:
    print("⚠️ ERRO: TELEGRAM_BOT_TOKEN não configurado.")
if not MERCADO_PAGO_ACCESS_TOKEN:
    print("⚠️ ERRO: MERCADO_PAGO_ACCESS_TOKEN não configurado.")

WEBHOOK_URL = "https://SEU_WEBHOOK_AQUI/notificacao"  # <-- SE QUISER RECEBER CONFIRMAÇÕES

# ================== LISTA FIXA DE PRODUTOS ==================
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

# ================== MENU /START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Quero Comprar", callback_data='menu_comprar')],
        [InlineKeyboardButton("❓ Suporte", url="https://t.me/NTGTECH")]
    ]
    await update.message.reply_text("Olá! 👋 Bem-vindo à NTG TECH.\nEscolha uma opção:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== MENU PRINCIPAL ==================
async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_comprar":
        keyboard = [[InlineKeyboardButton(nome, callback_data=nome)] for nome in PRODUTOS.keys()]
        await query.edit_message_text("Escolha o produto:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== CRIA PAGAMENTO MERCADO PAGO ==================
def criar_preferencia_pagamento(produto_name, preco, telegram_user_id):
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}", "Content-Type": "application/json"}
    body = {
        "items": [{"title": produto_name, "quantity": 1, "unit_price": preco, "currency_id": "BRL"}],
        "notification_url": WEBHOOK_URL,
        "metadata": {"telegram_user_id": telegram_user_id, "produto": produto_name}
    }
    response = requests.post("https://api.mercadopago.com/checkout/preferences", headers=headers, json=body)
    return response.json()

# ================== COMPRA DO PRODUTO ==================
async def product_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    produto_name = query.data
    produto = PRODUTOS.get(produto_name)

    preco = produto["preco"]

    pagamento = criar_preferencia_pagamento(produto_name, preco, query.from_user.id)
    link_pagamento = pagamento.get("init_point")

    await query.edit_message_text(f"💰 Produto: {produto_name}\nValor: R$ {preco:.2f}\n\nClique para pagar:\n{link_pagamento}")

# ================== BOT RUN ==================
def run_telegram_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(main_menu_button, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(product_button_handler))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=8080, use_reloader=False), daemon=True).start()
    run_telegram_bot()
