from pyrogram import Client
from configs import Config
from handlers.start_handler import start_handler
from handlers.video_handler import videos_handler
from handlers.photo_handler import photo_handler
from handlers.settings_handler import settings_handler
from handlers.admin_handlers import broadcast_handler, status_handler, check_handler, extend_subscription_handler, clear_users_handler
from handlers.callback_handlers import callback_handlers
from handlers.text_handler import handle_file_name

NubBot = Client(
    name=Config.SESSION_NAME,
    api_id=int(Config.API_ID),
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Register handlers
NubBot.on_message(filters=start_handler.filters)(start_handler)
NubBot.on_message(filters=videos_handler.filters)(videos_handler)
NubBot.on_message(filters=photo_handler.filters)(photo_handler)
NubBot.on_message(filters=settings_handler.filters)(settings_handler)
NubBot.on_message(filters=broadcast_handler.filters)(broadcast_handler)
NubBot.on_message(filters=status_handler.filters)(status_handler)
NubBot.on_message(filters=check_handler.filters)(check_handler)
NubBot.on_message(filters=extend_subscription_handler.filters)(extend_subscription_handler)
NubBot.on_message(filters=clear_users_handler.filters)(clear_users_handler)
NubBot.on_message(filters=handle_file_name.filters)(handle_file_name)
NubBot.on_callback_query()(callback_handlers)

if __name__ == "__main__":
    NubBot.run()