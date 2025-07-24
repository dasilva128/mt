from pyrogram import Client, filters
from pyrogram.types import Message
from configs import Config
from helpers.database.access_db import db
from helpers.payment import check_user_access
import string
import os
import asyncio

RenameDB = {}

async def handle_file_name(bot: Client, m: Message):
    user_id = m.from_user.id
    print(f"Received text message from user {user_id}: {m.text}")
    if user_id not in RenameDB:
        print(f"User {user_id} not in RenameDB")
        return
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        print(f"Access denied for user {user_id}")
        return
    merged_vid_path = RenameDB[user_id]["merged_vid_path"]
    format_ = RenameDB[user_id]["format"]
    new_name = m.text.strip()
    print(f"Processing new file name: {new_name}")
    if not new_name:
        await m.reply_text("File name cannot be empty! Please send a valid name.")
        return
    ascii_ = ''.join([i if (i in string.digits or i in string.ascii_letters or i == " ") else "" for i in new_name])
    if not ascii_:
        await m.reply_text("File name contains invalid characters! Use only letters, numbers, and spaces.")
        return
    new_file_name = f"{Config.DOWN_PATH}/{str(user_id)}/{ascii_.replace(' ', '_')}.{format_}"
    await m.reply_text(f"Renaming file to `{new_file_name.rsplit('/', 1)[-1]}`")
    try:
        os.rename(merged_vid_path, new_file_name)
        merged_vid_path = new_file_name
    except Exception as e:
        print(f"Failed to rename file for user {user_id}: {e}")
        await m.reply_text(f"Failed to rename file: {e}")
        return
    await asyncio.sleep(2)
    from handlers.upload_handler import proceed_with_upload
    await proceed_with_upload(bot, m, merged_vid_path, user_id)
    del RenameDB[user_id]
    print(f"File renamed and uploaded for user {user_id}")

handle_file_name.filters = filters.private & filters.text