# (c) @savior_128

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, LinkPreviewOptions
from configs import Config
from helpers.database.add_user import AddUserToDatabase
from helpers.payment import check_user_access
from handlers.video_handler import videos_handler, convert_callback, convert_format_callback, compress_callback, merge_now_callback, clear_files_callback
from handlers.callback_handlers import callback_handlers, cancel_callback
from handlers.text_handler import handle_file_name

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Client(
    "NubBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

async def start_command(client: Client, message: Message):
    """Handle the /start command."""
    user_id = message.from_user.id
    logger.info(f"Received /start from user {user_id}")
    await AddUserToDatabase(client, message)
    access, trial_message = await check_user_access(client, message, None)
    
    if user_id == Config.BOT_OWNER:
        await message.reply_text(
            Config.START_TEXT,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Developer - @savior_128", url="https://t.me/savior_128")],
                    [InlineKeyboardButton("Open Settings", callback_data="openSettings")]
                ]
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return

    if not access:
        if not trial_message or not isinstance(trial_message, str):
            trial_message = "Your trial has expired. Please contact @savior_128 to subscribe."
        await message.reply_text(
            trial_message,
            quote=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Owner", url="https://t.me/savior_128")]]
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return

    reply_text = f"{Config.START_TEXT}\n\n{trial_message}" if trial_message else Config.START_TEXT
    await message.reply_text(
        reply_text,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Developer - @savior_128", url="https://t.me/savior_128")],
                [InlineKeyboardButton("Open Settings", callback_data="openSettings")]
            ]
        ),
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

app.on_message(filters.command("start"))(start_command)
app.on_message(filters=handle_file_name.filters)(handle_file_name)
app.on_message(filters=videos_handler.filters)(videos_handler)
app.on_callback_query(filters.regex(r"convert_\d+"))(convert_callback)
app.on_callback_query(filters.regex(r"convert_format_\d+_(mp4|mkv|webm)"))(convert_format_callback)
app.on_callback_query(filters.regex(r"compress_\d+"))(compress_callback)
app.on_callback_query(filters.regex(r"merge_\d+"))(merge_now_callback)
app.on_callback_query(filters.regex(r"clearFiles_\d+"))(clear_files_callback)
app.on_callback_query(filters.regex(r"cancelProcess|showFileName_\d+|refreshFsub|showThumbnail|deleteThumbnail|triggerUploadMode|showQueueFiles|removeFile_\d+|triggerGenSS|triggerGenSample|openSettings|renameFile_(Yes|No)|closeMeh"))(callback_handlers)
app.on_callback_query(filters.regex(r"cancel_\d+"))(cancel_callback)

async def main():
    try:
        await app.start()
        logger.info("Bot started successfully")
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await app.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Event loop closed")