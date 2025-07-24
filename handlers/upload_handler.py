from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto
from configs import Config
from helpers.uploader import UploadVideo
from helpers.database.access_db import db
from helpers.clean import delete_all
from helpers.ffmpeg import generate_screen_shots, cult_small_video
from helpers.streamtape import UploadToStreamtape
from helpers.display_progress import progress_for_pyrogram, humanbytes
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from PIL import Image
import os
import random
import time
import asyncio

QueueDB = {}
FormtDB = {}
RenameDB = {}

async def proceed_with_upload(bot: Client, update: Message | CallbackQuery, merged_vid_path: str, user_id: int):
    cb = update if isinstance(update, CallbackQuery) else None
    message = update.message if isinstance(update, CallbackQuery) else update
    try:
        await message.edit("Extracting Video Data ...")
    except:
        await message.reply_text("Extracting Video Data ...")
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
        print(f"Error extracting metadata for user {user_id}: {e}")
        await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
        QueueDB.update({user_id: []})
        FormtDB.update({user_id: None})
        try:
            await message.edit("The merged video is corrupted!\nTry again later.")
        except:
            await message.reply_text("The merged video is corrupted!\nTry again later.")
        return
    video_thumbnail = None
    db_thumbnail = await db.get_thumbnail(user_id)
    if db_thumbnail is not None:
        video_thumbnail = await bot.download_media(message=db_thumbnail, file_name=f"{Config.DOWN_PATH}/{str(user_id)}/thumbnail/")
        Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
        img = Image.open(video_thumbnail)
        img.resize((width, height))
        img.save(video_thumbnail, "JPEG")
    else:
        video_thumbnail = f"{Config.DOWN_PATH}/{str(user_id)}/{str(time.time())}.jpg"
        ttl = random.randint(0, int(duration) - 1)
        file_generator_command = [
            "ffmpeg",
            "-ss",
            str(ttl),
            "-i",
            merged_vid_path,
            "-vframes",
            "1",
            video_thumbnail
        ]
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if os.path.exists(video_thumbnail):
            Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
            img = Image.open(video_thumbnail)
            img.resize((width, height))
            img.save(video_thumbnail, "JPEG")
        else:
            video_thumbnail = None
    file_size = os.path.getsize(merged_vid_path)
    try:
        sent_message = await UploadVideo(
            bot=bot,
            cb=cb,
            merged_vid_path=merged_vid_path,
            width=width,
            height=height,
            duration=duration,
            video_thumbnail=video_thumbnail,
            file_size=file_size,
            user_id=user_id
        )
        if sent_message:
            print(f"Successfully uploaded video for user {user_id}")
            # Send to LOG_CHANNEL if configured
            if Config.LOG_CHANNEL:
                try:
                    channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                    upload_as_doc = await db.get_upload_as_doc(user_id=user_id)
                    caption = f"Merged video by user {user_id}\n© @savior_128"
                    if upload_as_doc:
                        await bot.send_document(
                            chat_id=channel_id,
                            document=merged_vid_path,
                            thumb=video_thumbnail,
                            caption=caption
                        )
                    else:
                        await bot.send_video(
                            chat_id=channel_id,
                            video=merged_vid_path,
                            duration=duration,
                            width=width,
                            height=height,
                            thumb=video_thumbnail,
                            caption=caption
                        )
                    print(f"Successfully sent merged video to channel {Config.LOG_CHANNEL} for user {user_id}")
                except Exception as e:
                    print(f"Failed to send video to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
                    try:
                        await message.reply_text(f"Failed to send video to log channel: {e}")
                    except:
                        await bot.send_message(user_id, f"Failed to send video to log channel: {e}")
        else:
            print(f"Failed to upload video for user {user_id}")
            try:
                await message.edit("Failed to upload video to user!")
            except:
                await message.reply_text("Failed to upload video to user!")
            return
    except Exception as e:
        print(f"Error uploading video for user {user_id}: {e}")
        try:
            await message.edit("Failed to upload video!")
        except:
            await message.reply_text("Failed to upload video!")
        return
    caption = f"© @savior_128"
    if await db.get_generate_ss(user_id):
        try:
            await message.edit("Generating Screenshots ...")
        except:
            await message.reply_text("Generating Screenshots ...")
        generate_ss_dir = f"{Config.DOWN_PATH}/{str(user_id)}"
        list_images = await generate_screen_shots(merged_vid_path, generate_ss_dir, 9, duration)
        if list_images is None:
            try:
                await message.edit("Failed to generate screenshots!")
            except:
                await message.reply_text("Failed to generate screenshots!")
            await asyncio.sleep(Config.TIME_GAP)
        else:
            try:
                await message.edit("Generated screenshots successfully!\nUploading ...")
            except:
                await message.reply_text("Generated screenshots successfully!\nUploading ...")
            photo_album = []
            if list_images:
                for i, image in enumerate(list_images):
                    if os.path.exists(str(image)):
                        if i == 0:
                            photo_album.append(InputMediaPhoto(media=str(image), caption=caption))
                        else:
                            photo_album.append(InputMediaPhoto(media=str(image)))
                await bot.send_media_group(chat_id=user_id, media=photo_album)
                # Send screenshots to LOG_CHANNEL if configured
                if Config.LOG_CHANNEL:
                    try:
                        channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                        await bot.send_media_group(
                            chat_id=channel_id,
                            media=photo_album,
                            caption=f"Screenshots for merged video by user {user_id}\n© @savior_128"
                        )
                        print(f"Successfully sent screenshots to channel {Config.LOG_CHANNEL} for user {user_id}")
                    except Exception as e:
                        print(f"Failed to send screenshots to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
    if (await db.get_generate_sample_video(user_id)) and (duration >= 15):
        try:
            await message.edit("Generating Sample Video ...")
        except:
            await message.reply_text("Generating Sample Video ...")
        sample_vid_dir = f"{Config.DOWN_PATH}/{user_id}/"
        ttl = int(duration * 10 / 100)
        sample_video = await cult_small_video(
            video_file=merged_vid_path,
            output_directory=sample_vid_dir,
            start_time=ttl,
            end_time=(ttl + 10),
            format_=RenameDB.get(user_id, {}).get("format", "mp4")
        )
        if sample_video is None:
            try:
                await message.edit("Failed to generate sample video!")
            except:
                await message.reply_text("Failed to generate sample video!")
            await asyncio.sleep(Config.TIME_GAP)
        else:
            try:
                await message.edit("Generated sample video successfully!\nUploading ...")
            except:
                await message.reply_text("Generated sample video successfully!\nUploading ...")
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
            except:
                try:
                    await message.edit("Sample video file corrupted!")
                except:
                    await message.reply_text("Sample video file corrupted!")
                await asyncio.sleep(Config.TIME_GAP)
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
                    progress_args=("Uploading Sample Video ...", message, c_time)
                )
                # Send sample video to LOG_CHANNEL if configured
                if Config.LOG_CHANNEL:
                    try:
                        channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                        await bot.send_video(
                            chat_id=channel_id,
                            video=sample_video,
                            thumb=video_thumbnail,
                            width=sam_vid_width,
                            height=sam_vid_height,
                            duration=sam_vid_duration,
                            caption=f"Sample video for merged video by user {user_id}\n© @savior_128"
                        )
                        print(f"Successfully sent sample video to channel {Config.LOG_CHANNEL} for user {user_id}")
                    except Exception as e:
                        print(f"Failed to send sample video to channel {Config.LOG_CHANNEL} for user {user_id}: {e}")
            except Exception as sam_vid_err:
                print(f"Error uploading sample video for user {user_id}: {sam_vid_err}")
                try:
                    await message.edit("Failed to upload sample video!")
                except:
                    await message.reply_text("Failed to upload sample video!")
                await asyncio.sleep(Config.TIME_GAP)
    try:
        await message.delete()
    except:
        pass
    await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
    QueueDB.update({user_id: []})
    FormtDB.update({user_id: None})