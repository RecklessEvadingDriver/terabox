import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import re
import os

# Replace with your bot token and channel ID
TELEGRAM_TOKEN = "7702695962:AAG6Tqbi5WwgQZsi8UATK3byFwL7gGE_3a0"
FORCE_JOIN_CHANNEL = -1001234567890  # Replace with numeric channel ID

TERABOX_URLS = [
    "mirrobox.com", "nephobox.com", "freeterabox.com", "1024tera.com",
    "4funbox.co", "terabox.app", "terabox.fun", "momerybox.com",
    "tibibox.com", "terabox.com"
]

def get_terabox_info(file_id, password=''):
    api_url = f"https://terabox.hnn.workers.dev/api/get-info?shorturl={file_id}&pwd={password}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_download_link(file_id, password=''):
    info = get_terabox_info(file_id, password)
    if "error" in info or not info.get("list"):
        return "Error fetching file info.", "", ""
    try:
        file_data = info['list'][0]
        post_data = {
            'shareid': info['shareid'],
            'uk': info['uk'],
            'sign': info['sign'],
            'timestamp': info['timestamp'],
            'fs_id': file_data['fs_id']
        }
        response = requests.post(
            "https://terabox.hnn.workers.dev/api/get-download",
            json=post_data,
            timeout=10
        )
        response.raise_for_status()
        download_info = response.json()
        download_link = download_info.get("downloadLink", "Error: Download link not found.")
        file_name = file_data.get("file_name", "Unknown")
        file_size = file_data.get("file_size", "Unknown size")
        return download_link, file_name, file_size
    except Exception as e:
        return f"Error: {str(e)}", "", ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /download <TeraBox URL> to get your file.\n\nFor help, type /help.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here's how you can use the bot:\n\n"
        "/start - Start the bot.\n"
        "/download <TeraBox URL> - Get a download link for a TeraBox file.\n"
        "/feedback <your feedback> - Send feedback to us.\n"
        "Make sure you have joined the channel to use the bot.\n"
        "You can use the download button to directly access the download link.\n"
        "If multiple files are available, you will get multiple download buttons."
    )
    await update.message.reply_text(help_text)

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a TeraBox file URL.")
        return

    url = context.args[0]
    password = context.args[1] if len(context.args) > 1 else ''
    file_id = extract_file_id(url)

    if not file_id:
        await update.message.reply_text("Invalid URL. Please provide a valid TeraBox link.")
        return

    await update.message.reply_text("Processing your request. Please wait...")

    try:
        download_link, file_name, file_size = get_download_link(file_id, password)
        if "Error" not in download_link:
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv']
            is_video = any(file_name.lower().endswith(ext) for ext in video_extensions)

            if is_video:
                keyboard = [
                    [InlineKeyboardButton("Stream Video", url=download_link)],
                    [InlineKeyboardButton("Download Video", url=download_link)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Video: {file_name}\nSize: {file_size}\n\n"
                    "You can stream the video in your browser or download it:",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [[InlineKeyboardButton("Download Now", url=download_link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"File Name: {file_name}\nFile Size: {file_size}",
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(f"Error: {download_link}")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback_message = " ".join(context.args)
    if feedback_message:
        logging.info(f"Feedback received: {feedback_message}")
        await update.message.reply_text("Thank you for your feedback!")
    else:
        await update.message.reply_text("Please provide your feedback after the command.")

async def channel_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        chat_member = await context.bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            await update.message.reply_text(
                "Please join the required channel before using the bot.\n"
                "You can join the channel by clicking [here](https://t.me/Niggasupporter).",
                parse_mode="Markdown"
            )
            return False
    except Exception as e:
        logging.error(f"Error checking channel membership: {str(e)}")
        await update.message.reply_text("An error occurred while checking channel membership. Please try again later.")
        return False

def extract_file_id(url):
    for domain in TERABOX_URLS:
        pattern = rf"https?://{domain}/s/([a-zA-Z0-9_-]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def channel_check_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text and update.message.text.startswith('/'):
        if not await channel_check(update, context):
            return
    await context.next_handler(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Exception while handling an update: {context.error}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_error_handler(error_handler)
    application.add_handler(MessageHandler(filters.ALL, channel_check_middleware), group=-1)
    application.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
