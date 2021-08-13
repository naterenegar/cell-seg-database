import database_models
from database_models import * 
from database_models import database_handle, metadata, engine
import sqlalchemy
import asyncio
import datetime

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

    # Get all of the annotation tags
    tags = []
    for a in anns:
        for t in a["tags"]:
            tags.append(t)

    tags = set(tags)
    labeled_sets = {}
    for t in tags:
        labeled_sets[t] = await LabeledPool(name=t, num_images=0).save()

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

            for ann in image["annotations"]:
                ann_id = ann[0]
                x1, y1 = ann[1]
                x2, y2 = ann[2]
                
                ann_alt = {}
                for ann_entry in anns:
                    if ann_entry["ann_id"] == ann_id:
                        ann_alt = ann_entry
                        break

                finished = ann_alt["valid"]
                memberships = [labeled_sets[t] for t in ann_alt["tags"]]

                for m in memberships:
                    num_images = m.num_images
                    await m.update(num_images=num_images+1)

                # ann_id+1 since primary key must be > 0 
                ormar_ann = await ImageAnnotation(id=ann_id+1, 
                                                  path="",
                                                  in_progress=False,
                                                  finished=finished,
                                                  created_by="Nathan Renegar",
                                                  created_on=datetime.datetime.now(),
                                                  updated_by="Nathan Renegar",
                                                  updated_on=datetime.datetime.now(),
                                                  started_at=datetime.datetime.now(),
                                                  finished_at=datetime.datetime.now(),
                                                  source_x1=x1,
                                                  source_x2=x2,
                                                  source_y1=y1,
                                                  source_y2=y2,
                                                  cell_count=0,
                                                  cell_morphology="balled",
                                                  source_image=db_image,
                                                  memberships=memberships).save()

    # TODO: Add capacitance traces
    # TODO: Add pools

db_exp_list = asyncio.run(main())
print(db_exp_list)

# Add the experiments to the database
# Add the images to each experiment
# Add existing annotations to applicable images
