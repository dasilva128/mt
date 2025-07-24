from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helpers.database.access_db import db

async def OpenSettings(m: Message, user_id: int):
    try:
        upload_as_doc = await db.get_upload_as_doc(user_id)
        gen_ss = await db.get_generate_ss(user_id)
        gen_sample = await db.get_generate_sample_video(user_id)
        db_thumbnail = await db.get_thumbnail(user_id)
        buttons = [
            [
                InlineKeyboardButton(
                    f"Upload as {'Video' if not upload_as_doc else 'Document'} ✅",
                    callback_data="triggerUploadMode"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{'✅' if gen_ss else '❌'} Generate Screenshots",
                    callback_data="triggerGenSS"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{'✅' if gen_sample else '❌'} Generate Sample Video",
                    callback_data="triggerGenSample"
                )
            ],
            [
                InlineKeyboardButton(
                    "Show Queue Files",
                    callback_data="showQueueFiles"
                )
            ]
        ]
        if db_thumbnail is not None:
            buttons.append([InlineKeyboardButton("Show Thumbnail", callback_data="showThumbnail")])
        buttons.append([InlineKeyboardButton("Close", callback_data="closeMeh")])
        await m.edit(
            text="Here You can control Bot Settings",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as err:
        print(f"Error in OpenSettings: {err}")
        await m.edit("Something went wrong!")
        raise err