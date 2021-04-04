import copy
import os

# This file defines wrappers around dictionaries for various artifacts in the
# database. I haven't actually used them yet. The plan is to use them to make
# the database less hardcoded and more customizable (e.g. supply an inheritance
# scheme that defines how data should be oragnized instead of hardcoding
# dictionaires)

# I really don't have that much experience with databases, so this could be a
# dumb way to do things.

# This defines a raw image in the database 
class SourceImage(object):
    
    def __init__(self, init_dict=None):
        self.dict = {
            "name": "",
            "resolution": [-1, -1],
            "source_exp": "",
            "path": "",
            "cell_type": None,
            "time": -1,
            "annotations": []
        }

    def get_dict(self):
        return copy.deepcopy(self.dict)

# subimage metadata of a source image 
class SubImage(object):
    
    def __init__(self):
        self.dict = {
            'size': (256, 256),
            'source_name': "",
            'source_path': "",
            'source_offset': (0, 0)
        }
        pass

    def on_disk(self):
        if self.dict['path'] != "" and os.path.exists(self.dict['path']):
            return True
        else:
            return False

    def get_dict(self):
        return copy.deepcopy(self.dict)

# This is a subimage that is annotated
class ImageAnnotation(object):

    def __init__(self):
        self.dict = {
            'ann_type': 'image',
            'ann_id': -1,
            'valid': False,
            'annotator': "",
            'annotatorType': None, # Hand annotated? or model annotated?
            'contents': {
                'experiment': -1,
                'time': -1,
                'cell_count': -1,
                'cell_type': None
            },
            'X': {
                'path': "",
                'size': (256, 256),
                'source_name': "",
                'source_path': "",
                'source_offset': (0, 0)
            },
            'y': {
                'path': ""
            },
            'npzs': [] # List of NPZs paths containing this annotation 
        }
    
    def get_dict(self):
        return copy.deepcopy(self.dict)

def subimage_dict_to_ann(d):
    ann = ImageAnnotation()
    ann['X']['size'] = d['size']
    ann['X']['source_name'] = d['source_name']
    ann['X']['source_offset'] = d['source_offset']
    ann['X']['source_path'] = d['source_path']

    return ann
