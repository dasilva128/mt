# (c) @savior_128

import os
import time
import asyncio
import logging
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from configs import Config
from helpers.database.access_db import get_db
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access
from helpers.markup_maker import MakeButtons
from helpers.clean import delete_all
from helpers.state import QueueDB, ReplyDB, update_queue_db, update_reply_db, get_queue_db, get_reply_db
from helpers.display_progress import show_loading_animation
from handlers.upload_handler import proceed_with_upload
from pyrogram import enums

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg not installed or not working: {stderr.decode()}")
            raise Exception("FFmpeg is not installed or not working properly!")
    except Exception as e:
        logger.error(f"Error checking FFmpeg: {e}")
        raise

async def convert_video_format(file_path: str, output_dir: str, user_id: int, output_format: str) -> str | None:
    """Convert video to the specified format using FFmpeg."""
    await check_ffmpeg()
    output_file = f"{output_dir}/{user_id}/converted_{time.time()}.{output_format}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", file_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-threads", "1",
        "-y", output_file
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024
        )
        stdout, stderr = await process.communicate()
        if stderr:
            logger.error(f"FFmpeg error converting video for user {user_id}: {stderr.decode()}")
            return None
        if os.path.exists(output_file):
            logger.info(f"Video converted successfully for user {user_id}: {output_file}")
            return output_file
        return None
    except Exception as e:
        logger.error(f"Error converting video for user {user_id}: {e}")
        return None

async def compress_video(file_path: str, output_dir: str, user_id: int) -> str | None:
    """Compress video using FFmpeg."""
    await check_ffmpeg()
    output_file = f"{output_dir}/{user_id}/compressed_{time.time()}.mp4"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", file_path,
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "1",
        "-y", output_file
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024
        )
        stdout, stderr = await process.communicate()
        if stderr:
            logger.error(f"FFmpeg error compressing video for user {user_id}: {stderr.decode()}")
            return None
        if os.path.exists(output_file):
            logger.info(f"Video compressed successfully for user {user_id}: {output_file}")
            return output_file
        return None
    except Exception as e:
        logger.error(f"Error compressing video for user {user_id}: {e}")
        return None

async def merge_videos(file_list: str, output_dir: str, user_id: int) -> str | None:
    """Merge videos listed in a text file using FFmpeg."""
    await check_ffmpeg()
    output_file = f"{output_dir}/{user_id}/merged_{time.time()}.mp4"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", file_list,
        "-c:v", "copy",
        "-c:a", "copy",
        "-y", output_file
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024
        )
        stdout, stderr = await process.communicate()
        if stderr:
            logger.error(f"FFmpeg error merging videos for user {user_id}: {stderr.decode()}")
            return None
        if os.path.exists(output_file):
            logger.info(f"Videos merged successfully for user {user_id}: {output_file}")
            return output_file
        return None
    except Exception as e:
        logger.error(f"Error merging videos for user {user_id}: {e}")
        return None

async def videos_handler(bot: Client, m: Message):
    """Handle video or document messages and add them to the queue."""
    user_id = m.from_user.id
    db = await get_db()
    await db.add_user(id=user_id)
    access, trial_message = await check_user_access(bot, m, None)
    if not access:
        logger.info(f"User {user_id} denied access due to payment check")
        return
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        logger.info(f"User {user_id} failed force subscribe")
        return
    media = m.video or m.document
    file_name = media.file_name if media.file_name else f"video_{user_id}_{int(time.time())}.mp4"
    file_name = re.sub(r'[^\w\-\.]', '_', file_name)
    logger.info(f"Processing video for user {user_id}: {file_name}")
    if file_name.rsplit(".", 1)[-1].lower() not in ["mp4", "mkv", "webm"]:
        await m.reply_text(
            text="This video format is not allowed!\nOnly send MP4, MKV, or WEBM.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        logger.info(f"User {user_id} sent invalid format: {file_name}")
        return
    async with QueueDB_lock:
        if await get_queue_db(user_id) is None:
            await update_queue_db(user_id, [])
    input_ = f"{Config.DOWN_PATH}/{user_id}/input.txt"
    if len(await get_queue_db(user_id)) > 0 and os.path.exists(input_):
        await m.reply_text(
            text="Sorry, a process is already in progress!\nPlease wait or cancel the current process.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        logger.info(f"User {user_id} has ongoing process")
        return
    user_dir = f"{Config.DOWN_PATH}/{user_id}/"
    os.makedirs(user_dir, exist_ok=True)
    editable = await m.reply_text(
        text="Please wait...",
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )
    try:
        logger.info(f"Downloading video for user {user_id}: {file_name}")
        video_path = await bot.download_media(
            message=media,
            file_name=f"{user_dir}{file_name}"
        )
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Failed to download video for user {user_id}: Path is None or does not exist")
            await editable.edit("Video download failed! Invalid file path.", parse_mode=enums.ParseMode.MARKDOWN)
            return
        logger.info(f"Video saved successfully: {video_path}")
        MessageText = (
            "Okay, now send the next video or select an option below!"
        )
        async with QueueDB_lock:
            queue = await get_queue_db(user_id)
            queue.append(m.id)
            await update_queue_db(user_id, queue)
        async with ReplyDB_lock:
            reply_id = await get_reply_db(user_id)
            if reply_id is not None:
                try:
                    await bot.delete_messages(chat_id=m.chat.id, message_ids=reply_id)
                except Exception as e:
                    logger.error(f"Error deleting previous reply for user {user_id}: {e}")
        await asyncio.sleep(Config.TIME_GAP)
        if len(await get_queue_db(user_id)) == Config.MAX_VIDEOS:
            MessageText = (
                "Okay, now press **Merge Now** button or select another option!"
            )
        markup = await MakeButtons(bot, m, await get_queue_db(user_id))
        markup.append([
            InlineKeyboardButton("Merge Now", callback_data=f"merge_{user_id}"),
            InlineKeyboardButton("Convert Format", callback_data=f"convert_{user_id}"),
            InlineKeyboardButton("Compress", callback_data=f"compress_{user_id}"),
            InlineKeyboardButton("Clear Queue", callback_data=f"clearFiles_{user_id}")
        ])
        try:
            await editable.edit(text="Your video has been added to the queue!", parse_mode=enums.ParseMode.MARKDOWN)
            reply_ = await m.reply_text(
                text=MessageText,
                reply_markup=InlineKeyboardMarkup(markup),
                quote=True,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await update_reply_db(user_id, reply_.id)
            logger.info(f"Queue updated for user {user_id}, reply ID: {reply_.id}")
        except Exception as e:
            logger.error(f"Error updating message for user {user_id}: {e}")
            reply_ = await m.reply_text(
                text="Your video has been added to the queue!\n" + MessageText,
                reply_markup=InlineKeyboardMarkup(markup),
                quote=True,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await update_reply_db(user_id, reply_.id)
    except Exception as e:
        logger.error(f"Error processing video for user {user_id}: {e}")
        await editable.edit(f"Error processing video: {e}", parse_mode=enums.ParseMode.MARKDOWN)
    finally:
        try:
            await editable.delete()
        except Exception as e:
            logger.warning(f"Failed to delete temporary message for user {user_id}: {e}")

async def convert_callback(bot: Client, query: CallbackQuery):
    """Handle convert callback to show format selection menu."""
    data = query.data
    logger.info(f"Convert callback triggered for user {query.from_user.id}, data: {data}")
    if not data.startswith("convert_") or len(data.split("_")) != 2:
        logger.error(f"Invalid convert callback data: {data}")
        await query.answer("Invalid data!", show_alert=True)
        return
    try:
        user_id = int(data.split("_")[1])
    except ValueError:
        logger.error(f"Invalid user_id in convert callback: {data}")
        await query.answer("Error processing data!", show_alert=True)
        return
    if user_id != query.from_user.id:
        await query.answer("This command is not for you!", show_alert=True)
        logger.info(f"Unauthorized convert callback by user {query.from_user.id}")
        return
    markup = [
        [
            InlineKeyboardButton("MP4", callback_data=f"convert_format_{user_id}_mp4"),
            InlineKeyboardButton("MKV", callback_data=f"convert_format_{user_id}_mkv"),
            InlineKeyboardButton("WEBM", callback_data=f"convert_format_{user_id}_webm")
        ]
    ]
    try:
        await query.message.edit(
            text="Please select the output format:",
            reply_markup=InlineKeyboardMarkup(markup),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        logger.info(f"Format selection menu shown for user {user_id}")
    except Exception as e:
        logger.error(f"Error in convert_callback for user {user_id}: {e}")
        await query.answer("Error displaying format menu!", show_alert=True)

async def convert_format_callback(bot: Client, query: CallbackQuery):
    """Handle format conversion callback."""
    data = query.data
    logger.info(f"Convert format callback triggered for user {query.from_user.id}, data: {data}")
    if not data.startswith("convert_format_"):
        logger.error(f"Invalid convert_format callback data: {data}")
        await query.answer("Invalid data!", show_alert=True)
        return
    try:
        parts = data.split("_")
        if len(parts) != 3:
            logger.error(f"Invalid convert_format callback format: {data}")
            await query.answer("Invalid data format!", show_alert=True)
            return
        user_id = int(parts[1])
        output_format = parts[2].lower()
    except ValueError as e:
        logger.error(f"Error parsing convert_format callback data: {data}, error: {e}")
        await query.answer("Error processing data!", show_alert=True)
        return
    if user_id != query.from_user.id:
        await query.answer("This command is not for you!", show_alert=True)
        logger.info(f"Unauthorized convert_format callback by user {query.from_user.id}")
        return
    queue = await get_queue_db(user_id)
    if not queue:
        await query.message.edit("No videos in queue!", parse_mode=enums.ParseMode.MARKDOWN)
        logger.info(f"No videos in queue for user {user_id}")
        return
    try:
        message = await bot.get_messages(query.message.chat.id, queue[-1])
        media = message.video or message.document
        file_name = media.file_name or f"video_{user_id}_{int(time.time())}.{output_format}"
        file_name = re.sub(r'[^\w\-\.]', '_', file_name)
        user_dir = f"{Config.DOWN_PATH}/{user_id}/"
        os.makedirs(user_dir, exist_ok=True)
        editable = await show_loading_animation(query.message, "Converting video format...")
        logger.info(f"Downloading video for conversion for user {user_id}: {file_name}")
        video_path = await bot.download_media(
            message=media,
            file_name=f"{user_dir}{file_name}"
        )
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Failed to download video for user {user_id}: Path is None or does not exist")
            await editable.edit("Video download failed!", parse_mode=enums.ParseMode.MARKDOWN)
            return
        logger.info(f"Video saved for conversion: {video_path}")
        converted_file = await convert_video_format(
            file_path=video_path,
            output_dir=Config.DOWN_PATH,
            user_id=user_id,
            output_format=output_format
        )
        if converted_file and os.path.exists(converted_file):
            await bot.send_video(
                chat_id=user_id,
                video=converted_file,
                caption="Converted video\n© @savior_128",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await delete_all(root=user_dir)
            logger.info(f"Video converted and sent to user {user_id}: {converted_file}")
        else:
            await editable.edit("Format conversion failed!", parse_mode=enums.ParseMode.MARKDOWN)
            logger.error(f"Video conversion failed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in convert_format_callback for user {user_id}: {e}")
        await editable.edit(f"Error in format conversion: {e}", parse_mode=enums.ParseMode.MARKDOWN)
    finally:
        try:
            await editable.delete()
        except Exception as e:
            logger.warning(f"Failed to delete temporary message for user {user_id}: {e}")

async def compress_callback(bot: Client, query: CallbackQuery):
    """Handle video compression callback."""
    data = query.data
    logger.info(f"Compress callback triggered for user {query.from_user.id}, data: {data}")
    try:
        user_id = int(data.split("_")[1])
    except ValueError:
        logger.error(f"Invalid compress callback data: {data}")
        await query.answer("Invalid data!", show_alert=True)
        return
    if user_id != query.from_user.id:
        await query.answer("This command is not for you!", show_alert=True)
        logger.info(f"Unauthorized compress callback by user {query.from_user.id}")
        return
    queue = await get_queue_db(user_id)
    if not queue:
        await query.message.edit("No videos in queue!", parse_mode=enums.ParseMode.MARKDOWN)
        logger.info(f"No videos in queue for user {user_id}")
        return
    try:
        message = await bot.get_messages(query.message.chat.id, queue[-1])
        media = message.video or message.document
        file_name = media.file_name or f"video_{user_id}_{int(time.time())}.mp4"
        file_name = re.sub(r'[^\w\-\.]', '_', file_name)
        user_dir = f"{Config.DOWN_PATH}/{user_id}/"
        os.makedirs(user_dir, exist_ok=True)
        editable = await show_loading_animation(query.message, "Compressing video...")
        logger.info(f"Downloading video for compression for user {user_id}: {file_name}")
        video_path = await bot.download_media(
            message=media,
            file_name=f"{user_dir}{file_name}"
        )
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Failed to download video for user {user_id}: Path is None or does not exist")
            await editable.edit("Video download failed!", parse_mode=enums.ParseMode.MARKDOWN)
            return
        logger.info(f"Video saved for compression: {video_path}")
        compressed_file = await compress_video(
            file_path=video_path,
            output_dir=Config.DOWN_PATH,
            user_id=user_id
        )
        if compressed_file and os.path.exists(compressed_file):
            await bot.send_video(
                chat_id=user_id,
                video=compressed_file,
                caption="Compressed video\n© @savior_128",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await delete_all(root=user_dir)
            logger.info(f"Video compressed and sent to user {user_id}: {compressed_file}")
        else:
            await editable.edit("Compression failed!", parse_mode=enums.ParseMode.MARKDOWN)
            logger.error(f"Video compression failed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in compress_callback for user {user_id}: {e}")
        await editable.edit(f"Error in compression: {e}", parse_mode=enums.ParseMode.MARKDOWN)
    finally:
        try:
            await editable.delete()
        except Exception as e:
            logger.warning(f"Failed to delete temporary message for user {user_id}: {e}")

async def merge_now_callback(bot: Client, query: CallbackQuery):
    """Handle video merging callback."""
    data = query.data
    logger.info(f"Merge callback triggered for user {query.from_user.id}, data: {data}")
    try:
        user_id = int(data.split("_")[1])
    except ValueError:
        logger.error(f"Invalid merge callback data: {data}")
        await query.answer("Invalid data!", show_alert=True)
        return
    if user_id != query.from_user.id:
        await query.answer("This command is not for you!", show_alert=True)
        logger.info(f"Unauthorized merge callback by user {query.from_user.id}")
        return
    queue = await get_queue_db(user_id)
    if not queue:
        await query.message.edit("No videos in queue to merge!", parse_mode=enums.ParseMode.MARKDOWN)
        logger.info(f"No videos in queue for user {user_id}")
        return
    try:
        user_dir = f"{Config.DOWN_PATH}/{user_id}/"
        os.makedirs(user_dir, exist_ok=True)
        input_file = f"{user_dir}input.txt"
        with open(input_file, "w") as input_list:
            for message_id in queue:
                message = await bot.get_messages(query.message.chat.id, message_id)
                media = message.video or message.document
                file_name = media.file_name or f"video_{user_id}_{int(time.time())}.mp4"
                file_name = re.sub(r'[^\w\-\.]', '_', file_name)
                video_path = await bot.download_media(
                    message=media,
                    file_name=f"{user_dir}{file_name}"
                )
                if not video_path or not os.path.exists(video_path):
                    logger.error(f"Failed to download video for merging for user {user_id}: {file_name}")
                    await query.message.edit("Failed to download videos for merging!", parse_mode=enums.ParseMode.MARKDOWN)
                    return
                input_list.write(f"file '{video_path}'\n")
        logger.info(f"Input file created for merging for user {user_id}: {input_file}")
        editable = await show_loading_animation(query.message, "Merging videos...")
        merged_file = await merge_videos(
            file_list=input_file,
            output_dir=Config.DOWN_PATH,
            user_id=user_id
        )
        if merged_file and os.path.exists(merged_file):
            await editable.edit("Merging completed! Would you like to rename the merged file?", 
                              reply_markup=InlineKeyboardMarkup(
                                  [
                                      [InlineKeyboardButton("Yes", callback_data="renameFile_Yes")],
                                      [InlineKeyboardButton("No", callback_data="renameFile_No")]
                                  ]
                              ),
                              parse_mode=enums.ParseMode.MARKDOWN)
            from helpers.state import update_rename_db
            await update_rename_db(user_id, {"merged_vid_path": merged_file, "format": "mp4"})
            logger.info(f"Videos merged for user {user_id}: {merged_file}")
        else:
            await editable.edit("Merging failed!", parse_mode=enums.ParseMode.MARKDOWN)
            await delete_all(root=user_dir)
            await update_queue_db(user_id, [])
            logger.error(f"Video merging failed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in merge_now_callback for user {user_id}: {e}")
        await editable.edit(f"Error in merging videos: {e}", parse_mode=enums.ParseMode.MARKDOWN)
        await delete_all(root=user_dir)
        await update_queue_db(user_id, [])
    finally:
        try:
            await editable.delete()
        except Exception as e:
            logger.warning(f"Failed to delete temporary message for user {user_id}: {e}")

async def clear_files_callback(bot: Client, query: CallbackQuery):
    """Handle clearing of video queue and temporary files."""
    data = query.data
    logger.info(f"Clear files callback triggered for user {query.from_user.id}, data: {data}")
    try:
        user_id = int(data.split("_")[1])
    except ValueError:
        logger.error(f"Invalid clear files callback data: {data}")
        await query.answer("Invalid data!", show_alert=True)
        return
    if user_id != query.from_user.id:
        await query.answer("This command is not for you!", show_alert=True)
        logger.info(f"Unauthorized clear files callback by user {query.from_user.id}")
        return
    try:
        user_dir = f"{Config.DOWN_PATH}/{user_id}/"
        await delete_all(root=user_dir)
        await update_queue_db(user_id, [])
        await update_reply_db(user_id, None)
        await query.message.edit("Queue and temporary files cleared successfully!", parse_mode=enums.ParseMode.MARKDOWN)
        logger.info(f"Queue and files cleared for user {user_id}")
    except Exception as e:
        logger.error(f"Error in clear_files_callback for user {user_id}: {e}")
        await query.message.edit(f"Error clearing files: {e}", parse_mode=enums.ParseMode.MARKDOWN)
    finally:
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete temporary message for user {user_id}: {e}")

videos_handler.filters = filters.private & (filters.video | filters.document)