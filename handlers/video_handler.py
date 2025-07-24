from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, Message
from configs import Config
from helpers.database.add_user import AddUserToDatabase
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access
from helpers.markup_maker import MakeButtons
from helpers.clean import delete_all
import os
import asyncio

QueueDB = {}
ReplyDB = {}

async def videos_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        return
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    media = m.video or m.document
    if media.file_name is None:
        await m.reply_text("File Name Not Found!")
        return
    if media.file_name.rsplit(".", 1)[-1].lower() not in ["mp4", "mkv", "webm"]:
        await m.reply_text("This Video Format not Allowed!\nOnly send MP4 or MKV or WEBM.", quote=True)
        return
    if QueueDB.get(m.from_user.id, None) is None:
        QueueDB.update({m.from_user.id: []})
    input_ = f"{Config.DOWN_PATH}/{m.from_user.id}/input.txt"
    if len(QueueDB.get(m.from_user.id, [])) > 0 and os.path.exists(input_):
        await m.reply_text("Sorry,\nAlready one process in progress!\nPlease wait or cancel the current process.", quote=True)
        return
    if os.path.exists(f"{Config.DOWN_PATH}/{m.from_user.id}/"):
        await delete_all(root=f"{Config.DOWN_PATH}/{m.from_user.id}/")
    editable = await m.reply_text("Please Wait ...", quote=True)
    MessageText = "Okay,\nNow send me the next video or press **Merge Now** button!"
    QueueDB.get(m.from_user.id).append(m.id)
    if ReplyDB.get(m.from_user.id, None) is not None:
        try:
            await bot.delete_messages(chat_id=m.chat.id, message_ids=ReplyDB.get(m.from_user.id))
        except:
            pass
    await asyncio.sleep(Config.TIME_GAP)
    if len(QueueDB.get(m.from_user.id)) == Config.MAX_VIDEOS:
        MessageText = "Okay, now press **Merge Now** button!"
    markup = await MakeButtons(bot, m, QueueDB)
    try:
        await editable.edit(text="Your video added to queue!")
        reply_ = await m.reply_text(
            text=MessageText,
            reply_markup=InlineKeyboardMarkup(markup),
            quote=True
        )
        ReplyDB.update({m.from_user.id: reply_.id})
    except:
        reply_ = await m.reply_text(
            text="Your video added to queue!\n" + MessageText,
            reply_markup=InlineKeyboardMarkup(markup),
            quote=True
        )
        ReplyDB.update({m.from_user.id: reply_.id})

videos_handler.filters = filters.private & (filters.video | filters.document)