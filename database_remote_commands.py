from PIL import Image
import numpy as np
from datetime import datetime
from subprocess import Popen, DEVNULL, run
import os

from database_models import * 
import asyncio
import boto3

# TODO: Extract to image utils
def crop_image(im, crop):
    assert len(crop) == 2 and len(crop[0]) == 2 and len(crop[1]) == 2
    assert crop[0][0] < crop[1][0] and crop[0][1] < crop[1][1]

    return im[crop[0][0]:crop[1][0], crop[0][1]:crop[1][1]]

def load_image(infilename):
    img = Image.open(infilename)
    img.load()
    data = np.asarray(img)
    return data

def save_image(im, outfilename, grayscale=False):
    if grayscale is True:
        Image.fromarray(im).convert("L").save(outfilename)
    else:
        Image.fromarray(im).save(outfilename)

def get_yes_no(question):
    result = input(question + " [y/n]: ")
    result = True if result.lower() == 'y' else False
    return result

class Database(object):

    def __init__(self, database_handle, metadata, engine, bucket='laboncmosdata'):

        self.database_handle = database_handle
        self.metadata = metadata
        self.engine = engine
        self.prompt = "ann-database> "
        self.cmd_handlers = {
                             'exit':         self.leave_db,
                             'list-invalid': self.cmd_handler_list_invalid_anns,
                             'list-anns':    self.cmd_handler_list_anns,
                             'do-ann':       self.cmd_handler_do_annotation,
                            }
        # Make sure all of our directories are made
        if not os.path.exists('.tmp.anns/'):
            os.mkdir('.tmp.anns/')

        try:
            self.s3_handle = boto3.client('s3') 
        except:
            print("Could not connect to the S3 bucket. Are your AWS credentials configured correctly?")
            exit()

        self.bucket = 'laboncmosdata'


    def start_db(self):
        asyncio.run(self.connect_to_db(self.database_handle))

    async def connect_to_db(self, handle):
        await handle.connect()
        metadata.create_all(engine)
        await self.start_command_CLI()

    async def leave_db(self, **args):
        print("Goodbye!")

    async def cmd_handler_list_invalid_anns(self, **args):
        invalid_anns = {'finished': False}
        await self.cmd_handler_list_anns(**invalid_anns)

    async def cmd_handler_list_anns(self, **args):
        anns = await ImageAnnotation.objects.all(**args)
        for a in anns:
            ms = await a.memberships.all()
            print(str(a.id) + ":", a.source_image.name + ",", ms[0].name)

        print("Found " + str(len(anns)) + " annotations matching the given criteria.")

    # Args is a list of tags
    async def cmd_handler_do_annotation(self, **args):
        # First, we make sure we got an id
        if "id" not in args.keys():
            print("    Must provide named argument \"id\" with do_annotation")
        
        ann = await ImageAnnotation.objects.get(id=int(args["id"]))
        key = ""
        if ann.s3_key == "":
            key = "db/anns/" + str(args["id"]) + "/y_" + str(args["id"]) + ".png"
            print("    Annotation is blank. Creating new annotation")

            source_image = await SourceImage.objects.get(name=ann.source_image.name)
            size = ann.get_image_size() 
            crop = ann.get_source_offset()

            tmp_filename = '.tmp.anns/src.png'
            print("    Fetching source image...")
            with open(tmp_filename, 'wb') as f:
                self.s3_handle.download_fileobj(self.bucket, source_image.s3_key, f)
            print("    Source image downloaded. Opening annotation tool")
            im = load_image(tmp_filename)
            X = np.expand_dims(crop_image(im, crop), axis=0)
            y = np.expand_dims(np.expand_dims(np.zeros(size), axis=-1), axis=0)
            print(y.shape)
            np.savez('.tmp.npz', X=X, y=y)

        else:
            key = ann.s3_key
            print("    Annotation exists in database. Update? [y/n]: ")

            with open('.tmp.anns/ann.png', 'wb') as f:
                self.s3_handle.download_fileobj(self.bucket, ann.s3_key, f)
    
        caliban_proc = Popen(['python3', 'deepcell-label/desktop/caliban.py', '-rgb', 'RGB', '.tmp.npz'])

        if get_yes_no("Did you complete the annotation?") and os.path.isfile('.tmp_save_version_0.npz'):
            finished_ann = np.load('.tmp_save_version_0.npz')
            save_image(np.squeeze(finished_ann['y']), ".tmp.upload.png", grayscale=True)
            self.s3_handle.upload_file(".tmp.upload.png", self.bucket, key)


    # WARNING: This hands over control from the main program to the object 
    async def start_command_CLI(self):
        cmd = ""

        while cmd != "exit":
            cmd = input(self.prompt) 
            cmd = cmd.split(' ')
            cmd, args = cmd[0], cmd[1:]
            kv = dict([tuple(a.split('=')) for a in args])
            try:
                await self.cmd_handlers[cmd](**kv)
            except KeyError:
                if cmd.lower() != 'help':
                    print("Command not found.")
                print("Here's a list of available commands: ")
                cmds = list(self.cmd_handlers.keys())
                cmds.sort()
                for cmd in cmds: 
                    print("    " + cmd)
            except KeyboardInterrupt:
                print("\n\nCommand aborted.\n")

