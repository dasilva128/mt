# (c) @savior128

from configs import Config
from helpers.database.database import Database

db = Database(Config.MONGODB_URI, Config.SESSION_NAME)