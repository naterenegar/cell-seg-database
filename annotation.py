import copy

# Dictionary wrapper for different types of annotations
class ImageAnnotation(object):

    def __init__(self):
        self.ann_dict = {
            'ann_type': 'image',
            'ann_id': 0,
            'valid': False,
            'author': "",
            'contents': {
                'cell_count': None,
                'cell_type': None
            },
            'X': {
                'path': "",
                'ann_size': (256, 256),
                'source_name': "",
                'source_path': "",
                'source_offset': (0, 0)
            },
            'y': {
                'path': ""
            }
        }
    
    def get_dict(self):
        return copy.deepcopy(self.ann_dict)
