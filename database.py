import annotation

import re
import os
import json
import numpy as np
import cv2
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, Slider, Button, RadioButtons, TextBox
import matplotlib.patches as patches
from matplotlib.backend_bases import MouseEvent

# TODO: Add support for importing annotations

# TODO: Add warning for annotations that cannot be sourced

# NOTE: Assumes images are preprocessed (e.g. aligned, cropped, normalized,
# etc.). If we want, we can add a description for an experiment that
# denotes what steps have been taken. This is fine for now. Alternatively,
# to maintain consistency throughout the database, we could, upon init,
# take all images in a experiment through preprocessing steps

class Database(object):

    def __init__(self, init_filename='.db.json', autosave=True):
        self.db_dict = {'info': {'initialized': False}, 'data': {}, 'annotations': {'num_anns': 0}} # default dictionary
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
                # image loop
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
                    annotations = [] # tuples of (path, (x1, y1, x2, y2)) to find annotation and rectangle within self
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

    # This is a behemoth of a function... maybe consider splitting it up into
    # helpers?
    def cmd_handler_create_anns(self, args):

        # This gets the experiment number 
        valid_exp = False
        while valid_exp == False:
            # grab all image metadata in relevant experiment
            try:
                exp = int(input("Please enter desired experiment number: "))
                exp = 'exp' + ('0' + str(exp) if exp < 10 else str(exp))
                exp_images = self.db_dict['data']['experiments'][exp]['images']['image_array']
                num_exp_images = self.db_dict['data']['experiments'][exp]['images']['num_images']
                duration = self.db_dict['data']['experiments'][exp]['duration'] 
                h, v = exp_images[0]['resolution']
                print(exp, "has", self.db_dict['data']['experiments'][exp]['duration'], 
                        "hours of data, consisting of", num_exp_images, "images.")
                valid_exp = True
            except (KeyError, ValueError) as e:
                print("You entered an invalid experiment number. Valid numbers are:")
                exp_strings = list(self.db_dict['data']['experiments'].keys())
                exp_strings = [int(x.split('exp')[1]) for x in exp_strings]
                print(str(exp_strings))

        # Get start and ending hours
        times = [img['time'] for img in exp_images]

        fig,ax = plt.subplots(ncols=2, nrows=1, sharey=True, sharex=True)
        ax = ax.ravel()
        im0 = cv2.imread(exp_images[0]['path']) 
        im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
        im1 = cv2.imread(exp_images[-1]['path']) 
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
        artist_0 = ax[0].imshow(im0)
        ax[0].set_title('First image at time = ' + str(times[0]) + " hours")
        artist_1 = ax[1].imshow(im1)
        ax[1].set_title('Last image at time = ' + str(times[-1]) + " hours")
    
        axcolor = 'lightgoldenrodyellow'
        start_ax = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor=axcolor)
        end_ax   = plt.axes([0.25, 0.10, 0.65, 0.03], facecolor=axcolor)
        update_ax = plt.axes([0.25, 0.025, 0.1, 0.04])
        next_ax = plt.axes([0.8, 0.025, 0.1, 0.04])

        s_start = Slider(start_ax, 'Start time (hrs)', times[0], times[-1], valinit=times[0], valstep=(times[1] - times[0]))
        s_end   = Slider(end_ax, 'End time (hrs)', times[0], times[-1],valinit=times[-1], valstep=(times[1] - times[0]))
        update = Button(update_ax, 'Update', color=axcolor, hovercolor='0.975')
        next_button = Button(next_ax, 'Next', color=axcolor, hovercolor='0.975')

        def update_start(val):
            ts = s_start.val
            te = s_end.val
            if ts > te:
                s_end.set_val(ts)
                
        def update_end(val):
            ts = s_start.val
            te = s_end.val
            if te < ts:
                s_start.set_val(te)
                
        def get_closest_time_idx(val):
            cl_time, cl_idx = 0, 0
            for idx, time in list(enumerate(times)):
                if (abs(val - time) < abs(cl_time - time)):
                    cl_time = time
                    cl_idx = idx

            return cl_idx, cl_time

        def update_images(event):
            s_idx, st = get_closest_time_idx(s_start.val)
            e_idx, et = get_closest_time_idx(s_end.val)
            s_start.set_val(st)
            s_end.set_val(et)

            im0 = cv2.imread(exp_images[s_idx]['path']) 
            im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
            im1 = cv2.imread(exp_images[e_idx]['path']) 
            im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
            artist_0.set_data(im0)
            ax[0].set_title('First image at time = ' + str(st) + " hours")
            artist_1.set_data(im1) 
            ax[1].set_title('Last image at time = ' + str(et) + " hours")

        def proceed(event):
            update_images(None)
            plt.close()

        s_start.on_changed(update_start)
        s_end.on_changed(update_end)
        update.on_clicked(update_images)
        next_button.on_clicked(proceed)
        plt.show()

        start_ax.remove()
        end_ax.remove()
        update_ax.remove()
        next_ax.remove()

        start_idx, start_hr = get_closest_time_idx(s_start.val)
        end_idx, end_hr = get_closest_time_idx(s_end.val) 

        # Set up figure for ROI settings
        fig,ax = plt.subplots(ncols=2, nrows=1, sharey=True, sharex=True)
        ax = ax.ravel()
        im0 = cv2.imread(exp_images[start_idx]['path']) 
        im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
        im1 = cv2.imread(exp_images[end_idx]['path']) 
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
        artist_0 = ax[0].imshow(im0)
        ax[0].set_title('First image at time = ' + str(start_hr) + " hours")
        artist_1 = ax[1].imshow(im1)
        ax[1].set_title('Last image at time = ' + str(end_hr) + " hours")

        # set up new axes, sliders, and buttons for annotations
        h_grid_ax = plt.axes([0.15, 0.10, 0.20, 0.03], facecolor=axcolor)
        v_grid_ax = plt.axes([0.15, 0.15, 0.20, 0.03], facecolor=axcolor)
        h_res_ax = plt.axes([0.50, 0.10, 0.05, 0.03])
        v_res_ax = plt.axes([0.50, 0.15, 0.05, 0.03])
        h_pad_ax = plt.axes([0.70, 0.10, 0.05, 0.03])
        v_pad_ax = plt.axes([0.70, 0.15, 0.05, 0.03])
        update_ax = plt.axes([0.15, 0.05, 0.05, 0.03]) 
        stride_ax = plt.axes([0.40, 0.8, 0.05, 0.03])

        h_strech = Slider(h_grid_ax, 'H Grid',1,3,valinit=1, valstep=0.05)
        v_strech = Slider(v_grid_ax, 'V Grid',1,3,valinit=1, valstep=0.05)
        h_res = TextBox(h_res_ax, 'H Res', initial='256')
        v_res = TextBox(v_res_ax, 'V Res', initial='256')
        h_pad_box = TextBox(h_pad_ax, 'H Pad', initial='256')
        v_pad_box = TextBox(v_pad_ax, 'V Pad', initial='256')
        update_button = Button(update_ax, 'Update', color=axcolor, hovercolor='0.975')
        stride_box = TextBox(stride_ax, 'Sampling Stride',initial='1')

        # radio buttons to toggle between two modes

        def draw_grid():
            for a in ax:
                for p in a.patches:
                    p.set_visible(True)

            fig.canvas.draw()

        def clear_grid():
            for a in ax:
                for p in a.patches:
                    p.set_visible(False)
            fig.canvas.draw()

        def reset_grid():
            for a in ax:
                a.patches = []

        def get_num_rois():
            num_rois = 0
            for rect in ax[0].patches:
                if rect.get_edgecolor() == (1.0, 0.0, 0.0, 1):
                    num_rois = num_rois + 1
            return num_rois

        def click_roi(event):
            if type(event) == MouseEvent:
                try:
                    click_x, click_y = event.xdata, event.ydata

                    for idx, rect in list(enumerate(ax[0].patches)):
                        xmin, ymin = rect.get_xy()
                        xmax, ymax = xmin + rect.get_width(), ymin + rect.get_height()
                        if ((click_x >= xmin and click_x <= xmax) and
                            (click_y >= ymin and click_y <= ymax)):
                                color = rect.get_edgecolor()                    
                                clicked_color = (1.0, 0.0, 0.0, 1)
                                if color != clicked_color:
                                    rect.set_edgecolor('r')
                                    ax[1].patches[idx].set_edgecolor('r')
                                elif color == clicked_color:
                                    rect.set_edgecolor('g')
                                    ax[1].patches[idx].set_edgecolor('g')
                except TypeError:
                    pass
      
            num_rois = get_num_rois()
            stride = int(stride_box.text)
            num_sample_imgs = num_rois * ((end_idx - start_idx) // stride)
            fig.suptitle('ROIS: ' + str(num_rois) + 
                    '; Source Images: ' + str((end_idx - start_idx) // stride) + 
                    '; Sample Images: ' + str(num_sample_imgs))

            fig.canvas.draw_idle()

        def update_grid_drawing(event):
            reset_grid()

            h_size = int(h_res.text)
            v_size = int(v_res.text)
            h_pad = int(h_pad_box.text)
            v_pad = int(v_pad_box.text)

            max_hs = (h - h_pad - h_size) // int(h_size * h_strech.val)
            max_vs = (v - v_pad - v_size) // int(v_size * v_strech.val)
            h_starts = np.linspace(h_pad, h - h_pad - h_size, max_hs)
            v_starts = np.linspace(v_pad, v - v_pad - v_size, max_vs) 

            maximum_ts = max_hs * max_vs

            starts = []
            for i in range(maximum_ts):
                starts.append((int(h_starts[i % max_hs]), int(v_starts[i // max_hs])))

            # Create the grid based on the settings given to us
            for start in starts:
                for a in ax:
                    rect = patches.Rectangle(start,h_size,v_size,linewidth=1,edgecolor='g',facecolor='none')
                    a.add_patch(rect)
            fig.canvas.draw_idle()
            click_roi(None) # update ROI and image counts
        
        update_grid_drawing(None)
        update_button.on_clicked(update_grid_drawing)
        stride_box.on_submit(click_roi)
        click_roi_id = plt.connect('button_press_event', click_roi)

        plt.show()
        
        stride = int(stride_box.text)
        num_rois = get_num_rois()
        num_sample_images = num_rois * ((end_idx - start_idx) // stride)


        # Construct list of annotations to be appended 
        next_ann_ID = self.db_dict['annotations']['num_anns']
        img_idxs = [(start_idx + i*stride) for i in range((end_idx - start_idx) // stride)] 
        roi_corners = []
        for rect in ax[0].patches:
            color = rect.get_edgecolor()                    
            clicked_color = (1.0, 0.0, 0.0, 1)
            if color == clicked_color:
                roi_corners.append(rect.get_xy())
        
        # TODO: Decide where sample image and annotation goes, then save that
        # path to the JSON dict
        tmp_ann = annotation.ImageAnnotation()
        ann_list = []
        for idx in img_idxs:
            for offset in roi_corners:
                print(offset)
                d = tmp_ann.ann_dict
                d['ann_id'] = next_ann_ID
                d['valid'] = False
                d['X']['ann_size'] = (int(h_res.text), int(v_res.text))
                d['X']['source_offset'] = offset
                d['X']['source_path'] = exp_images[idx]['path'] 
                d['X']['source_name'] = exp_images[idx]['name']
                ann_list.append(tmp_ann.get_dict())  
                next_ann_ID = next_ann_ID + 1


#        print(ann_list)
#        exp_images
#        start_idx
#        stop_idx
#        stride

        # Look for any overlap between this list of annotations and the
        # existing annotations. If there is overlap, print out where it was,
        # and go back to main prompt


        # Get NPZ granularity
        npz_gran = int(input("There will be " + str(num_sample_images) + " images generated. Please enter number of sample images per NPZ: ")) 
        num_npzs = num_sample_images // npz_gran 
        print("Generating " + str(num_npzs) + " NPZs...") 

        # name format: datetime-exp-starthr-endhr-numimgs-firstSampleID.npz
        for i in range(num_npzs):
            now = datetime.now()
            date_time = (now.strftime("%Y_%m_%d-%H_%M_%S")).split('-')[0]
            start_hr = end_hr = "0"
            npz_name = '-'.join([exp, start_hr, end_hr, str(npz_gran), date_time])
            print('\t' + npz_name)



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

        return # json dicts

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
            except KeyboardInterrupt:
                print("\n\nCommand aborted.\n")

