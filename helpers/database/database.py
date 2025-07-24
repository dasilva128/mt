# (c) @savior128

import datetime
import motor.motor_asyncio


class Database:
    """MongoDB database handler for user data."""

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        """Create a new user document."""
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            upload_as_doc=False,
            thumbnail=None,
            generate_ss=False,
            generate_sample_video=False
        )

    async def add_user(self, id):
        """Add a new user to the database."""
        user = self.new_user(id)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        """Check if a user exists in the database."""
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        """Get the total number of users in the database."""
        return await self.col.count_documents({})

    async def get_all_users(self):
        """Get all users from the database."""
        return self.col.find({})

    async def delete_user(self, user_id):
        """Delete a user from the database."""
        await self.col.delete_many({'id': int(user_id)})

    async def set_upload_as_doc(self, id, upload_as_doc):
        """Set whether to upload as document."""
        await self.col.update_one({'id': id}, {'$set': {'upload_as_doc': upload_as_doc}})

    async def get_upload_as_doc(self, id):
        """Get upload_as_doc setting for a user."""
        user = await self.col.find_one({'id': int(id)})
        return user.get('upload_as_doc', False)

    async def set_thumbnail(self, id, thumbnail):
        """Set thumbnail for a user."""
        await self.col.update_one({'id': id}, {'$set': {'thumbnail': thumbnail}})

    async def get_thumbnail(self, id):
        """Get thumbnail for a user."""
        user = await self.col.find_one({'id': int(id)})
        return user.get('thumbnail', None)

    async def set_generate_ss(self, id, generate_ss):
        """Set generate screenshots setting for a user."""
        await self.col.update_one({'id': id}, {'$set': {'generate_ss': generate_ss}})

    async def get_generate_ss(self, id):
        """Get generate screenshots setting for a user."""
        user = await self.col.find_one({'id': int(id)})
        return user.get('generate_ss', False)

    async def set_generate_sample_video(self, id, generate_sample_video):
        """Set generate sample video setting for a user."""
        await self.col.update_one({'id': id}, {'$set': {'generate_sample_video': generate_sample_video}})

    async def get_generate_sample_video(self, id):
        """Get generate sample video setting for a user."""
        user = await self.col.find_one({'id': int(id)})
        return user.get('generate_sample_video', False)