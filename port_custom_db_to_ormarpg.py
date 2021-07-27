import database_models
from database_models import Experiment, Image, ImageAnnotation
from database_models import DATABASE_URL, database_handle, metadata
import sqlalchemy
import asyncio

# Connect to the database and make sure that all of our tables are created
asyncio.run(database_handle.connect())
engine = sqlalchemy.create_engine(database_models.DATABASE_URL)
metadata.create_all(engine)

# Open up our old database 
import database
db = database.Database()
