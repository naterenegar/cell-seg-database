import database_models
from database_models import Experiment, SourceImage, ImageAnnotation, DataType
from database_models import database_handle, metadata, engine
import sqlalchemy
import asyncio

# Connect to the database and make sure that all of our tables are created

# Open up our old database, get the dictionary
import database

async def main():
    await database_handle.connect()
    metadata.create_all(engine)
    db = database.Database()
    db_dict = db.get_dict()

    image_dt = await DataType(typename="SourceImage").save()
    cap_dt = await DataType(typename="CapacitanceTrace").save()
    exp_dt_list = [image_dt, cap_dt]

    anns = db_dict["annotations"]["ann_list"]

    exps = db_dict["data"]["experiments"]
    exp_list = [e for e in exps if exps[e]["images"]["num_images"] > 100]
    db_exp_list = []

    for exp in exp_list:
        db_exp = await Experiment.objects.create(name=exp, 
                                                 chip="rev-1",
                                                 cell_line="tmp",
                                                 duration=exps[exp]["duration"],
                                                 datatypes=exp_dt_list)
        db_exp_list.append(db_exp)
        for image in exps[exp]["images"]["image_array"]:
            db_image = await SourceImage.objects.create(name=image["name"],
                                                        path=image["path"],
                                                        time=image["time"],
                                                        num_channels=3,
                                                        image_resx=image["resolution"][0],
                                                        image_resy=image["resolution"][1],
                                                        experiment=db_exp)
#            for ann in image 
db_exp_list = asyncio.run(main())
print(db_exp_list)

# Add the experiments to the database
# Add the images to each experiment
# Add existing annotations to applicable images
