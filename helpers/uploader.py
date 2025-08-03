# (c) @savior_128

import os
import time
import asyncio
import logging
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from configs import Config
from helpers.database.access_db import get_db
from helpers.display_progress import progress_for_pyrogram, show_loading_animation
from pyrogram import enums

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def UploadVideo(bot: Client, update: Message | CallbackQuery, merged_vid_path: str, width: int, height: int, duration: int, video_thumbnail: str, file_size: int, user_id: int):
    """Upload video or document to user."""
    cb = isinstance(update, CallbackQuery)
    message = update.message if cb else update
    try:
        c_time = time.time()
        db = await get_db()
        upload_as_doc = await db.get_upload_as_doc(id=user_id)
        caption = "© @savior_128"
        if upload_as_doc:
            sent_message = await bot.send_document(
                chat_id=user_id,
                document=merged_vid_path,
                thumb=video_thumbnail,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Uploading Document...", message, c_time),
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            sent_message = await bot.send_video(
                chat_id=user_id,
                video=merged_vid_path,
                duration=duration,
                width=width,
                height=height,
                thumb=video_thumbnail,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Uploading Video...", message, c_time),
                parse_mode=enums.ParseMode.MARKDOWN
            )
        if Config.LOG_CHANNEL and Config.LOG_CHANNEL.strip():
            try:
                channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                if upload_as_doc:
                    await bot.send_document(
                        chat_id=channel_id,
                        document=merged_vid_path,
                        thumb=video_thumbnail,
                        caption=f"Merged video by user {user_id}\n© @savior_128",
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                else:
                    await bot.send_video(
                        chat_id=channel_id,
                        video=merged_vid_path,
                        duration=duration,
                        width=width,
                        height=height,
                        thumb=video_thumbnail,
                        caption=f"Merged video by user {user_id}\n© @savior_128",
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                logger.info(f"Video sent to channel {Config.LOG_CHANNEL} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send video to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
                await message.reply_text(f"Failed to log video to channel: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        return sent_message
    except Exception as e:
        logger.error(f"Error uploading video for user {user_id}: {e}")
        try:
            await message.edit(f"Failed to upload video! Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        except:
            await message.reply_text(f"Failed to upload video! Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        return None