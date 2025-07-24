import asyncio
from configs import Config
from pyrogram import Client
from helpers.display_progress import progress_for_pyrogram
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helpers.database.access_db import db
import time


async def UploadVideo(bot: Client, cb: CallbackQuery, merged_vid_path: str, width: int, height: int, duration: int, video_thumbnail, file_size: int, user_id: int):
    try:
        sent_ = None
        c_time = time.time()
        upload_as_doc = await db.get_upload_as_doc(user_id=user_id)
        if upload_as_doc:
            try:
                sent_ = await bot.send_document(
                    chat_id=user_id,
                    document=merged_vid_path,
                    thumb=video_thumbnail,
                    caption="© @savior_128",
                    progress=progress_for_pyrogram,
                    progress_args=("Uploading as Document ...", cb.message, c_time)
                )
            except Exception as e:
                print(f"Error uploading document: {e}")
                try:
                    await cb.message.edit("Failed to upload as document!")
                except:
                    await cb.message.reply_text("Failed to upload as document!")
        else:
            try:
                sent_ = await bot.send_video(
                    chat_id=user_id,
                    video=merged_vid_path,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=video_thumbnail,
                    caption="© @savior_128",
                    progress=progress_for_pyrogram,
                    progress_args=("Uploading as Video ...", cb.message, c_time)
                )
            except Exception as e:
                print(f"Error uploading video: {e}")
                try:
                    await cb.message.edit("Failed to upload as video!")
                except:
                    await cb.message.reply_text("Failed to upload as video!")
    except Exception as e:
        print(f"Error in UploadVideo: {e}")
        try:
            await cb.message.edit("Failed to upload video!")
        except:
            await cb.message.reply_text("Failed to upload video!")