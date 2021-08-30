import database_models
from database_models import * 
from database_models import database_handle, metadata, engine
import sqlalchemy
import asyncio
import datetime
import database_remote_commands
import asyncpg


db = database_remote_commands.Database(database_handle, metadata, engine)
try:
    db.start_db()
except asyncpg.exceptions.InvalidPasswordError:
    print("Incorrect password.")

