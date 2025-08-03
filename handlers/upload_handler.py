# (c) @savior_128

import os
import time
import random
import asyncio
import logging
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto
from configs import Config
from helpers.uploader import UploadVideo
from helpers.database.access_db import get_db
from helpers.clean import delete_all
from helpers.ffmpeg import generate_screen_shots, cult_small_video
from helpers.display_progress import progress_for_pyrogram, humanbytes, show_loading_animation
from helpers.state import QueueDB, FormtDB, RenameDB, update_queue_db, update_formt_db
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from PIL import Image
from pyrogram import enums

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def proceed_with_upload(bot: Client, update: Message | CallbackQuery, merged_vid_path: str, user_id: int):
    """Upload merged video, screenshots, and sample video."""
    cb = update if isinstance(update, CallbackQuery) else None
    message = update.message if isinstance(update, CallbackQuery) else update
    try:
        message = await show_loading_animation(message, "Extracting Video Data...")
    except Exception as e:
        logger.warning(f"Failed to show loading animation for user {user_id}: {e}")
        message = await bot.send_message(user_id, "Extracting Video Data...", parse_mode=enums.ParseMode.MARKDOWN)

    duration = 1
    width = 100
    height = 100
    try:
        metadata = extractMetadata(createParser(merged_vid_path))
        if metadata.has("duration"):
            duration = metadata.get('duration').seconds
        if metadata.has("width"):
            width = metadata.get("width")
        if metadata.has("height"):
            height = metadata.get("height")
    except Exception as e:
        logger.error(f"Error extracting metadata for user {user_id}: {e}")
        await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
        await update_queue_db(user_id, [])
        await update_formt_db(user_id, None)
        await message.edit(f"The merged video is corrupted! Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        return

    video_thumbnail = None
    db = await get_db()
    db_thumbnail = await db.get_thumbnail(id=user_id)
    if db_thumbnail and os.path.exists(db_thumbnail):
        video_thumbnail = db_thumbnail
        try:
            Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
            img = Image.open(video_thumbnail)
            img.resize((width, height))
            img.save(video_thumbnail, "JPEG")
        except Exception as e:
            logger.error(f"Error processing thumbnail for user {user_id}: {e}")
            video_thumbnail = None
    else:
        video_thumbnail = f"{Config.DOWN_PATH}/{user_id}/{str(time.time())}.jpg"
        ttl = random.randint(0, int(duration) - 1)
        file_generator_command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-ss",
            str(ttl),
            "-i",
            merged_vid_path,
            "-vframes",
            "1",
            video_thumbnail,
            "-y"
        ]
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024
        )
        stdout, stderr = await process.communicate()
        if stderr:
            logger.error(f"FFmpeg error generating thumbnail: {stderr.decode()}")
        if os.path.exists(video_thumbnail):
            try:
                Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
                img = Image.open(video_thumbnail)
                img.resize((width, height))
                img.save(video_thumbnail, "JPEG")
            except Exception as e:
                logger.error(f"Error processing generated thumbnail for user {user_id}: {e}")
                video_thumbnail = None
        else:
            video_thumbnail = None

    file_size = os.path.getsize(merged_vid_path)
    try:
        sent_message = await UploadVideo(
            bot=bot,
            update=update,
            merged_vid_path=merged_vid_path,
            width=width,
            height=height,
            duration=duration,
            video_thumbnail=video_thumbnail,
            file_size=file_size,
            user_id=user_id
        )
        if not sent_message:
            logger.error(f"Failed to upload video for user {user_id}")
            await message.edit("Failed to upload video to user!", parse_mode=enums.ParseMode.MARKDOWN)
            return
    except Exception as e:
        logger.error(f"Error uploading video for user {user_id}: {e}")
        await message.edit(f"Failed to upload video! Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        return

    caption = "© @savior_128"
    db = await get_db()
    if await db.get_generate_ss(id=user_id):
        try:
            message = await show_loading_animation(message, "Generating Screenshots...")
            generate_ss_dir = f"{Config.DOWN_PATH}/{user_id}"
            list_images = await generate_screen_shots(merged_vid_path, generate_ss_dir, 9, duration)
            if list_images is None:
                await message.edit("Failed to generate screenshots!", parse_mode=enums.ParseMode.MARKDOWN)
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await message.edit("Generated screenshots successfully!\nUploading...", parse_mode=enums.ParseMode.MARKDOWN)
                photo_album = []
                for i, image in enumerate(list_images):
                    if os.path.exists(image):
                        if i == 0:
                            photo_album.append(InputMediaPhoto(media=image, caption=caption, parse_mode=enums.ParseMode.MARKDOWN))
                        else:
                            photo_album.append(InputMediaPhoto(media=image))
                if photo_album:
                    await bot.send_media_group(chat_id=user_id, media=photo_album)
                    if Config.LOG_CHANNEL and Config.LOG_CHANNEL.strip():
                        try:
                            channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                            await bot.send_media_group(
                                chat_id=channel_id,
                                media=photo_album,
                                caption=f"Screenshots for merged video by user {user_id}\n© @savior_128",
                                parse_mode=enums.ParseMode.MARKDOWN
                            )
                            logger.info(f"Screenshots sent to channel {Config.LOG_CHANNEL} for user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to send screenshots to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
                            await message.reply_text(f"Failed to log screenshots to channel: {e}", parse_mode=enums.ParseMode.MARKDOWN)
                else:
                    await message.edit("No valid screenshots generated!", parse_mode=enums.ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error generating/uploading screenshots for user {user_id}: {e}")
            await message.edit(f"Error generating screenshots: {e}", parse_mode=enums.ParseMode.MARKDOWN)

    db = await get_db()
    if (await db.get_generate_sample_video(id=user_id)) and (duration >= 15):
        try:
            message = await show_loading_animation(message, "Generating Sample Video...")
            sample_vid_dir = f"{Config.DOWN_PATH}/{user_id}/"
            ttl = int(duration * 10 / 100)
            sample_video = await cult_small_video(
                video_file=merged_vid_path,
                output_directory=sample_vid_dir,
                start_time=ttl,
                end_time=(ttl + 10),
                format_=RenameDB.get(user_id, {}).get("format", "mp4")
            )
            if sample_video is None or not os.path.exists(sample_video):
                await message.edit("Failed to generate sample video!", parse_mode=enums.ParseMode.MARKDOWN)
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await message.edit("Generated sample video successfully!\nUploading...", parse_mode=enums.ParseMode.MARKDOWN)
                sam_vid_duration = 5
                sam_vid_width = 100
                sam_vid_height = 100
                try:
                    metadata = extractMetadata(createParser(sample_video))
                    if metadata.has("duration"):
                        sam_vid_duration = metadata.get('duration').seconds
                    if metadata.has("width"):
                        sam_vid_width = metadata.get("width")
                    if metadata.has("height"):
                        sam_vid_height = metadata.get("height")
                except Exception as e:
                    logger.error(f"Error extracting sample video metadata for user {user_id}: {e}")
                    await message.edit("Sample video file corrupted!", parse_mode=enums.ParseMode.MARKDOWN)
                    await asyncio.sleep(Config.TIME_GAP)
                    return
                try:
                    c_time = time.time()
                    await bot.send_video(
                        chat_id=user_id,
                        video=sample_video,
                        thumb=video_thumbnail,
                        width=sam_vid_width,
                        height=sam_vid_height,
                        duration=sam_vid_duration,
                        caption=caption,
                        progress=progress_for_pyrogram,
                        progress_args=("Uploading Sample Video...", message, c_time),
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                    if Config.LOG_CHANNEL and Config.LOG_CHANNEL.strip():
                        try:
                            channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                            await bot.send_video(
                                chat_id=channel_id,
                                video=sample_video,
                                thumb=video_thumbnail,
                                width=sam_vid_width,
                                height=sam_vid_height,
                                duration=sam_vid_duration,
                                caption=f"Sample video for merged video by user {user_id}\n© @savior_128",
                                parse_mode=enums.ParseMode.MARKDOWN
                            )
                            logger.info(f"Sample video sent to channel {Config.LOG_CHANNEL} for user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to send sample video to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
                            await message.reply_text(f"Failed to log sample video to channel: {e}", parse_mode=enums.ParseMode.MARKDOWN)
                except Exception as e:
                    logger.error(f"Error uploading sample video for user {user_id}: {e}")
                    await message.edit(f"Failed to upload sample video! Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
                    await asyncio.sleep(Config.TIME_GAP)
        except Exception as e:
            logger.error(f"Error generating sample video for user {user_id}: {e}")
            await message.edit(f"Error generating sample video: {e}", parse_mode=enums.ParseMode.MARKDOWN)

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete upload status message for user {user_id}: {e}")
    await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
    await update_queue_db(user_id, [])
    await update_formt_db(user_id, None)
    logger.info(f"Upload process completed for user {user_id}")