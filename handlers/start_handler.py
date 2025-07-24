from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from configs import Config
from helpers.database.add_user import AddUserToDatabase
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access

async def start_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        return
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    text = Config.START_TEXT
    if trial_message:
        text += f"\n\n**Note**: {trial_message}"
    await m.reply_text(
        text=text,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        quote=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Developer - @savior_128", url="https://t.me/savior_128")],
                [InlineKeyboardButton("Open Settings", callback_data="openSettings")],
                [InlineKeyboardButton("Close", callback_data="closeMeh")]
            ]
        )
    )

start_handler.filters = filters.private & filters.command("start")