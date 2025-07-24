from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LinkPreviewOptions
from configs import Config
from helpers.database.access_db import db
from helpers.forcesub import ForceSub
from helpers.payment import check_user_access
from helpers.markup_maker import MakeButtons
from helpers.clean import delete_all
from helpers.uploader import UploadVideo
from helpers.settings import OpenSettings
from helpers.streamtape import UploadToStreamtape
from helpers.ffmpeg import MergeVideo, generate_screen_shots
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import os
import random
import asyncio
from helpers.display_progress import progress_for_pyrogram, humanbytes

QueueDB = {}
FormtDB = {}
RenameDB = {}

async def callback_handlers(bot: Client, cb: CallbackQuery):
    access, trial_message = await check_user_access(bot, None, cb)
    if not access:
        return
    if "mergeNow" in cb.data:
        duration = 0
        list_message_ids = QueueDB.get(cb.from_user.id, None)
        if list_message_ids is None or len(list_message_ids) == 0:
            await cb.answer("Queue Empty!", show_alert=True)
            try:
                await cb.message.delete()
            except:
                pass
            return
        list_message_ids.sort()
        input_ = f"{Config.DOWN_PATH}/{cb.from_user.id}/input.txt"
        if len(list_message_ids) < 2:
            await cb.answer("Only one video sent for merging!", show_alert=True)
            try:
                await cb.message.delete()
            except:
                pass
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            return
        if not os.path.exists(f"{Config.DOWN_PATH}/{cb.from_user.id}/"):
            os.makedirs(f"{Config.DOWN_PATH}/{cb.from_user.id}/")
        valid_videos = []
        status_message = await cb.message.reply_text("Starting download process...")
        for i in (await bot.get_messages(chat_id=cb.from_user.id, message_ids=list_message_ids)):
            media = i.video or i.document
            unique_name = f"{media.file_name.rsplit('.', 1)[0]}_{i.id}_{random.randint(1000, 9999)}.{media.file_name.rsplit('.', 1)[-1].lower()}"
            file_dl_path = None
            try:
                c_time = time.time()
                file_dl_path = await bot.download_media(
                    message=i,
                    file_name=f"{Config.DOWN_PATH}/{cb.from_user.id}/{i.id}/{unique_name}",
                    progress=progress_for_pyrogram,
                    progress_args=(f"Downloading `{media.file_name}` ...", status_message, c_time)
                )
                if not os.path.exists(file_dl_path):
                    print(f"Download failed for message {i.id}: File not found")
                    try:
                        await status_message.edit(f"Failed to download `{media.file_name}`. Skipped!")
                    except:
                        await cb.message.reply_text(f"Failed to download `{media.file_name}`. Skipped!")
                    await asyncio.sleep(1)
                    continue
            except Exception as downloadErr:
                print(f"Failed to Download File {media.file_name}! Error: {downloadErr}")
                try:
                    await status_message.edit(f"Failed to download `{media.file_name}`. Skipped!")
                except:
                    await cb.message.reply_text(f"Failed to download `{media.file_name}`. Skipped!")
                await asyncio.sleep(1)
                continue
            try:
                metadata = extractMetadata(createParser(file_dl_path))
                if metadata is None or not metadata.has("duration"):
                    print(f"Invalid metadata for file {file_dl_path}")
                    try:
                        await status_message.edit(f"Corrupted file `{media.file_name}`. Skipped!")
                    except:
                        await cb.message.reply_text(f"Corrupted file `{media.file_name}`. Skipped!")
                    await asyncio.sleep(1)
                    continue
                duration += metadata.get('duration').seconds
                valid_videos.append(f"file '{file_dl_path}'")
            except Exception as e:
                print(f"Metadata error for file {file_dl_path}: {e}")
                try:
                    await status_message.edit(f"Corrupted file `{media.file_name}`. Skipped!")
                except:
                    await cb.message.reply_text(f"Corrupted file `{media.file_name}`. Skipped!")
                await asyncio.sleep(1)
                continue
        if len(valid_videos) < 2:
            try:
                await status_message.edit("Only one valid video in queue! Please send at least two valid videos.")
            except:
                await cb.message.reply_text("Only one valid video in queue! Please send at least two valid videos.")
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            return
        try:
            await status_message.edit("Trying to Merge Videos ...")
        except:
            await cb.message.reply_text("Trying to Merge Videos ...")
        with open(input_, 'w') as _list:
            _list.write("\n".join(valid_videos))
        output_format = valid_videos[0].rsplit('.', 1)[-1].strip("'").lower()
        merged_vid_path = await MergeVideo(
            input_file=input_,
            user_id=cb.from_user.id,
            message=status_message,
            format_=output_format
        )
        if merged_vid_path is None:
            try:
                await status_message.edit(text="Failed to Merge Video!")
            except:
                await cb.message.reply_text("Failed to Merge Video!")
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            return
        try:
            await status_message.edit("Successfully Merged Video!")
        except:
            await cb.message.reply_text("Successfully Merged Video!")
        await asyncio.sleep(Config.TIME_GAP)
        file_size = os.path.getsize(merged_vid_path)
        if int(file_size) > 2097152000:
            try:
                await status_message.edit(f"Sorry,\nFile Size is {humanbytes(file_size)}!\nI can't upload to Telegram!\nUploading to Streamtape ...")
            except:
                await cb.message.reply_text(f"Sorry,\nFile Size is {humanbytes(file_size)}!\nI can't upload to Telegram!\nUploading to Streamtape ...")
            streamtape_url = await UploadToStreamtape(file=merged_vid_path, editable=status_message, file_size=file_size)
            if streamtape_url and Config.LOG_CHANNEL:
                try:
                    channel_id = int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL
                    await bot.send_message(
                        chat_id=channel_id,
                        text=f"Merged video by user {cb.from_user.id} (too large for Telegram)\nStreamtape URL: {streamtape_url}\n© @savior_128"
                    )
                    print(f"Successfully sent Streamtape URL to channel {Config.LOG_CHANNEL} for user {cb.from_user.id}")
                except Exception as e:
                    print(f"Failed to send Streamtape URL to channel {Config.LOG_CHANNEL} for user {cb.from_user.id}: {e}")
                    try:
                        await status_message.reply_text(f"Failed to send Streamtape URL to log channel: {e}")
                    except:
                        await bot.send_message(cb.from_user.id, f"Failed to send Streamtape URL to log channel: {e}")
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            return
        try:
            await status_message.edit(
                text="Do you want to rename the file?\nChoose a button from below:",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Rename File", callback_data="renameFile_Yes")],
                        [InlineKeyboardButton("Keep Default", callback_data="renameFile_No")]
                    ]
                )
            )
        except:
            await cb.message.reply_text(
                text="Do you want to rename the file?\nChoose a button from below:",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Rename File", callback_data="renameFile_Yes")],
                        [InlineKeyboardButton("Keep Default", callback_data="renameFile_No")]
                    ]
                )
            )
        RenameDB[cb.from_user.id] = {"merged_vid_path": merged_vid_path, "format": output_format}
    elif "cancelProcess" in cb.data:
        try:
            await cb.message.edit("Trying to Delete Working DIR ...")
        except:
            await cb.message.reply_text("Trying to Delete Working DIR ...")
        await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
        QueueDB.update({cb.from_user.id: []})
        FormtDB.update({cb.from_user.id: None})
        try:
            await cb.message.edit("Successfully Cancelled!")
        except:
            await cb.message.reply_text("Successfully Cancelled!")
    elif cb.data.startswith("showFileName_"):
        message_ = await bot.get_messages(chat_id=cb.message.chat.id, message_ids=int(cb.data.split("_", 1)[-1]))
        try:
            await bot.send_message(
                chat_id=cb.message.chat.id,
                text="This File!",
                reply_to_message_id=message_.id,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Remove File", callback_data=f"removeFile_{str(message_.id)}")]
                    ]
                )
            )
        except Exception as e:
            if "FloodWait" in str(e):
                await cb.answer("Don't Spam!", show_alert=True)
                await asyncio.sleep(int(str(e).split("for ")[1].split(" seconds")[0]))
            else:
                media = message_.video or message_.document
                await cb.answer(f"Filename: {media.file_name}")
    elif "refreshFsub" in cb.data:
        if Config.LOG_CHANNEL:
            try:
                user = await bot.get_chat_member(chat_id=(int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL), user_id=cb.message.chat.id)
                if user.status == "kicked":
                    try:
                        await cb.message.edit(
                            text="Sorry, you are banned from using this bot."
                        )
                    except:
                        await cb.message.reply_text("Sorry, you are banned from using this bot.")
                    return
            except UserNotParticipant:
                try:
                    invite_link = await bot.create_chat_invite_link(chat_id=(int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL))
                except Exception as e:
                    if "FloodWait" in str(e):
                        await asyncio.sleep(int(str(e).split("for ")[1].split(" seconds")[0]))
                        invite_link = await bot.create_chat_invite_link(chat_id=(int(Config.LOG_CHANNEL) if Config.LOG_CHANNEL.startswith("-100") else Config.LOG_CHANNEL))
                    else:
                        raise e
                try:
                    await cb.message.edit(
                        text="**Please join my log channel to use this bot!**",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [InlineKeyboardButton("Join Log Channel", url=invite_link.invite_link)],
                                [InlineKeyboardButton("Refresh", callback_data="refreshFsub")]
                            ]
                        )
                    )
                except:
                    await cb.message.reply_text(
                        text="**Please join my log channel to use this bot!**",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [InlineKeyboardButton("Join Log Channel", url=invite_link.invite_link)],
                                [InlineKeyboardButton("Refresh", callback_data="refreshFsub")]
                            ]
                        )
                    )
                return
            except Exception as e:
                print(f"Error in refreshFsub: {e}")
                try:
                    await cb.message.edit(
                        text="Something went wrong.",
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                except:
                    await cb.message.reply_text(
                        text="Something went wrong.",
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    )
                return
        try:
            await cb.message.edit(
                text=Config.START_TEXT,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Developer - @savior_128", url="https://t.me/savior_128")],
                        [InlineKeyboardButton("Open Settings", callback_data="openSettings")]
                    ]
                ),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except:
            await cb.message.reply_text(
                text=Config.START_TEXT,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Developer - @savior_128", url="https://t.me/savior_128")],
                        [InlineKeyboardButton("Open Settings", callback_data="openSettings")]
                    ]
                ),
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
    elif "showThumbnail" in cb.data:
        db_thumbnail = await db.get_thumbnail(cb.from_user.id)
        if db_thumbnail is not None:
            await cb.answer("Sending Thumbnail ...", show_alert=True)
            await bot.send_photo(
                chat_id=cb.message.chat.id,
                photo=db_thumbnail,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]
                    ]
                )
            )
        else:
            await cb.answer("No Thumbnail Found in Database!")
    elif "deleteThumbnail" in cb.data:
        await db.set_thumbnail(cb.from_user.id, thumbnail=None)
        try:
            await cb.message.edit("Thumbnail Deleted from Database!")
        except:
            await cb.message.reply_text("Thumbnail Deleted from Database!")
    elif "triggerUploadMode" in cb.data:
        upload_as_doc = await db.get_upload_as_doc(cb.from_user.id)
        await db.set_upload_as_doc(cb.from_user.id, not upload_as_doc)
        try:
            await OpenSettings(m=cb.message, user_id=cb.from_user.id)
        except:
            await cb.message.reply_text("Opening settings failed. Please try again.")
    elif "showQueueFiles" in cb.data:
        try:
            markup = await MakeButtons(bot, cb.message, QueueDB)
            await cb.message.edit(
                text="Here are the saved files in your queue:",
                reply_markup=InlineKeyboardMarkup(markup)
            )
        except ValueError:
            await cb.answer("Your Queue is Empty!", show_alert=True)
        except:
            await cb.message.reply_text("Here are the saved files in your queue:", reply_markup=InlineKeyboardMarkup(markup))
    elif cb.data.startswith("removeFile_"):
        if (QueueDB.get(cb.from_user.id, None) is not None) and (QueueDB.get(cb.from_user.id) != []):
            QueueDB.get(cb.from_user.id).remove(int(cb.data.split("_", 1)[-1]))
            try:
                await cb.message.edit(
                    text="File removed from queue!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("Go Back", callback_data="openSettings")]
                        ]
                    )
                )
            except:
                await cb.message.reply_text(
                    text="File removed from queue!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("Go Back", callback_data="openSettings")]
                        ]
                    )
                )
        else:
            await cb.answer("Your Queue is Empty!", show_alert=True)
    elif "triggerGenSS" in cb.data:
        generate_ss = await db.get_generate_ss(cb.from_user.id)
        await db.set_generate_ss(cb.from_user.id, not generate_ss)
        try:
            await OpenSettings(cb.message, user_id=cb.from_user.id)
        except:
            await cb.message.reply_text("Opening settings failed. Please try again.")
    elif "triggerGenSample" in cb.data:
        generate_sample_video = await db.get_generate_sample_video(cb.from_user.id)
        await db.set_generate_sample_video(cb.from_user.id, not generate_sample_video)
        try:
            await OpenSettings(cb.message, user_id=cb.from_user.id)
        except:
            await cb.message.reply_text("Opening settings failed. Please try again.")
    elif "openSettings" in cb.data:
        try:
            await OpenSettings(cb.message, cb.from_user.id)
        except:
            await cb.message.reply_text("Opening settings failed. Please try again.")
    elif cb.data.startswith("renameFile_"):
        if (QueueDB.get(cb.from_user.id, None) is None) or (QueueDB.get(cb.from_user.id) == []):
            await cb.answer("Queue Empty!", show_alert=True)
            return
        merged_vid_path = RenameDB.get(cb.from_user.id, {}).get("merged_vid_path")
        output_format = RenameDB.get(cb.from_user.id, {}).get("format")
        if not merged_vid_path or not output_format:
            try:
                await cb.message.edit("Error: No valid merged video found. Please try again.")
            except:
                await cb.message.reply_text("Error: No valid merged video found. Please try again.")
            return
        if cb.data.split("_", 1)[-1] == "Yes":
            try:
                await cb.message.edit("Please send the new file name!")
            except:
                await cb.message.reply_text("Please send the new file name!")
        else:
            from handlers.upload_handler import proceed_with_upload
            await proceed_with_upload(bot, cb, merged_vid_path, cb.from_user.id)
    elif "closeMeh" in cb.data:
        try:
            await cb.message.delete()
            if cb.message.reply_to_message:
                await cb.message.reply_to_message.delete()
        except:
            pass