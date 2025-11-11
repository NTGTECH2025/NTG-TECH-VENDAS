from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
import os
import base64
from io import BytesIO
from PIL import Image  # Necessário instalar Pillow
import threading
from flask import Flask, request
import asyncio
import time  # Importa a biblioteca 'time'

# --- Instância Flask para o Health Check e Rota Principal ---
app_flask = Flask(__name__)



@app_flask.route('/health')
def health_check():
    """
    Rota para o health check do bot.
    Retorna 'Bot is alive!' com status 200.
    """
    return 'Bot is alive!', 200


@app_flask.route('/')
def home():
    """
    Rota principal para evitar o erro 'Not Found'.
    Retorna uma mensagem simples indicando que o backend está funcionando.
    """
    return 'Bot backend is running. This URL is for internal bot operations and not a public website.', 200


# --- Fim das adições para Health Check e Rota Principal ---

# --- CONFIGURAÇÕES (Lendo dos Secrets do Replit) ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")

if not TOKEN:
    print(
        "AVISO: TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente! O bot pode não iniciar."
    )
if not MERCADO_PAGO_ACCESS_TOKEN:
    print(
        "AVISO: MERCADO_PAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente! Os links de pagamento não poderão ser gerados."
    )

# --- URL do seu Webhook (Servidor de Notificações) ---
# MUITO IMPORTANTE: COLE A URL ATUAL DO SEU WEBHOOK AQUI!
# Esta URL muda frequentemente no Replit. Copie da barra de "Preview" do seu projeto de webhook.
WEBHOOK_URL = "https://497eb7c7-a5c8-44cd-b216-afb9cce1bc76-00-39d048gqjpfu1.spock.replit.dev/notificacao"  # <<-- ATUALIZE ESTA LINHA COM A SUA URL ATUAL!

# --- URL para buscar produtos do seu próprio Webhook (nova rota) ---
GET_PRODUCTS_URL = WEBHOOK_URL.replace("/notificacao", "/produtos")

# --- Dicionário de Vídeos ---
# Usamos chaves curtas para o callback_data e armazenamos o título e o URL aqui
VIDEO_DATA = {
    "video_lightroom": {
        "title": "Lightroom Classic 2025",
        "url": "https://www.youtube.com/watch?v=ZozQ2V2haOo"
    },
    "video_illustrator": {
        "title": "Adobe Illustrator 2025",
        "url": "https://www.youtube.com/watch?v=NoEBAIMKV54"
    },  # Exemplo
    "video_acrobat": {
        "title": "Adobe Acrobat 2025",
        "url": "https://www.youtube.com/watch?v=NoEBAIMKV54"
    },  # Exemplo
    "video_aftereffects": {
        "title": "After Effects 2025",
        "url": "https://www.youtube.com/watch?v=NoEBAIMKV54"
    },  # Exemplo
    "video_indesign": {
        "title": "InDesign 2025",
        "url": "https://www.youtube.com/watch?v=NoEBAIMKV54"
    },  # Exemplo
    "video_premiere": {
        "title": "Premiere 2025",
        "url": "https://www.youtube.com/watch?v=NoEBAIMKV54"
    },  # Exemplo
    "video_photoshop": {
        "title": "Photoshop 2025",
        "url": "https://www.youtube.com/watch?v=5NMxsgTH9TI"
    },  # Exemplo
    # Adicione mais vídeos aqui, com uma chave única e curta para cada um
}


# --- Função assíncrona para buscar a lista de produtos do Webhook ---
async def fetch_products():
    """
    Busca a lista de produtos do backend do webhook (que agora lê do banco de dados).
    """
    try:
        print(f"Buscando produtos de: {GET_PRODUCTS_URL}")
        response = requests.get(GET_PRODUCTS_URL, timeout=10)
        response.raise_for_status()
        products_list = response.json()

        produtos_dict = {
            p['name']: {
                'preco': p['price'],
                'link': p['link']
            }
            for p in products_list
        }
        print(f"Produtos carregados: {produtos_dict.keys()}")
        return produtos_dict
    except requests.exceptions.RequestException as e:
        print(
            f"ERRO: Falha ao buscar produtos do backend ({GET_PRODUCTS_URL}). Erro: {e}"
        )
        return {}


# --- Função para exibir a lista de produtos como botões ---
async def show_product_list(update: Update,
                            context: ContextTypes.DEFAULT_TYPE,
                            message_id_to_edit=None):
    products = await fetch_products()
    if not products:
        message_text = "Desculpe, não foi possível carregar os produtos no momento. Tente novamente mais tarde."
        if message_id_to_edit:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id_to_edit,
                text=message_text)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message_text)
        return

    keyboard = [[
        InlineKeyboardButton(produto_name, callback_data=produto_name)
    ] for produto_name in products.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = "Perfeito! Escolha o produto que deseja adquirir entre as opções disponíveis abaixo:"  # Frase mais amigável

    if message_id_to_edit:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                            message_id=message_id_to_edit,
                                            text=message_text,
                                            reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text,
                                       reply_markup=reply_markup)


# --- Comando /start e Mensagem de Texto que mostra o MENU PRINCIPAL ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lida com o comando /start ou qualquer mensagem de texto, exibindo o menu principal.
    """
    keyboard = [[
        InlineKeyboardButton("🛒 Quero Comprar", callback_data='menu_comprar')
    ], [InlineKeyboardButton("❓ Tirar Dúvidas", callback_data='menu_duvidas')],
                [
                    InlineKeyboardButton("▶️ Acessar Vídeos de Instalação",
                                         callback_data='menu_videos')
                ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Frase inicial mais amigável e expansiva
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=
        "Olá! Tudo bem? 👋 Seja muito bem-vindo(a) à NTG TECH! É um prazer ter você aqui. Escolha uma opção abaixo para começar a interagir conosco:",
        reply_markup=reply_markup)


# --- Lida com os cliques nos botões do MENU PRINCIPAL ---
async def main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await .answer(
    )  # Responde à callback  para remover o estado de "carregando" do botão

    # Ajuste aqui para a frase mais natural
    if query.data == 'menu_comprar':
    await query.edit_message_text(
        text="Entendido! Vamos lá. Preparando a lista de produtos para você:"
    )
    await show_product_list(update, context, message_id_to_edit=query.message.message_id)


    elif query.data == 'menu_duvidas':
        faq_message = (
            "Entendo sua necessidade de tirar dúvidas! Estamos aqui para ajudar. Você pode:\n\n"  # Frase mais amigável
            "➡️ Enviar sua pergunta detalhada diretamente ou enviar seu erro para o suporte: @NTGTECH\n\n"
            "Estamos à disposição para garantir que você tenha a melhor experiência possível!"  # Frase de encerramento
        )

        # Adiciona o botão de voltar ao menu principal
        keyboard = [[
            InlineKeyboardButton("🏠 Voltar ao Menu Principal",
                                 callback_data='menu_principal')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=faq_message,
            reply_markup=reply_markup,  # Adiciona o reply_markup aqui
            parse_mode="HTML")
    elif query.data == 'menu_videos':
        video_keyboard = []
        for key, data in VIDEO_DATA.items():
            video_keyboard.append([
                InlineKeyboardButton(f"🎥 Vídeo: {data['title']}",
                                     callback_data=key)
            ])

        video_keyboard.append([
            InlineKeyboardButton("↩️ Ver Outros Vídeos de Instalação",
                                 callback_data='menu_videos')
        ])  # Mantém este
        video_keyboard.append([
            InlineKeyboardButton("🏠 Voltar ao Menu Principal",
                                 callback_data='menu_principal')
        ])  # Adiciona este

        video_reply_markup = InlineKeyboardMarkup(video_keyboard)
        await query.edit_message_text(
            text=
            "Excelente! Para te auxiliar na instalação, selecione o vídeo do programa que deseja acessar. Temos tutoriais claros para você!",  # Frase mais amigável
            reply_markup=video_reply_markup)
    elif query.data == 'menu_principal':
        await query.edit_message_text(text="Retornando ao menu principal...")
        await start(update, context)


# --- Lida com o clique nos botões de vídeo para enviar a mensagem com preview ---
async def send_video_message(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    video_key = query.data

    video_info = VIDEO_DATA.get(video_key)

    if not video_info:
        print(f"ERRO: Chave de vídeo inesperada no callback_data: {video_key}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            "Desculpe, houve um erro ao carregar o vídeo. Por favor, tente novamente."
        )
        return

    video_title = video_info["title"]
    video_url = video_info["url"]

    # Edita a mensagem original (dos botões de vídeo) para um texto mais neutro e claro
    # CORREÇÃO AQUI: Garante que parse_mode="HTML" esteja presente para interpretar o <b>
    await query.edit_message_text(
        text=
        f"Pronto! Você solicitou o vídeo de: <b>{video_title}</b>. Em breve ele aparecerá logo abaixo!",
        parse_mode="HTML")

    # Envia a NOVA MENSAGEM com o link do vídeo para a pré-visualização
    message_video = f"Assista ao vídeo aqui: <b>{video_title}</b>\n\n{video_url}"  # Frase mais amigável
    await context.bot.send_message(chat_id=query.message.chat_id,
                                   text=message_video,
                                   parse_mode="HTML",
                                   disable_web_page_preview=False)

    # Envia uma SEGUNDA NOVA MENSAGEM com as opções de acompanhamento
    follow_up_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("↩️ Ver Outros Vídeos de Instalação",
                                 callback_data='menu_videos')
        ],  # Texto mais descritivo
        [
            InlineKeyboardButton("🏠 Voltar ao Menu Principal",
                                 callback_data='menu_principal')
        ]
    ])
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=
        "O vídeo foi enviado! O que mais você gostaria de fazer agora? Estamos à sua disposição!",  # Frase mais amigável
        reply_markup=follow_up_keyboard)


# --- Quando o usuário clica num botão de produto ---
async def product_button_handler(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    produto_name = query.data  # Nome do produto clicado
    await query.answer()

    products = await fetch_products()
    product_data = products.get(produto_name)

    if not product_data:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            f"Desculpe, o produto '{produto_name}' não foi encontrado em nosso catálogo. Por favor, tente novamente mais tarde."
        )
        return

    preco = product_data["preco"]

    # Edita a mensagem original da lista de produtos para indicar a seleção
    # AQUI ESTÁ A CORREÇÃO: Usamos parse_mode="HTML" para que a tag <b> seja interpretada.
    await query.edit_message_text(
        text=
        f"Você escolheu o produto: <b>{produto_name}</b>. Estamos gerando seu link de pagamento agora mesmo!",
        parse_mode="HTML")

    try:
        print(
            f"Tentando criar preferência de pagamento para {produto_name} (Usuário: {query.from_user.id})..."
        )
        payment_link_response = criar_preferencia_pagamento(
            produto_name, preco, query.from_user.id)

        payment_link = payment_link_response.get("init_point")
        qr_code_base64 = None

        if payment_link_response and "point_of_interaction" in payment_link_response:
            poi = payment_link_response["point_of_interaction"]
            if "transaction_data" in poi and "qr_code_base64" in poi[
                    "transaction_data"]:
                qr_code_base64 = poi["transaction_data"]["qr_code_base64"]

        if qr_code_base64:
            img_bytes = base64.b64decode(qr_code_base64)
            img_stream = BytesIO(img_bytes)

            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=img_stream,
                caption=
                f"Aqui está o QR Code Pix para sua compra de <b>{produto_name}</b> por R${preco:.2f}. Escaneie para pagar com agilidade:",  # Frase mais amigável
                parse_mode="HTML")
            if payment_link:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=
                    f"Ou, se preferir, use o link direto para pagar pelo Mercado Pago: <a href=\"{payment_link}\">Clique aqui para pagar de forma segura!</a>",  # Frase mais amigável
                    parse_mode="HTML")
        elif payment_link:
            mensagem = (
                f"Pronto! Para adquirir <b>{produto_name}</b> por apenas R${preco:.2f}, utilize este link de pagamento seguro do Mercado Pago:\n\n"  # Frase mais amigável
                f"<a href=\"{payment_link}\">Clique aqui para pagar agora!</a>"
            )
            await context.bot.send_message(chat_id=query.message.chat_id,
                                           text=mensagem,
                                           parse_mode="HTML")
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=
                f"Desculpe, não foi possível gerar o link de pagamento para <b>{produto_name}</b> no momento. Por favor, tente novamente mais tarde ou contate o suporte da NTG TECH."
            )

        follow_up_purchase_keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🛒 Fazer Outra Compra",
                                     callback_data='menu_comprar')
            ],
             [
                 InlineKeyboardButton("🏠 Voltar ao Menu Principal",
                                      callback_data='menu_principal')
             ]])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            "Sua solicitação de compra foi processada! O que mais você gostaria de fazer agora? Estamos à disposição!",  # Frase mais amigável
            reply_markup=follow_up_purchase_keyboard)

    except requests.exceptions.RequestException as e:
        print(
            f"ERRO: Falha na comunicação com o Mercado Pago ao gerar link para {produto_name}. Erro: {e}"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            f"Desculpe, houve um erro ao gerar o link de pagamento para <b>{produto_name}</b>. Por favor, tente novamente mais tarde ou contate o suporte da NTG TECH."
        )
        return
    except Exception as e:
        print(
            f"ERRO GERAL: Erro inesperado ao gerar link de pagamento para {produto_name}. Erro: {e}"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=
            f"Desculpe, houve um erro inesperado ao gerar o link de pagamento para <b>{produto_name}</b>. Por favor, tente novamente mais tarde ou contate o suporte da NTG TECH."
        )
        return


# --- Função Original: Cria uma preferência de pagamento no Mercado Pago (API /checkout/preferences) ---
# Retornada ao método original que gera apenas o link.
def criar_preferencia_pagamento(produto_name, preco, telegram_user_id):
    """
    Cria uma preferência de pagamento no Mercado Pago e retorna o JSON completo da resposta.
    """
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise ValueError(
            "MERCADO_PAGO_ACCESS_TOKEN não configurado. Não é possível criar pagamento."
        )

    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "items": [{
            "title": produto_name,
            "quantity": 1,
            "unit_price": preco,
            "currency_id": "BRL"
        }],
        "notification_url":
        WEBHOOK_URL,  # Seu webhook para receber notificações
        "metadata": {
            "telegram_user_id": telegram_user_id,
            "produto": produto_name
        },
        "payment_methods":
        {  # Adiciona Pix como método de pagamento preferencial
            "excluded_payment_methods": [],
            "excluded_payment_types": [],
            "installments": 1,
            "default_payment_method_id": "pix"  # Tenta priorizar Pix
        }
    }
    print(
        f"Payload enviado ao Mercado Pago (Preferência API): notification_url={WEBHOOK_URL}, metadata={body['metadata']}"
    )
    response = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        headers=headers,
        json=body)
    response.raise_for_status()  # Levanta um erro se a requisição não for 2xx
    return response.json()  # Retorna a resposta JSON completa


# --- Inicializa o bot do Telegram ---
def run_telegram_bot_thread_target():
    """
    Função alvo para a thread do bot do Telegram.
    Cria e define um novo loop de evento asyncio para esta thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if not TOKEN:
        print(
            "ERRO CRÍTICO: TOKEN do Telegram não configurado. Bot não pode iniciar."
        )
        return

    app_builder = Application.builder().token(TOKEN)
    app_tg = app_builder.build()

    # Handler para o comando /start
    app_tg.add_handler(CommandHandler("start", start))

    # Handler para QUALQUER mensagem de texto que não seja um comando
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    # Handler para os botões do menu principal E para o botão "Voltar ao Menu Principal" nos vídeos
    app_tg.add_handler(CallbackQueryHandler(main_menu_button,
                                            pattern='^menu_'))

    # Handler para os botões de vídeo (callback_data agora é uma chave curta como 'video_lightroom')
    # O padrão '^video_' captura todos os callbacks que começam com 'video_'
    app_tg.add_handler(
        CallbackQueryHandler(send_video_message, pattern='^video_'))

    # Handler para os botões de produtos (todos os outros callbacks)
    app_tg.add_handler(CallbackQueryHandler(product_button_handler))

    print(
        "Bot do Telegram iniciado no Replit... Aguardando comandos e cliques..."
    )
    app_tg.run_polling(poll_interval=1.0)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_thread = threading.Thread(target=lambda: app_flask.run(
        host='0.0.0.0', port=port, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    print(
        f"Servidor Flask do Bot (Health Check) iniciado em thread separada na porta {port}..."
    )

    run_telegram_bot_thread_target()
    print(f"Bot do Telegram (polling) rodando na thread principal...")
