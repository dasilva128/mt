# (c) @savior_128

import os
import asyncio
import logging
from pyrogram import Client, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LinkPreviewOptions
from configs import Config
from helpers.forcesub import ForceSub
from helpers.state import QueueDB, ReplyDB, FormtDB, RenameDB, update_queue_db, update_reply_db, update_formt_db, update_rename_db, get_queue_db, get_reply_db
from helpers.clean import delete_all
from helpers.database.access_db import get_db
from helpers.settings import OpenSettings
from handlers.upload_handler import proceed_with_upload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def callback_handlers(bot: Client, cb: CallbackQuery):
    """Handle all callback queries."""
    if cb.data == "cancelProcess":
        await cancel_process(bot, cb)
    elif cb.data.startswith("showFileName_"):
        await show_file_name(bot, cb)
    elif cb.data == "refreshFsub":
        await refresh_fsub(bot, cb)
    elif cb.data == "showThumbnail":
        await show_thumbnail(bot, cb)
    elif cb.data == "deleteThumbnail":
        await delete_thumbnail(bot, cb)
    elif cb.data == "triggerUploadMode":
        await trigger_upload_mode(bot, cb)
    elif cb.data == "showQueueFiles":
        await show_queue_files(bot, cb)
    elif cb.data.startswith("removeFile_"):
        await remove_file(bot, cb)
    elif cb.data == "triggerGenSS":
        await trigger_gen_ss(bot, cb)
    elif cb.data == "triggerGenSample":
        await trigger_gen_sample(bot, cb)
    elif cb.data == "openSettings":
        await OpenSettings(cb.message, cb.from_user.id)
    elif cb.data.startswith("renameFile_"):
        await rename_file(bot, cb)
    elif cb.data == "closeMeh":
        try:
            await cb.message.delete()
            logger.info(f"Message closed for user {cb.from_user.id}")
        except Exception as e:
            logger.error(f"Error closing message for user {cb.from_user.id}: {e}")

async def cancel_process(bot: Client, cb: CallbackQuery):
    """Cancel the current process and clear queue."""
    user_id = cb.from_user.id
    try:
        await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
        await update_queue_db(user_id, [])
        await update_formt_db(user_id, None)
        await update_rename_db(user_id, {})
        reply_id = await get_reply_db(user_id)
        if reply_id:
            try:
                await bot.delete_messages(chat_id=cb.message.chat.id, message_ids=reply_id)
                await update_reply_db(user_id, None)
            except Exception as e:
                logger.error(f"Error deleting reply message for user {user_id}: {e}")
        await cb.message.edit("Process cancelled!")
        logger.info(f"Process cancelled for user {user_id}")
    except Exception as e:
        logger.error(f"Error cancelling process for user {user_id}: {e}")
        await cb.message.edit(f"Error cancelling process: {e}")

async def show_file_name(bot: Client, cb: CallbackQuery):
    """Show file name for a queued video."""
    try:
        message_id = int(cb.data.split("_")[1])
        message = await bot.get_messages(cb.message.chat.id, message_id)
        media = message.video or message.document
        file_name = media.file_name or "Unknown"
        await cb.answer(f"File name: {file_name}", show_alert=True)
        logger.info(f"Showed file name for message {message_id} to user {cb.from_user.id}")
    except Exception as e:
        logger.error(f"Error showing file name for user {cb.from_user.id}: {e}")
        await cb.answer("Error retrieving file name!", show_alert=True)

async def refresh_fsub(bot: Client, cb: CallbackQuery):
    """Refresh ForceSub check."""
    if not Config.UPDATES_CHANNEL or not Config.UPDATES_CHANNEL.strip():
        await cb.message.delete()
        logger.info(f"No UPDATES_CHANNEL set, skipping refresh for user {cb.from_user.id}")
        return
    try:
        user = await bot.get_chat_member(
            chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL),
            user_id=cb.message.chat.id
        )
        if user.status == "kicked":
            await cb.message.edit(
                text="Sorry, you are banned from using this bot.",
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info(f"User {cb.from_user.id} is banned from updates channel")
            return
        await cb.message.delete()
        logger.info(f"User {cb.from_user.id} passed ForceSub check")
    except pyrogram.errors.UserNotParticipant:
        await cb.message.edit(
            text="**Please join my updates channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Join Updates Channel", url=(await bot.create_chat_invite_link(
                        int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL
                    )).invite_link)],
                    [InlineKeyboardButton("Refresh", callback_data="refreshFsub")]
                ]
            ),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        logger.info(f"User {cb.from_user.id} still not in updates channel")
    except Exception as e:
        logger.error(f"Error refreshing ForceSub for user {cb.from_user.id}: {e}")
        await cb.message.edit(f"Error checking channel membership: {e}")

async def show_thumbnail(bot: Client, cb: CallbackQuery):
    """Show user's custom thumbnail."""
    user_id = cb.from_user.id
    try:
        db = await get_db()
        db_thumbnail = await db.get_thumbnail(id=user_id)
        if db_thumbnail is None:
            await cb.message.edit("No custom thumbnail set!")
            logger.info(f"No thumbnail set for user {user_id}")
            return
        await bot.send_photo(
            chat_id=user_id,
            photo=db_thumbnail,
            caption="Your custom thumbnail!\n\nTo remove it, click the button below.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]])
        )
        await cb.message.delete()
        logger.info(f"Thumbnail shown for user {user_id}")
    except Exception as e:
        logger.error(f"Error showing thumbnail for user {user_id}: {e}")
        await cb.message.edit(f"Error showing thumbnail: {e}")

async def delete_thumbnail(bot: Client, cb: CallbackQuery):
    """Delete user's custom thumbnail."""
    user_id = cb.from_user.id
    try:
        db = await get_db()
        await db.set_thumbnail(id=user_id, thumbnail=None)
        await cb.message.edit("Thumbnail deleted successfully!")
        logger.info(f"Thumbnail deleted for user {user_id}")
    except Exception as e:
        logger.error(f"Error deleting thumbnail for user {user_id}: {e}")
        await cb.message.edit(f"Error deleting thumbnail: {e}")

async def trigger_upload_mode(bot: Client, cb: CallbackQuery):
    """Toggle upload as document/video."""
    user_id = cb.from_user.id
    try:
        db = await get_db()
        current = await db.get_upload_as_doc(id=user_id)
        await db.set_upload_as_doc(id=user_id, upload_as_doc=not current)
        await OpenSettings(cb.message, user_id)
        logger.info(f"Upload mode toggled for user {user_id}: {'document' if not current else 'video'}")
    except Exception as e:
        logger.error(f"Error toggling upload mode for user {user_id}: {e}")
        await cb.message.edit(f"Error toggling upload mode: {e}")

async def show_queue_files(bot: Client, cb: CallbackQuery):
    """Show all queued files."""
    user_id = cb.from_user.id
    try:
        queue = await get_queue_db(user_id)
        if not queue:
            await cb.message.edit("No files in queue!")
            logger.info(f"No queued files for user {user_id}")
            return
        markup = []
        for message_id in queue:
            message = await bot.get_messages(cb.message.chat.id, message_id)
            media = message.video or message.document
            file_name = media.file_name or "Unknown"
            markup.append([InlineKeyboardButton(f"{file_name}", callback_data=f"showFileName_{message_id}")])
            markup.append([InlineKeyboardButton(f"Remove {file_name}", callback_data=f"removeFile_{message_id}")])
        markup.append([InlineKeyboardButton("Close", callback_data="closeMeh")])
        await cb.message.edit(
            text="Here are your queued files:",
            reply_markup=InlineKeyboardMarkup(markup)
        )
        logger.info(f"Queued files shown for user {user_id}")
    except Exception as e:
        logger.error(f"Error showing queue files for user {user_id}: {e}")
        await cb.message.edit(f"Error showing queue files: {e}")

async def remove_file(bot: Client, cb: CallbackQuery):
    """Remove a file from the queue."""
    try:
        message_id = int(cb.data.split("_")[1])
        user_id = cb.from_user.id
        queue = await get_queue_db(user_id)
        if message_id in queue:
            queue.remove(message_id)
            await update_queue_db(user_id, queue)
            await show_queue_files(bot, cb)
            logger.info(f"File {message_id} removed from queue for user {user_id}")
        else:
            await cb.message.edit("File not found in queue!")
            logger.info(f"File {message_id} not in queue for user {user_id}")
    except Exception as e:
        logger.error(f"Error removing file for user {cb.from_user.id}: {e}")
        await cb.message.edit(f"Error removing file: {e}")

async def trigger_gen_ss(bot: Client, cb: CallbackQuery):
    """Toggle generate screenshots setting."""
    user_id = cb.from_user.id
    try:
        db = await get_db()
        current = await db.get_generate_ss(id=user_id)
        await db.set_generate_ss(id=user_id, generate_ss=not current)
        await OpenSettings(cb.message, user_id)
        logger.info(f"Generate screenshots toggled for user {user_id}: {not current}")
    except Exception as e:
        logger.error(f"Error toggling generate screenshots for user {user_id}: {e}")
        await cb.message.edit(f"Error toggling generate screenshots: {e}")

async def trigger_gen_sample(bot: Client, cb: CallbackQuery):
    """Toggle generate sample video setting."""
    user_id = cb.from_user.id
    try:
        db = await get_db()
        current = await db.get_generate_sample_video(id=user_id)
        await db.set_generate_sample_video(id=user_id, generate_sample_video=not current)
        await OpenSettings(cb.message, user_id)
        logger.info(f"Generate sample video toggled for user {user_id}: {not current}")
    except Exception as e:
        logger.error(f"Error toggling generate sample video for user {user_id}: {e}")
        await cb.message.edit(f"Error toggling generate sample video: {e}")

async def rename_file(bot: Client, cb: CallbackQuery):
    """Handle file renaming decision."""
    user_id = cb.from_user.id
    try:
        if cb.data == "renameFile_Yes":
            await cb.message.edit(
                text="Please send the new file name (only letters, numbers, spaces, underscores, or hyphens allowed):",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            logger.info(f"User {user_id} chose to rename file")
        else:
            merged_vid_path = RenameDB.get(user_id, {}).get("merged_vid_path")
            if not merged_vid_path:
                await cb.message.edit("No merged video found!")
                await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
                await update_queue_db(user_id, [])
                await update_formt_db(user_id, None)
                await update_rename_db(user_id, {})
                logger.info(f"No merged video found for user {user_id}")
                return
            await proceed_with_upload(bot, cb, merged_vid_path, user_id)
            logger.info(f"User {user_id} skipped renaming, proceeding with upload")
    except Exception as e:
        logger.error(f"Error in rename_file for user {user_id}: {e}")
        await cb.message.edit(f"Error processing rename decision: {e}")

async def cancel_callback(bot: Client, cb: CallbackQuery):
    """Handle cancel callback."""
    try:
        user_id = int(cb.data.split("_")[1])
        if user_id != cb.from_user.id:
            await cb.answer("This command is not for you!", show_alert=True)
            logger.info(f"Unauthorized cancel attempt by user {cb.from_user.id}")
            return
        await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
        await update_queue_db(user_id, [])
        await update_formt_db(user_id, None)
        await cb.message.delete()
        logger.info(f"Process cancelled via callback for user {user_id}")
    except Exception as e:
        logger.error(f"Error in cancel_callback for user {cb.from_user.id}: {e}")
        await cb.message.edit(f"Error cancelling process: {e}")