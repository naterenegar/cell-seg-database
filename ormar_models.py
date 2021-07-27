from typing import Optional

import databases
import pydantic

import ormar
import sqlalchemy

DATABASE_URL = "postgresql:///laboncmos"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# note that this step is optional -> all ormar cares is a internal
# class with name Meta and proper parameters, but this way you do not
# have to repeat the same parameters if you use only one database
class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database

class Experiment(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "experiments"
   
    name: str = ormar.String(primary_key=True, max_length=100)
    chip: str = ormar.String(max_length=100)
    # duration
    # images
    # ...
   
class Image(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "images"

    # The reverse relation (Experiment -> Image) is automatically generated
    name: str = ormar.String(primary_key=True, max_length=100)
    path: str = ormar.String(max_length=1000)
    experiment: Optional[Experiment] = ormar.ForeignKey(Experiment, name="experiment_id")

class ImageAnnotation(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "annotations"

    id: int = ormar.Integer(primary_key=True)
    path: str = ormar.String(max_length=1000)
    source_image: Optional[Image] = ormar.ForeignKey(Image)

    source_x1: int = ormar.Integer()
    source_y1: int = ormar.Integer()
    source_x2: int = ormar.Integer()
    source_y2: int = ormar.Integer()
