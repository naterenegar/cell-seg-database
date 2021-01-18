# We also want this to be able to scan an experiment directory containing
# multiple experiments (as directories). In each directory is some data, and
# the user can pass a parsing function in to construct the database.

# Maybe instead of reading all of the data into memory, we can just construct a
# map of where to find the data. This makes sense since the usual use case is a
# small number of files at a time.

# TODO: We also want to store the cell type 

import re
import os
import json

class Database(object):

    # autosave(bool): Determines if file is automatically saved on program exit
    def __init__(self, init_filename='.db.json', autosave=True):
        self.db_dict = {'info': {'initialized': False}, 'data': {}}
        self.dbf_init = open(init_filename, "r+")
        self.dbf_working = open(init_filename + '.tmp', "w+")
        self.filename = init_filename
        self.autosave = autosave 
        self.dirty = True

        try:
            data = json.load(self.dbf_init)
        except json.decoder.JSONDecodeError: 
            print(init_filename, "either does not exist or is empty...\n"\
                    "Starting new database")

    # This calls writes back any changes to the local JSON file 
    def __del__(self):
        if self.autosave == True and self.dirty == True:
            self.save()

    def save(self):
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

    # TODO: Currently does not support importing annotations
    def init_database(self, top_dir, exp_dir, exp_prefix):
        if self.db_dict['info']['initialized'] == True:
            print("Warning: Overwriting initialized database")

        exps = list(filter(lambda x: x[0:len(exp_prefix)] == exp_prefix,
            os.listdir(os.path.join(top_dir, exp_dir))))
        print("Found " + str(len(exps)) + " experiments.")

        exps = {x: {"full_path": os.path.join(top_dir, exp_dir, x)} for x in exps}

        for exp in exps:
            exps[exp]['datatypes'] = os.listdir(exps[exp]['full_path'])
            for datatype in exps[exp]['datatypes']:
                exps[exp][datatype] = {}

        total_images = 0
        annotated_images = 0
        for exp, data in exps.items():
            if 'images' in data['datatypes']:
                image_dir = os.path.join(data['full_path'], 'images')
                image_list = os.listdir(image_dir) 
                num_images = len(image_list)
                total_images = total_images + num_images
                exps[exp]['images']['num_images'] = num_images

                img_array = []
                for img in image_list:
                    name = img
                    full_img_path = os.path.join(image_dir, name)
                    source_exp = exp 
                    cell_type = None # TODO: Get the cell type from the .mat file
                    time = name.split(exp + '_t')[1].split('.')[0]
                    nums = re.search('([0-9]+)_([0-9]+).*', time) 
                    time = float(nums.group(1)) + (float(nums.group(2)) / 1000)
                    annotated = False
                    annotation_path = ""
                    image_dict = {'name': name, 'source_exp': exp, 'path': full_img_path,
                            'cell_type': cell_type, 'time': time, 'annotated': annotated,
                            'annotation_path': annotation_path}
                    img_array.append(image_dict)
                img_array.sort(key=lambda x: x['time'])       
               
                exps[exp]['images']['image_array'] = img_array

        print("Found a total of", total_images, "images across all experiments, {:.2f}% of which are annotated.".format(annotated_images/total_images))
        self.db_dict['info']['initialized'] = True
        self.db_dict['data']['experiments'] = exps
