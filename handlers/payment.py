import time
import asyncio
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.types import LinkPreviewOptions
from helpers.database.access_db import db
from configs import Config

WALLET_ADDRESS = "UQDHrICGKiVH4pUaxrXKSkfH5_A-pbYibVqRiGHnYgTvLdyw"
PAYMENT_AMOUNT = 1
TRIAL_DURATION = 1800  # 30 minutes in seconds
SUBSCRIPTION_DURATION = 2592000  # 30 days in seconds

async def check_user_access(client: Client, message: Message | None, callback_query: 'CallbackQuery' = None):
    """Check if user has access based on trial or subscription."""
    user_id = callback_query.from_user.id if callback_query else message.from_user.id
    if user_id == Config.BOT_OWNER:
        return True, None
    user_data = await db.get_user_data(user_id)
    current_time = time.time()
    
    # If user doesn't exist, add them and set trial start time
    if not user_data:
        await db.add_user(user_id)
        await db.set_trial_start_time(user_id, current_time)
        user_data = await db.get_user_data(user_id)
    
    trial_start_time = user_data.get("trial_start_time", current_time)
    subscription_end_time = user_data.get("subscription_end_time", 0)
    
    # Check if user is within subscription period
    if subscription_end_time > current_time:
        return True, None
    
    # Check if user is within trial period
    if current_time - trial_start_time <= TRIAL_DURATION:
        remaining_trial = int(TRIAL_DURATION - (current_time - trial_start_time))
        return True, f"Trial mode: {remaining_trial // 60} minutes remaining"
    
    # If trial has expired, show payment message
    reply_target = callback_query.message if callback_query else message
    await reply_target.reply_text(
        text=(
            f"Your 30-minute trial has expired!\n\n"
            f"To continue using the bot, please send **{PAYMENT_AMOUNT} TON** to this wallet:\n"
            f"`{WALLET_ADDRESS}`\n\n"
            f"After payment, contact the bot owner (@savior_128) with your transaction ID."
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url="https://t.me/savior_128")]]
        ),
        quote=True,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )
    return False, None