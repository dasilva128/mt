# (c) @savior_128

import asyncio
from configs import Config
from pyrogram import Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message


async def ForceSub(bot: Client, cmd: Message):
    """Force users to join the updates channel."""
    if not Config.UPDATES_CHANNEL:
        return 200
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL)
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        invite_link = await bot.create_chat_invite_link(
            chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL)
        )
    except Exception as err:
        print(f"Unable to create invite link for {Config.UPDATES_CHANNEL}\nError: {err}")
        return 200
    try:
        user = await bot.get_chat_member(
            chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL),
            user_id=cmd.from_user.id
        )
        if user.status == "kicked":
            await bot.send_message(
                chat_id=cmd.from_user.id,
                text="Sorry, you are banned from using this bot.",
                parse_mode="markdown",
                disable_web_page_preview=True
            )
            return 400
    except UserNotParticipant:
        await bot.send_message(
            chat_id=cmd.from_user.id,
            text="**Please join my updates channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Join Updates Channel", url=invite_link.invite_link)],
                    [InlineKeyboardButton("Refresh", callback_data="refreshFsub")]
                ]
            ),
            parse_mode="markdown"
        )
        return 400
    except Exception:
        await bot.send_message(
            chat_id=cmd.from_user.id,
            text="Something went wrong.",
            parse_mode="markdown",
            disable_web_page_preview=True
        )
        return 400
    return 200