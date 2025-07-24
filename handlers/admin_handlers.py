from pyrogram import Client, filters
from pyrogram.types import Message, LinkPreviewOptions
from configs import Config
from helpers.database.access_db import db
from helpers.broadcast import broadcast_handler
from helpers.payment import SUBSCRIPTION_DURATION
import shutil
import psutil
import datetime
from helpers.display_progress import humanbytes

async def broadcast_handler(bot: Client, m: Message):
    await broadcast_handler(m)

broadcast_handler.filters = filters.private & filters.command("broadcast") & filters.reply & filters.user(Config.BOT_OWNER)

async def status_handler(bot: Client, m: Message):
    total, used, free = shutil.disk_usage(".")
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    total_users = await db.total_users_count()
    await m.reply_text(
        text=f"**Total Disk Space:** {total} \n**Used Space:** {used}({disk_usage}%) \n**Free Space:** {free} \n**CPU Usage:** {cpu_usage}% \n**RAM Usage:** {ram_usage}%\n\n**Total Users in DB:** `{total_users}`",
        quote=True
    )

status_handler.filters = filters.private & filters.command("status") & filters.user(Config.BOT_OWNER)

async def check_handler(bot: Client, m: Message):
    if len(m.command) == 2:
        editable = await m.reply_text("Checking User Details ...")
        user = await bot.get_users(user_ids=int(m.command[1]))
        detail_text = f"**Name:** [{user.first_name}](tg://user?id={str(user.id)})\n" \
                      f"**Username:** `{user.username}`\n" \
                      f"**Upload as Doc:** `{await db.get_upload_as_doc(user_id=int(m.command[1]))}`\n" \
                      f"**Generate Screenshots:** `{await db.get_generate_ss(user_id=int(m.command[1]))}`\n" \
                      f"**Trial Start Time:** `{await db.get_trial_start_time(user_id=int(m.command[1]))}`\n" \
                      f"**Subscription End Time:** `{await db.get_subscription_end_time(user_id=int(m.command[1]))}`"
        try:
            await editable.edit(
                text=detail_text,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except:
            await m.reply_text(
                text=detail_text,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                quote=True
            )

check_handler.filters = filters.private & filters.command("check") & filters.user(Config.BOT_OWNER)

async def extend_subscription_handler(bot: Client, m: Message):
    if len(m.command) != 2:
        await m.reply_text("Usage: /extend_subscription <user_id>", quote=True)
        return
    try:
        user_id = int(m.command[1])
        if not await db.is_user_exist(user_id):
            await m.reply_text("User not found in database!", quote=True)
            return
        current_time = time.time()
        new_subscription_end_time = current_time + SUBSCRIPTION_DURATION
        await db.set_subscription_end_time(user_id, new_subscription_end_time)
        await m.reply_text(f"Subscription extended for user {user_id} until {datetime.datetime.fromtimestamp(new_subscription_end_time).strftime('%Y-%m-%d %H:%M:%S')}", quote=True)
        await bot.send_message(
            chat_id=user_id,
            text="Your subscription has been extended for 30 days! You can now use the bot."
        )
    except ValueError:
        await m.reply_text("Invalid user ID!", quote=True)
    except Exception as e:
        await m.reply_text(f"Error: {e}", quote=True)

extend_subscription_handler.filters = filters.private & filters.command("extend_subscription") & filters.user(Config.BOT_OWNER)

async def clear_users_handler(bot: Client, m: Message):
    try:
        await db.clear_users()
        await m.reply_text("All users have been successfully removed from the database!", quote=True)
    except Exception as e:
        await m.reply_text(f"Error clearing users: {e}", quote=True)

clear_users_handler.filters = filters.private & filters.command("clear_users") & filters.user(Config.BOT_OWNER)