import re
import os
import json
import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# Nice to haves to get to if you have time:
#   - Pack/Unpack NPZs 

# TODO: Add support for importing annotations

# TODO: Add warning for annotations that cannot be sourced

# NOTE: Assumes images are preprocessed (e.g. aligned, cropped, normalized,
# etc.). If we want, we can add a description for an experiment that
# denotes what steps have been taken. This is fine for now. Alternatively,
# to maintain consistency throughout the database, we could, upon init,
# take all images in a experiment through preprocessing steps

# TODO: I want to be able to open up all of the raw images corresponding
# to images in an NPZ in a matplotlib window. This is useful because you
# can go back and forth, look at other contexts, etc

class Database(object):

    def __init__(self, init_filename='.db.json', autosave=True):
        self.db_dict = {'info': {'initialized': False}, 'data': {}} # default dictionary
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
                             'create-anns': self.cmd_handler_create_anns}

        try:
            self.db_dict = json.load(self.dbf_init)
        except json.decoder.JSONDecodeError: 
            print("Database info file", init_filename, "either does not exist or is empty...\n"\
                    "Starting new database")

    # this "destructor" writes back any changes to the local JSON file upon 
    def __del__(self):
        if self.autosave == True and self.dirty == True:
            self.save()

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

   
    # NOTE: This currently assumes all images in a experiment are the same
    # resolution. We can add an option to check for this if necessary, but I
    # think it is a reasonable assumption for now
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
                # image loop
                res = cv2.imread(os.path.join(image_dir, image_list[0]))
                h, w, _ = res.shape

                img_array = []
                for img in image_list:
                    name = img
                    full_img_path = os.path.join(image_dir, name)
                    source_exp = exp 
                    cell_type = None # TODO: Get the cell type from the .mat file
                    time = name.split(exp + '_t')[1].split('.')[0]
                    nums = re.search('([0-9]+)_([0-9]+).*', time) 
                    time = float(nums.group(1)) + (float(nums.group(2)) / 1000)
                    annotations = [] # tuples of (path, (x1, y1, x2, y2)) to find annotation and rectangle within self
                    image_dict = {'name': name, 'resolution': [w, h], 'source_exp': exp, 'path': full_img_path,
                            'cell_type': cell_type, 'time': time, 'annotations': annotations }
                    img_array.append(image_dict)
                img_array.sort(key=lambda x: x['time'])       
               
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

    # TODO: 
    # Give number of desired images as well as images per time sequence.
    # This function will search through the database and look for images that
    # fit the criteria. you can also choose a granularity for how often to
    # create an NPZ. This function also creates all of the necessary metadata
    # for annotation tracking.

    # Today:
    #   - Given number of annotations, creates time series and separate NPZs
    #   while checking to make sure none of them overlap. We'll confirm with
    #   the user the location of each time series before creating the NPZs 
    #       1. get desired # of annotations, time series, annotation resolution, npz granularity from user
    #           - # of annotations: total number of annotations to create
    #           - # of time series: number of consecutive sequences to create
    #           (e.g. 2 time series w/ 100 annotations creates 2 sets of 50
    #           looking at two different spots on the image)
    #           - annotation resolution (default 256x256): image size of each annotation
    #           - npz granularity: number of annotations to pack into each NPZ file. 

    # TODO: Change this to select annotation by hour range and give number of
    # sample streams (i.e. time sequences)
    def cmd_handler_create_anns(self, args):
        # commmand is "ann-create"
        exp = int(input("Please enter desired experiment number: "))
        npz_gran = int(input("Please enter number of images per NPZ: ")) 

        # grab all image metadata in relevant experiment
        exp = 'exp' + ('0' + str(exp) if exp < 10 else str(exp))
        exp_images = self.db_dict['data']['experiments'][exp]['images']['image_array']
        w, h = exp_images[0]['resolution']

        # This loop lets user configure ROI options
        acceptable = 'n'
        num_images = 1
        while acceptable == 'n':
            num_anns = int(input("Please enter number of annotations: "))
            ann_res = input("Please enter annotation resolution in form \"<width>, <height>\": ")
            ann_w, ann_h = ann_res.split(',')
            ann_w = int(ann_w)
            ann_h = int(ann_h)
            w_strech = float(input("Please enter horizontal spacing factor (min 1): "))
            h_strech = float(input("Please enter vertical spacing factor (min 1): "))
            w_strech = 1 if w_strech < 1 else w_strech
            h_strech = 1 if h_strech < 1 else h_strech

            # generate equally spaced tuples by default
            max_ws = (w - 2 * ann_w) // int(ann_w * w_strech)
            max_hs = (h - 2 * ann_h) // int(ann_h * h_strech)
            w_starts = np.linspace(ann_w, w - 2*ann_w, max_ws)
            h_starts = np.linspace(ann_h, h - 2*ann_h, max_hs) 

            maximum_ts = max_ws * max_hs
            time_series = int(input("Please enter number of time series (maximum = " + str(maximum_ts) + "): "))
            time_stride = int(input("Please enter time series stride (number of images between each step in series): "))
            num_images = (num_anns // time_series) * time_stride

            starts = []
            for i in range(time_series):
                starts.append((int(w_starts[i % max_ws]), int(h_starts[i // max_ws])))

            # Load first and last image in sampling range
            fig,ax = plt.subplots(ncols=2, nrows=1, sharey=True)
            ax = ax.ravel()
            im0 = cv2.imread(exp_images[0]['path']) 
            im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
            im1 = cv2.imread(exp_images[num_images-1]['path']) 
            im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
            ax[0].imshow(im0)
            ax[0].set_title('First image')
            ax[1].imshow(im1)
            ax[1].set_title('Last image')

            # Draw bounding boxes around generated ROIs
            i = 1
            for start in starts:
                for a in ax:
                    rect = patches.Rectangle(start,ann_w,ann_h,linewidth=1,edgecolor='g',facecolor='none')
                    a.add_patch(rect)
                    a.annotate(str(i), xy=(start[0] + int(ann_w / 2), start[1] + int(ann_h / 2)), 
                                color='b', fontsize='x-large', ha='center', va='center') 
                i = i + 1

            # Ask user to confirm settings
            print("With these settings, the annotations will go " + str(num_images) + " images into the experiment.")
            print("Showing generated ROIs for first and last image...")
            plt.show()
            acceptable = input("Are these settings acceptable? [y/n]: ")

        num_npzs = num_anns // num_images
        print("Generating " + str(num_npzs) + " NPZs...") 

        # TODO: Generate a name for each NPZ

        # TODO: Put sample images into each NPZ by time series, so consecutive
        # images are localized in space and not in time

        # TODO: Create metadata on an NPZ basis as well. Should just be a list
        # of NPZs, number of images in each, and a boolean whose value
        # corresponds to the completeness of annotation (true = all annotated,
        # false = not all annotated)

        # TODO: Generate NPZ JSON data for annotations
        #   Includes:
        #      - npz_path: path to NPZ file containig the annotated sample image
        #      - annID: unique integer. perhaps next unique stored at top level
        #      - annotationComplete: boolean indicating whether chosen sample image has been labeled
        #      - annotationType: (hand, machine)
        #      - annotator: if type is 'hand', then this is a name. if 'machine', it's the name of the model used to predict an annotation
        #      - size: resolution
        #      - time: hours
        #      - experiment: integer
        #      - cellType: string
        #      - numberOfCells: of each class if more than one class
        #      - sourceImage
        #      - sourceOffset (integer x, integer y), location of top left pixel of annotation in source

        # TODO: For each NPZ, take a subset of all the generated annotation
        #       metadata and store it in the NPZ. The order of entries should
        #       correspond to the order of images in the NPZ 

        # TODO: Update source metadata
        #      - each image contains an "annotations" field that is a list of
        #        tuples, where the tuple is (<annotation_id>, (x1, y1), (x2,
        #        y2)) and the two (x,y) pairs define a rectangle, so x1 < x2
        #        and y1 < y2

        return

    # How this is going to work:
    #  - One JSON file in the anns directory that contains information about
    #  all annotations in the database. This order in this file does not
    #  correspond to order in an NPZ. Each annotation will be an entry
    #  containing:
    #   - NPZ file
    #      - annotation status 
    #      There will be an array of entries in the NPZ
    #      - annID (integer)
    #      - size (resolution)
    #      - time (hours)
    #      - experiment (integer)
    #      - cellType (string)
    #      - numberOfCells (of each class if more than one class)
    #      - sourceImage
    #      - sourceOffset (integer x, integer y), location of top left pixel of annotation in source
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

    

