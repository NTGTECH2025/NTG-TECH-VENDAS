import os
import requests
import base64
from io import BytesIO
from PIL import Image
import threading
from flask import Flask, request
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Flask para health check
app_flask = Flask(__name__)

@app_flask.route("/")
def health_check():
    return "Bot NTG está vivo!", 200

# Tokens
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")

if not TOKEN:
    print("AVISO: TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente!")
if not MERCADO_PAGO_ACCESS_TOKEN:
    print("AVISO: MERCADO_PAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente!")

# Webhook e produtos
WEBHOOK_URL = "https://497eb7c7-a5c8-44cd-b216-afb9cce1bc76-00-39d048gqjpfu1.spock.replit.dev/notificacao"
GET_PRODUCTS_URL = WEBHOOK_URL.replace("/notificacao", "/produtos")

# Vídeos
VIDEO_DATA = {
    "video_photoshop": {
        "title": "Photoshop 2025",
        "url": "https://www.youtube.com/watch?v=5NMxsgTH9TI"
    },
    # Adicione mais vídeos aqui
}

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Quero Comprar", callback_data='menu_comprar')],
        [InlineKeyboardButton("❓ Tirar Dúvidas", callback_data='menu_duvidas')],
        [InlineKeyboardButton("▶️ Acessar Vídeos de Instalação", callback_data='menu_videos')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Olá! 👋 Seja bem-vindo à NTG TECH! Escolha uma opção abaixo:",
        reply_markup=reply_markup
    )

# Buscar produtos
async def fetch_products():
    try:
        response = requests.get(GET_PRODUCTS_URL, timeout=10)
        response.raise_for_status()
        products_list = response.json()
        return {
            p['name']: {'preco': p['price'], 'link': p['link']}
            for p in products_list
        }
    except:
        return {}

# Mostrar produtos
async def show_product_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = await fetch_products()
    if not products:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Não foi possível carregar os produtos.")
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Escolha um produto:", reply_markup=reply_markup)

# Menu principal
async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'menu_comprar':
        await query.edit_message_text(text="Carregando produtos...")
        await show_product_list(update, context)
    elif query.data == 'menu_duvidas':
        keyboard = [[InlineKeyboardButton("🏠 Voltar ao Menu", callback_data='menu_principal')]]
        await query.edit_message_text(
            text="Envie sua dúvida ou fale com @NTGTECH.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == 'menu_videos':
        keyboard = [
            [InlineKeyboardButton(f"🎥 {v['title']}", callback_data=k)] for k, v in VIDEO_DATA.items()
        ]
        keyboard.append([InlineKeyboardButton("🏠 Voltar ao Menu", callback_data='menu_principal')])
        await query.edit_message_text(
            text="Escolha um vídeo de instalação:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == 'menu_principal':
        await query.edit_message_text(text="Voltando ao menu...")
        await start(update, context)

# Vídeos
async def send_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    video_info = VIDEO_DATA.get(query.data)
    if not video_info:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Vídeo não encontrado.")
        return
    await query.edit_message_text(text=f"Você escolheu: <b>{video_info['title']}</b>", parse_mode="HTML")
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"{video_info['url']}", parse_mode="HTML")

# Pagamento
def criar_preferencia_pagamento(nome, preco, user_id):
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "items": [{"title": nome, "quantity": 1, "unit_price": preco, "currency_id": "BRL"}],
        "notification_url": WEBHOOK_URL,
        "metadata": {"telegram_user_id": user_id, "produto": nome},
        "payment_methods": {"installments": 1, "default_payment_method_id": "pix"}
    }
    response = requests.post("https://api.mercadopago.com/checkout/preferences", headers=headers, json=body)
    response.raise_for_status()
    return response.json()

# Produto selecionado
async def product_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    produto = query.data
    products = await fetch_products()
    dados = products.get(produto)
    if not dados:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Produto não encontrado.")
        return
    preco = dados["preco"]
    await query.edit_message_text(text=f"Gerando link de pagamento para <b>{produto}</b>...", parse_mode="HTML")
    try:
        resposta = criar_preferencia_pagamento(produto, preco, query.from_user.id)
        link = resposta.get("init_point")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"<a href='{link}'>Clique aqui para pagar</a>", parse_mode="HTML")
    except:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Erro ao gerar link de pagamento.")

def run_telegram_bot_thread_target():
    """
    Função alvo para a thread do bot do Telegram.
    Cria e define um novo loop de evento asyncio para esta thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if not TOKEN:
        print("ERRO CRÍTICO: TOKEN do Telegram não configurado. Bot não pode iniciar.")
        return

    app_tg = Application.builder().token(TOKEN).build()

    # Handler para o comando /start
    app_tg.add_handler(CommandHandler("start", start))

    # Handler para QUALQUER mensagem de texto que não seja um comando
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    # Handler para os botões do menu principal E para o botão "Voltar ao Menu Principal" nos vídeos
    app_tg.add_handler(CallbackQueryHandler(main_menu_button, pattern='^menu_'))

    # Handler para os botões de vídeo
    app_tg.add_handler(CallbackQueryHandler(send_video_message, pattern='^video_'))

    # Handler para os botões de produtos
    app_tg.add_handler(CallbackQueryHandler(product_button_handler))

    print("Bot do Telegram iniciado... Aguardando comandos e cliques...")
    app_tg.run_polling()


# Início
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_thread = threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=port, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    print(f"Servidor Flask iniciado na porta {port}...")
    run_telegram_bot_thread_target()
