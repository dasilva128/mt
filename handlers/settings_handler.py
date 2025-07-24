from pyrogram import Client, filters
from pyrogram.types import Message
from helpers.database.add_user import AddUserToDatabase
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access
from helpers.settings import OpenSettings

async def settings_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        return
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    editable = await m.reply_text("Please Wait ...", quote=True)
    try:
        await OpenSettings(editable, m.from_user.id)
    except:
        await m.reply_text("Opening settings failed. Please try again.", quote=True)

settings_handler.filters = filters.private & filters.command("settings")