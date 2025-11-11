import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import threading

# ------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL")  # https://ntg-tech-vendas.onrender.com

if not TOKEN or not MERCADO_PAGO_ACCESS_TOKEN or not RENDER_BASE_URL:
    print("⚠️ ERRO: Variáveis de ambiente não configuradas corretamente!")
    exit()

# ------------------------------------------
# LISTA DE PRODUTOS (todos R$10,00)
# ------------------------------------------
PRODUTOS = {
    "ILLUSTRATOR 2025": "https://drive.google.com/drive/folders/1x1JQV47hebrLQe_GF4eq32oQgMt2E5CA?usp=drive_link",     
    "PHOTOSHOP 2024": "https://drive.google.com/file/d/1wt3EKXIHdopKeFBLG0pEuPWJ2Of4ZrAx/view?usp=sharing",
    "PHOTOSHOP 2025": "https://drive.google.com/file/d/1w0Uyjga1SZRveeStUWWZoz4OxH-tVA3g/view?usp=sharing",
    "INDESIGN 2025": "https://drive.google.com/file/d/1vZM63AjyRh8FnNn06UjhN49BLSNcXe7Y/view?usp=sharing",
    "PREMIERE 2025": "https://drive.google.com/file/d/1QWXJNYVPJ319rXLlDbtf9mdnkEvudMbW/view?usp=sharing",
    "ADOBE ACROBAT DC 2025": "https://drive.google.com/file/d/11g0c9RJoOg0qkF7ucMGN6PGL28USKnmM/view?usp=drive_link",
    "REVIT 2025": "https://drive.google.com/file/d/18O8AA2AKCniqqlbG4AE4qCQ2sIP5oUiF/view?usp=sharing",
    "SKETCHUP 2025": "https://drive.google.com/file/d/SEU_LINK_SKETCHUP_AQUI/view?usp=sharing",
    "AFTER EFFECTS 2025": "https://drive.google.com/file/d/1fvxYC41vLa51wO1noCy7PgFwSlaEBbad/view?usp=sharing",
    "LIGHTROOM CLASSIC 2025": "https://drive.google.com/file/d/19imV-3YRbViFw-EMHh4ivS9ok2Sqv0un/view?usp=sharing",
    "PACOTE OFFICE 2025": "https://drive.google.com/file/d/1fw1QYPgL1tPXj5_x91g6qgwLHPE6Ru8w/view?usp=drive_link",
    "CAPCUT": "https://drive.google.com/file/d/1EKgufKRp7eTVbAW_ViIKAMhdikHoMlLe/view?usp=drive_link"
}

PRECO_PADRAO = 10.00

# ------------------------------------------
# TELEGRAM BOT
# ------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(prod, callback_data=prod)] for prod in PRODUTOS.keys()]
    await update.message.reply_text("Escolha o produto:", reply_markup=InlineKeyboardMarkup(keyboard))

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    produto = query.data
    await query.answer()

    body = {
        "items": [{
            "title": produto,
            "quantity": 1,
            "unit_price": PRECO_PADRAO
        }],
        "notification_url": f"{RENDER_BASE_URL}/notificacao",
        "metadata": {
            "telegram_user_id": query.from_user.id,
            "produto": produto
        }
    }

    resp = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        headers={"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"},
        json=body
    ).json()

    link_pagamento = resp.get("init_point")

    await query.edit_message_text(f"💰 *Pagamento:* R$10,00\n\nClique para pagar:\n{link_pagamento}", parse_mode="Markdown")

# ------------------------------------------
# WEBHOOK (ENTREGA AUTOMÁTICA)
# ------------------------------------------
app = Flask(__name__)

@app.route("/notificacao", methods=["POST"])
def notificacao():
    data = request.json
    pagamento_id = data.get("data", {}).get("id")

    if pagamento_id:
        resp = requests.get(
            f"https://api.mercadopago.com/v1/payments/{pagamento_id}",
            headers={"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
        ).json()

        if resp.get("status") == "approved":
            produto = resp["metadata"]["produto"]
            user = resp["metadata"]["telegram_user_id"]
            link = PRODUTOS[produto]
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                          json={"chat_id": user, "text": f"✅ Pagamento aprovado!\n\nAqui está seu download:\n{produto}\n{link}"})
    return "OK"

# ------------------------------------------
# EXECUTAR BOT + SERVIDOR
# ------------------------------------------
def run_bot():
    app_tg = Application.builder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CallbackQueryHandler(comprar))
    app_tg.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
