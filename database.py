# My packges 
import imagetypes
import sequencer

# Native python packages 
import re
import os
import json
import random
import copy
from subprocess import Popen

# Addon packages 
import numpy as np
from PIL import Image
import cv2
from datetime import datetime

# TODO: Add support for importing annotations
# TODO: Add warning for annotations that cannot be sourced

# NOTE: Assumes images are preprocessed (e.g. aligned, cropped, normalized,
# etc.). If we want, we can add a description for an experiment that
# denotes what steps have been taken. This is fine for now. Alternatively,
# to maintain consistency throughout the database, we could, upon init,
# take all images in a experiment through preprocessing steps

class Database(object):

    def __init__(self, init_filename='.db.json', autosave=True):
        
        # Default dictionary
        self.db_dict = {
                'info': {'initialized': False}, 
                'data': {}, 
                'annotations': {'num_anns': 0,
                                'ann_list': []
                               },
                'pools': {}}

        perm_string = "w+"
        if os.path.exists(init_filename):
            perm_string = "r+"
        self.dbf_init = open(init_filename, perm_string)
        self.dbf_working = open(init_filename + '.tmp', "w+")
        self.filename = init_filename
        self.autosave = autosave 
        self.dirty = True
        self.prompt = "ann-database> "

        self.cmd_handlers = {'import-anns': self.cmd_handler_import_annotation,
                             'exit': self.save,
                             'create-anns': self.cmd_handler_create_anns,
                             'create-pool': self.cmd_handler_create_image_pool,
                             'list-invalid': self.cmd_handler_list_invalid_anns,
                             'do-annotation': self.cmd_handler_do_annotation}

        try:
            self.db_dict = json.load(self.dbf_init)
        except json.decoder.JSONDecodeError: 
            print("Database info file", init_filename, "either does not exist or is empty...\n"\
                    "Starting new database")

    # this "destructor" writes back any changes to the local JSON file upon 
    def __del__(self):
        if self.autosave == True and self.dirty == True:
            self.save()

    def get_dict(self):
        return copy.deepcopy(self.db_dict)

    def save(self, dummy=None):
        self.dbf_init.close()
        json.dump(self.db_dict, self.dbf_working, indent=4)     
        self.dbf_working.close()
        os.system('mv ' + self.filename + '.tmp' + ' ' + self.filename)
        self.dirty = False

    def __str__(self):
        retstr = "" 
        for (exp, data) in self.exps:
            retstr = retstr + str(exp) + "\n"

        return retstr

    def is_initialized(self):
        return self.db_dict['info']['initialized']

    def init_database(self, top_dir='db', exp_dir='exps', ann_dir='anns', exp_prefix='exp'):
        if not (os.path.exists(top_dir) and os.path.exists(os.path.join(top_dir, exp_dir))):
            print("ERROR: Provided invalid paths:", top_dir, ",", os.path.join(top_dir, exp_dir))
            print("WARNING: Database not initialized.")
            return

        if self.db_dict['info']['initialized'] == True:
            print("Warning: Overwriting initialized database")

        # TODO: If these already exist in database file, check to see if we can
        # find these structures. If not, ask user to update directory structure
        self.db_dict['info']['top_dir'] = top_dir 
        self.db_dict['info']['exp_dir'] = os.path.join(top_dir, exp_dir)
        self.db_dict['info']['ann_dir'] = os.path.join(top_dir, ann_dir)
        self.db_dict['info']['exp_prefix'] = exp_prefix 

        exps = list(filter(lambda x: x[0:len(exp_prefix)] == exp_prefix,
            os.listdir(os.path.join(top_dir, exp_dir))))
        exps.sort()
        print("Found " + str(len(exps)) + " experiments:", exps)

        exps = {x: {"full_path": os.path.join(top_dir, exp_dir, x)} for x in exps}

        for exp in exps:
            exps[exp]['datatypes'] = os.listdir(exps[exp]['full_path'])
            exps[exp]['duration'] = 0
            for datatype in exps[exp]['datatypes']:
                exps[exp][datatype] = {}

        total_images = 0
        annotated_images = 0

        # Looks through experiment directories for raw images. Takes note of
        # any annotation pointers
        for exp, data in exps.items():
            if 'images' in data['datatypes']:
                image_dir = os.path.join(data['full_path'], 'images')
                image_list = os.listdir(image_dir) 
                num_images = len(image_list)
                total_images = total_images + num_images
                exps[exp]['images']['num_images'] = num_images

                # NOTE: This assumes all images in an experiment are the same
                # resolution. If this is not true, move these lines inside the
                # image loop. This will significantly slow down the init process
                res = cv2.imread(os.path.join(image_dir, image_list[0]))
                h, w, _ = res.shape

                max_time = 0
                img_array = []
                for img in image_list:
                    name = img
                    full_img_path = os.path.join(image_dir, name)
                    source_exp = exp 
                    cell_type = None # TODO: Get the cell type from the .mat file
                    time = name.split(exp + '_t')[1].split('.')[0]
                    nums = re.search('([0-9]+)_([0-9]+).*', time) 
                    time = float(nums.group(1)) + (float(nums.group(2)) / 1000)
                    max_time = time if time > max_time else max_time
                    annotations = [] # tuples of (path, (x1, y1, x2, y2)) to find annotation file and offset
                    image_dict = {'name': name, 'resolution': [w, h], 'source_exp': exp, 'path': full_img_path,
                            'cell_type': cell_type, 'time': time, 'annotations': annotations }
                    img_array.append(image_dict)
                img_array.sort(key=lambda x: x['time'])       
              
                exps[exp]['duration'] = max_time
                exps[exp]['images']['image_array'] = img_array

        ann_dir = os.path.join(top_dir, ann_dir)
        ann_files = os.listdir(ann_dir)
        json_files = []
        for af in ann_files:
            if '.json' in af:
                json_files.append(af)
            elif '.npz' not in af:
                ann_files.remove(af)

        # TODO: Handle return value (i.e. concatenate annotation dictionaries)
        for npz in ann_files:
            self.cmd_handler_import_annotation(os.path.join(ann_dir, npz), list_call=True)


        if annotated_images != 0 and not json_files_found:
            print("WARNING: Experiments claim images are annotated but we did \
                    not find any annotation metadata")

        print("Found a total of", total_images, "images across all experiments, {:.2f}% of which are annotated.".format(annotated_images/total_images))
        self.db_dict['info']['initialized'] = True
        self.db_dict['data']['experiments'] = exps

    def cmd_handler_create_anns(self, args):
        imsqr = sequencer.ImageSequencer(self)
        seq = imsqr.get_sequence()

        # Look for any overlap between this list of annotations and the
        # existing annotations. If there is overlap, print out where it was,
        # and go back to main prompt

        # Get NPZ granularity
        num_sample_images = len(seq)
        npz_gran = int(input("There will be " + str(num_sample_images) + " images generated. Please enter number of sample images per NPZ: ")) 
        num_npzs = num_sample_images // npz_gran 
        print("Generating " + str(num_npzs) + " NPZs...") 

        # name format: datetime-numimgs-firstSampleID.npz
        for i in range(num_npzs):
            now = datetime.now()
            date_time = (now.strftime("%Y_%m_%d-%H_%M_%S")).split('-')[0]
            npz_name = '-'.join([str(npz_gran), date_time])
            print('\t' + npz_name)

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
        invalid_count = 0
        for ann in self.db_dict['annotations']['ann_list']:
            if ann['valid'] == False:
                invalid_count = invalid_count + 1
                print(ann)

        print("Of", len(self.db_dict['annotations']['ann_list']), "annotations,", invalid_count, "are invalid")

    # Args is a list of tags
    def cmd_handler_do_annotation(self, args):
   
        tag_str = ""
        tags = []
        for arg in args:
            if len(arg) > 0:
                tag_str = tag_str + str(arg).strip() + " "
                tags.append(str(arg).strip())
        if len(args) > 0:
            print("Looking for annotations with these tags:", tag_str)
    
        tag = ""
        if len(tags) > 1:
            print("WARNING: Only using first tag. Multi-tag search unimplemented")
            tag = tags[0]

        # First, look for unfinished annotations
        invalid_anns = []
        for ann in self.db_dict['annotations']['ann_list']:
            if ann['valid'] == False:
                invalid_anns.append(ann)
    
        if tag != "":
            for ann in invalid_anns:
                if tag not in ann['tags']:
                    invalid_anns.remove(ann) 

        print("Found", len(invalid_anns), "unfinished annotations matching given criteria...")
        
        if len(invalid_anns) > 0:
            print("Doing first annotation on the list.")
            ann_todo = invalid_anns[0]      
            
            source_img = self.find_source_from_ann(ann_todo)
            if source_img is None:
                print("ERROR: Could not find source image for annotation")
                return 

            pil_img = Image.open(source_img['source_path']) 
            np_img = np.asarray(pil_img)
            np_img = np.expand_dims(np_img, axis=0)
            np.savez(".tmp.npz", X=np_img, y=np.zeros(np_img.shape[-1:] + tuple([1])))

            # Get contextual images of the source image, and take subimages
            # with padding around the annotation region. Save each of these
            # onto disk and open them up as an image sequence in imagej

            # Open up contextual images in ImageJ, detached (program can proceed) 
            Popen(["ImageJ-linux64"])

            # Open up the annotation tool, attached (i.e. program halts here until
            # annotation tool exits)
            
            # Ask user if they successfully completed the annotation

            # If no, done

            # If yes, load NPZ, get X and y, then save them to the annotation database
            # Mark this annotation as valid

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
    def start_command_CLI(self):
        cmd = ""

        while cmd != "exit":
            cmd = input(self.prompt) 
            cmd = cmd.split(' ')
            cmd, args = cmd[0], cmd[1:]
            try:
                self.cmd_handlers[cmd](args)
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

