# My packges 
import imagetypes
import sequencer

# Native python packages 
import re
import os
import json
import random
import copy
from subprocess import Popen, DEVNULL, run
from shutil import copyfile

# Addon packages 
import numpy as np
from PIL import Image
from datetime import datetime

from database_models import * 
import asyncio
import boto3

# TODO: Remap these commands to interface with a (possibly remote) PostgreSQL
# database via ormar

class Database(object):

    def __init__(self, database_handle, metadata, engine, bucket='laboncmosdata'):

        self.database_handle = database_handle
        self.metadata = metadata
        self.engine = engine

        # Default dictionary
        self.prompt = "ann-database> "

        self.cmd_handlers = {'import-anns':  self.cmd_handler_import_annotation,
                             'exit':         self.leave_db,
                             'create-anns':  self.cmd_handler_create_anns,
                             'create-pool':  self.cmd_handler_create_image_pool,
                             'list-invalid': self.cmd_handler_list_invalid_anns,
                             'list-anns':    self.cmd_handler_list_anns,
                             'do-ann':       self.cmd_handler_do_annotation,
                             'create-ball':  self.create_ann_ball}
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

    def cmd_handler_create_anns(self, args):

        # calls the gui 
        # TODO: Convert gui to something faster (e.g. Qt), and to something
        # that uses the database
        imsqr = sequencer.ImageSequencer(self)
        seq = imsqr.get_sequence()

    def cmd_handler_create_image_pool(self, args):
        more = True
        seq = []
        while more:
            imsqr = sequencer.ImageSequencer(self)
            seq = seq + imsqr.get_sequence()
            more_str = input("There are currently " + str(len(seq)) + " images in the pool. \nWould you like to add more images to the pool? [y/n]:")
            if more_str.lower() != 'y':
                more = False
        
        size = seq[0]['size']
        for s in seq:
            if s['size'] != size:
                raise KeyboardInterrupt("All images in pool must have same size") 

        pool_name = input("Please enter the image pool name: ") 
        npz_name = pool_name + '.npz' 
        json_name = pool_name + '.json'

        pool_path = os.path.join('db/pools', pool_name)
        npz_path = os.path.join(pool_path, npz_name)
        json_path = os.path.join(pool_path, json_name)

        if not os.path.exists(pool_path):
            os.makedirs(pool_path)
        else:
            overwrite_str = input("That pool already exists. Would you like to overwrite? [y/n]:")
            if overwrite_str != 'y':
                raise KeyboardInterrupt("Restarting command...") 

        # TODO: Change hardcoded num channels to dynamic 
        X = np.zeros((len(seq), size[0], size[1], 3))
        for (i, s) in enumerate(seq):
            image = Image.open(s['source_path']) 
            offset = s['source_offset']
            npim = np.asarray(image)
            X[i] = npim[offset[1]:offset[1]+size[1], offset[0]:offset[0]+size[0]]

        self.db_dict['pools'][pool_name] = {
            "path": pool_path,
            "npz_path": npz_path,
            "json_path": json_path
        }

        self.save_image_pool(pool_name, X, seq)

    # Returns data associated with an image pool
    def load_image_pool(self, pool_name):
        retval = None
        if pool_name in self.db_dict['pools'].keys():
            pool_info = self.db_dict['pools'][pool_name]
            f = np.load(pool_info['npz_path'])
            json_data = json.load(open(pool_info['json_path']))
            print(len(json_data['images']))
            retval = (f['X'], json_data)
        else:
            print(pool_name, "does not exist in this database.")

        return retval
    
    # Updates image pool on disk
    def save_image_pool(self, pool_name, X, metadata):
        if pool_name in self.db_dict['pools'].keys():
            pool_info = self.db_dict['pools'][pool_name]
            size = metadata[0]['size']
            np.savez(pool_info['npz_path'], X=X, y=np.zeros((len(metadata), size[0], size[1], 1)))
            pool_json = open(pool_info['json_path'], "w+")
            final_dict = {'pool': pool_name, 'images': metadata}
            json.dump(final_dict, pool_json, indent=4)     
        else:
            print(pool_name, "does not exist in this database.")

    # Takes in list of SubImage dictionaries and adds them as blank annotations
    # Lazily allocated... we don't create the annotation until the user
    # provides it. So, a blank annotation is really just a piece of metadata
    def add_blank_annotations(self, ann_list, tag=None):
        next_id = self.db_dict['annotations']['num_anns']
        anns = []
        for a in ann_list:
            ann = imagetypes.subimage_dict_to_ann(a)
            ann.dict['ann_id'] = next_id
            if tag:
                ann.dict['tags'].append(tag)
            anns.append(ann) 
            
            source_offset = ann.dict['X']['source_offset']
            source_final_offset = (source_offset[0] + ann.dict['X']['size'][0], 
                                   source_offset[1] + ann.dict['X']['size'][1])
            source_img = self.find_source_from_ann(ann)
            source_img['annotations'].append((next_id, source_offset, source_final_offset))
            self.db_dict['annotations']['ann_list'].append(ann.dict)

            next_id = next_id + 1
        

        self.db_dict['annotations']['num_anns'] = next_id

    def find_source_from_ann(self, ann):
        source_name = ann.dict['X']['source_name'].split(".")[0]
        source_exp = source_name[0:5]
        source_offset = ann.dict['X']['source_offset']
   
        source_images = None 
        for (exp, exp_data) in self.db_dict['data']['experiments'].items():
            if source_exp == exp:
                source_images = exp_data['images']['image_array']
                break
        source_img = None
        if source_images:
            for img in source_images:
                if source_name == img['name'].split(".")[0]:
                    source_img = img
        return source_img

    def cmd_handler_list_invalid_anns(self, args):
        ann_list = self.find_anns_by_tags(args)
        invalid_count = 0
        for ann in ann_list:
            if ann['valid'] == False:
                invalid_count = invalid_count + 1
                ann_str = str(ann['ann_id']) + ": "
                ann_str = ann_str + ann['X']['source_name'] + ", " + str(tuple(ann['X']['source_offset']))
                print(ann_str)

        print("Of", len(ann_list), "annotations,", invalid_count, "are invalid")

    async def cmd_handler_list_anns(self, **args):
        anns = await ImageAnnotation.objects.all(**args)
        for a in anns:
            ms = await a.memberships.all()
            print(a.id, a.source_image.name, ms[0].name)
            #print(a.id, a.source_image.name, a.select_related("memberships").get())

    def find_anns_by_tags(self, args, valid=None):
        tags = self.tag_helper(args)
        tag = ""
        if len(tags) > 1:
            print("WARNING: Only using first tag. Multi-tag search unimplemented")
        if len(tags) == 0:
            return self.db_dict['annotations']['ann_list']
        tag = tags[0]
        ann_list = []
        for ann in self.db_dict['annotations']['ann_list']:
            if tag in ann['tags']:
                ann_list.append(ann)

        return ann_list

    def create_ann_ball(self, args):
        directory = args[-1]

        if not os.path.exists(directory):
            os.makedirs(directory)

        tags = self.tag_helper(args)
        print(tags)
        tag = ""
        if len(tags) > 1:
            print("WARNING: Only using first tag. Multi-tag search unimplemented")
        tag = None if len(tags) < 1 else tags[0]
        print(tag)

        for ann in self.db_dict['annotations']['ann_list']:
            tag_match = tag in ann['tags']
            valid = ann['valid']
            if tag_match and valid:
                num = str(ann['ann_id'])
                xname = "X_" + num + ".png"
                yname = "y_" + num + ".png"
                ann_x_dir = os.path.join("db/anns", num, xname) 
                ann_y_dir = os.path.join("db/anns", num, yname) 
                new_x_dir = os.path.join(directory, xname)
                new_y_dir = os.path.join(directory, yname)
                copyfile(ann_x_dir, new_x_dir)
                copyfile(ann_y_dir, new_y_dir)

    def tag_helper(self, args):
        tag_str = ""
        tags = []
        for arg in args:
            if len(arg) > 0:
                tag_str = tag_str + str(arg).strip() + " "
                tags.append(str(arg).strip())
        if len(args) > 0:
            print("Looking for annotations with these tags:", tag_str)

        return tags

    # Args is a list of tags
    async def cmd_handler_do_annotation(self, **args):
        # First, we make sure we got an id
        if "id" not in args.keys():
            print("    Must provide named argument \"id\" with do_annotation")
        
        try:
            ann = await ImageAnnotation.objects.get(id=int(args["id"]))
            print("    Fetching annotation from s3 storage")
            print("    s3_key:", ann.s3_key)

            with open('.tmp.anns/ann', 'wb') as f:
                self.s3_handle.download_fileobj(self.bucket, ann.s3_key, f)
        
            print("    Image fetched successfully")

        except:
            print("    Annotation with id", str(args["id"]), "not found.")
            return

    def cmd_handler_import_annotation(self, args, list_call=False):
        ann_file = args
        if not list_call:
            ann_file = input("Please enter path to NPZ file containing annotations: ")        
            if not os.path.isfile(ann_file):
                print("Invalid file or path. Please try again")
                return

        ann = np.load(ann_file)
        print("Found following files in NPZ: ", str(ann.files))
        x_exists = 'X' in ann.files
        y_exists = 'y' in ann.files
        md_exists = 'md' in ann.files
        if not x_exists:
            choice = input("WARNING: Could not find source images in NPZ under name \'X\'. Is there an alternate name? [y/n]: ")

        if not y_exists:
            choice = input("WARNING: Could not find annotation images in NPZ under name \'y\'. Is there an alternate name? [y/n]: ")

        stray_anns = False
        if not md_exists:
            choice = input("WARNING: Could not find annotation metadata in NPZ under name \'md\'. Is there an alternate name? [y/n]: ")
            if choice != 'y':
                filename = input("Is there an alternate file? (enter for NO, filename for YES): ")
                if filename != '':
                    # open up file
                    pass
                else:
                    stray_anns = True
            else:
                stray_anns = True

        # Stray annotations should get set if we cannot complete the source
        # image to annotation mapping for whatever reason. This could be lack
        # of metadata or lack of source images in the database
        if stray_anns:
            print("WARNING: Proceeding with stray annotations. Unique datasets cannot be gauranteed")

        return

    # Can generate unlabelled and labelled pools. Labelled pools are defined as
    # a pool in which at least 1 pixel has an annotation... This is quite a
    # strict definition, so maybe in the future we can add a ceiling %age on
    # pixels annotated

    # TODO: This algorithm does not correclty find all of the regions that an
    # image can fit into. Imagine it shines a light into the x and y axes. Any
    # beams that make it to the other side are considered valid. Continuous
    # strips of beams that overlap in the x and y direction are considered for
    # image placement.  However, this algorithm fails, for example, if you have
    # a ring of images with an unoccupied region in the center, this algorithm
    # will not find the region in the center, and additionally will only
    # identify the extended corners as valid regions
    def generate_image_pool(self, n, exps=[1, 3, 22], size=(256,256), annotated='false'):
        i = 0
        while i < n:
            # Pick random experiment from list
            exp_num = random.randint(1, len(exps))
            exp_string = "exp" + ("0" if exp_num + 1 < 10 else "") + str(exp_num)

            # Pick random image
            img_dict = self.db_dict['data']['experiments'][exp_string]['images']
            img_idx = random.randint(0, img_dict['num_images'] - 1)
            img_data = img_dict['image_array'][img_idx] # is a dict with image information
            
            # First, determine if a subimage of the desired size is available
            # in this image

            # Algorithm for this:
            xs = []
            ys = []
            for ann in img_data['annotations']:
                x1, y1 = ann['source']
                x2, y2 = x1 + ann['size'][0], y1 + ann['size'][1]
                xs.append((x1, x2))
                ys.append((y1, y2))
            xs.sort()
            ys.sort()

            # Combine overlapping y pairs
            for i in range(len(ys) - 1):
                p1y1, p1y2 = ys[i]
                p2y1, p2y2 = ys[i+1]
                if (p1y2 >= p2y1):
                    combined_pair = (p1y1, p2y2)
                    del(ys[i])
                    ys[i] = combined_pair
        
            # Combine overlapping x pairs
            for i in range(len(xs) - 1):
                p1x1, p1x2 = xs[i]
                p2x1, p2x2 = xs[i+1]
                if (p1x2 >= p2x1):
                    combined_pair = (p1x1, p2x2)
                    del(xs[i])
                    xs[i] = combined_pair

            xmax = img_data['resolution'][0]
            ymax = img_data['resolution'][1]
            xsc = []
            ysc = []

            # Complement ys
            for i in range(len(ys)):
                if (i == 0) and (ys[i][0] > 0):
                    ysc.append((0, ys[i][0] - 1))
                elif(i == len(ys) - 1) and (ys[i][1] < ymax - 1):
                    ysc.append((ys[i][1] + 1, ymax - 1))
                else:
                    ysc.append((ys[i][1] + 1, ys[i+1][0] - 1))

            # Complement xs
            for i in range(len(xs)):
                if (i == 0) and (xs[i][0] > 0):
                    xsc.append((0, xs[i][0] - 1))
                elif(i == len(xs) - 1) and (xs[i][1] < xmax - 1):
                    xsc.append((xs[i][1] + 1, xmax - 1))
                else:
                    xsc.append((xs[i][1] + 1, xs[i+1][0] - 1))

            xsc_cand = []
            ysc_cand = []

            for x in xsc:
                if (x[1] - x[0] + 1 >= size[0]):
                    xsc_cand.append(x)

            for y in ysc:
                if (y[1] - y[0] + 1 >= size[0]):
                    ysc_cand.append(y)
    
            # If we go here, we've know there's a suitable image
            if len(xsc_cand) > 0 and len(ysc_cand) > 0:
                ypair = ysc_cand(random.randint(0, len(ysc_cand)-1))
                xpair = xsc_cand(random.randint(0, len(xsc_cand)-1))
                ann_tl = (xpair[0], ypair[0])
                ann_br = (ann_tl[0] + size[0], ann_tl[1] + size[1])
                i =  i + 1

                # TODO: Get metadata
                # TODO: Append to list

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

