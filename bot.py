import os
import requests
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ------------------------------------------
# VARIÁVEIS DE AMBIENTE
# ------------------------------------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL")
PORT = int(os.environ.get("PORT", 10000))  # <--- IMPORTANTE

# ------------------------------------------
# PRODUTOS (R$10 CADA)
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

PRECO = 10.00

# ------------------------------------------
# BOT TELEGRAM
# ------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(p, callback_data=p)] for p in PRODUTOS]
    await update.message.reply_text("Selecione o produto:", reply_markup=InlineKeyboardMarkup(keyboard))

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    produto = q.data
    await q.answer()

    body = {
        "items": [{"title": produto, "quantity": 1, "unit_price": PRECO}],
        "notification_url": f"{RENDER_BASE_URL}/notificacao",
        "metadata": {"telegram_user_id": q.from_user.id, "produto": produto}
    }

    resp = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        headers={"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"},
        json=body
    ).json()

    await q.edit_message_text(f"✅ Clique para pagar:\n\n{resp['init_point']}")

# ------------------------------------------
# FLASK WEBHOOK
# ------------------------------------------
app = Flask(__name__)

@app.route("/notificacao", methods=["POST"])
def notificacao():
    data = request.json
    payment_id = data.get("data", {}).get("id")

    if payment_id:
        resp = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
        ).json()

        if resp.get("status") == "approved":
            produto = resp["metadata"]["produto"]
            user_id = resp["metadata"]["telegram_user_id"]
            link = PRODUTOS[produto]

            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                          json={"chat_id": user_id, "text": f"✅ Pagamento aprovado!\n\n🔗 {produto}:\n{link}"})
    return "OK"

def run_bot():
    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(comprar))
    bot.run_polling()

threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
