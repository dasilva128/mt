from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from helpers.database.add_user import AddUserToDatabase
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access
from helpers.database.access_db import db

async def photo_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        return
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    editable = await m.reply_text("Saving Thumbnail to Database ...", quote=True)
    await db.set_thumbnail(m.from_user.id, thumbnail=m.photo.file_id)
    try:
        await editable.edit(
            text="Thumbnail Saved Successfully!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Show Thumbnail", callback_data="showThumbnail")],
                    [InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]
                ]
            )
        )
    except:
        await m.reply_text(
            text="Thumbnail Saved Successfully!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Show Thumbnail", callback_data="showThumbnail")],
                    [InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]
                ]
            ),
            quote=True
        )

photo_handler.filters = filters.private & filters.photo