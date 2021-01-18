
# We also want this to be able to scan an experiment directory containing
# multiple experiments (as directories). In each directory is some data, and
# the user can pass a parsing function in to construct the database.

# Maybe instead of reading all of the data into memory, we can just construct a
# map of where to find the data. This makes sense since the usual use case is a
# small number of files at a time.

# We also want to store the cell type 

class Database(object):

    def __init__(self, init_file=None):
        self.exps = []
        if init_file:
            # TODO: read JSON and restore state
            pass 


    def __str__(self):
        retstr = "" 
        for (exp, data) in self.exps:
            retstr = retstr + str(exp) + "\n"

        return retstr
   
    # TODO: Currently does not support importing annotations
    def init_database(self, top_dir, exp_prefix):
        pass


    def add_experiment(self, experiment_name, experiment_data):
        # format of experiment_data left up to use case. For ours we'll have
        # two types of data associated with an experiment: images and
        # capacitance measurements. Each datum should be timestamped w.r.t the
        # same time origin
        self.exps.append((experiment_name, experiment_data))
