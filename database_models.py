from typing import Optional

import databases
import pydantic

import ormar
import sqlalchemy

DATABASE_URL = "postgresql:///laboncmos"
database_handle = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
engine = sqlalchemy.create_engine(DATABASE_URL)

#### DATA GROUPINGS ####

class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database_handle

class DataType(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "datatypes"

    typename: str = ormar.String(primary_key=True, max_lenth=1000)

class Experiment(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "experiments"
   
    name: str = ormar.String(primary_key=True, max_length=200)
    chip: str = ormar.String(max_length=200)
    cell_line: str = ormar.String(max_length=200)
    duration: float = ormar.Float()

    datatypes: Optional[List[DataType]] = ormar.ManyToMany(DataType)

    # TODO: For clarity, explicitly list the reverse foreign keys
    #   source images
    #   capcitance traces
    #   ...
    # We should be able to add more datatypes without breaking anything (?)

class ImagePool(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "pools"

    name: str = ormar.String(primary_key=True, max_length=200)
    num_images: int = ormar.Integer(minimum=0) # positive

class LabeledPool(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "labeled_pools"

    name: str = ormar.String(primary_key=True, max_length=200)
    num_images: int = ormar.Integer(minimum=0) # positive

#### DATA ####

# TODO: May make sense to make a base class that has all of the necessary
# metadata to find the data in the S3 Bucket (i.e. S3 URI, bucket name)

class CapacitanceTrace(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "capacitance_traces"

    experiment: Optional[Experiment] = ormar.ForeignKey(Experiment)
    channel: int = ormar.Integer(minimum=0)
    sample_freq: float = ormar.Float(minimum=0)
    sample_offset: float = ormar.Float(minimum=0) # Offset of first sample


# TODO: Image base class:

# Source Images are the post-processed full size images taken during the
# experiment.
class SourceImage(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "images"

    name: str = ormar.String(primary_key=True, max_length=200)

    path: str = ormar.String(max_length=1000) # TODO: Change to S3 location

    time: float = ormar.Float(minimum=0)
    num_channels: int = ormar.Integer(minimum=0)

    image_resx: int = ormar.Integer(minimum=0)
    image_resy: int = ormar.Integer(minimum=0)

    experiment: Optional[Experiment] = ormar.ForeignKey(Experiment)

# Sample Images
class SampleImage(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "sample_images"

    id: int = ormar.Integer(primary_key=True)
    path: str = ormar.String(max_length=1000)

    num_channels: int = ormar.Integer(minimum=0)

    # Offset in source image. Implicity defines the resolution
    source_x1: int = ormar.Integer()
    source_y1: int = ormar.Integer()
    source_x2: int = ormar.Integer()
    source_y2: int = ormar.Integer()

    source_image: Optional[SourceImage] = ormar.ForeignKey(SourceImage)
    memberships: Optional[List[ImagePool]] = ormar.ManyToMany(ImagePool)

class ImageAnnotation(ormar.Model):
    class Meta(BaseMeta):
        tablename: str = "annotations"

    id: int = ormar.Integer(primary_key=True)
    path: str = ormar.String(max_length=1000)

    # Current annotation status
    in_progress: bool = ormar.Boolean()
    finished: bool = ormar.Boolean()

    # Creation times
    created_by: str = ormar.String(max_length=200)
    created_on: datetime.datetime = ormar.DateTime()

    # Last update times
    updated_by: str = ormar.String(max_lengh=200) 
    updated_on: datetime.datetime = ormar.DateTime()
    
    # Measures annotation time from view of database 
    started_at: datetime.datetime = ormar.DateTime()
    finished_at: datetime.datetime = ormar.DateTime()

    # Offset in source image. Implicity defines the resolution
    source_x1: int = ormar.Integer()
    source_y1: int = ormar.Integer()
    source_x2: int = ormar.Integer()
    source_y2: int = ormar.Integer()

    cell_count: int = ormar.Integer()
    cell_morphology: str = ormar.String(max_length=100) # "balled", "intermediate", "adhered"?

    source_image: Optional[SourceImage] = ormar.ForeignKey(SourceImage)
    memberships: Optional[List[LabeledPool]] = ormar.ManyToMany(LabeledPool)
