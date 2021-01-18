#!/usr/bin/env python3

import database

db = database.Database()

# Read JSON file for database object
# Check if the database has been initialized
#  

# What we want to do now is we want to look at a root directory and initalize
# everything into the database. In other words, we want to define a file
# structure the database can adhere to.

# I think we can have all of the raw data organized by experiment, and in each
# experiment directory we have data organized by type into subdirectories. So
# for example, we'd have a top level /database/ with all of the experiments in
# it, and in each experimennt, e.g. exp01/, we'd have a subfolder for each type
# of raw data. In our case, this is image data (.jpgs) and electrode data.
# In each experiment folder, we can also have a <datatype>_ann directory for
# annotated versions of the data. We'll organize this on an experiment level,
# but also have a top level annotation folder for construction of datasets for
# training, validation, and other analyses.

# As far as storing state, I think we'll track each files location, type,
# timestamp, etc. in a top level JSON. This should make looking up data easy,
# i.e. deserialize JSON into datastructure -> query datastructure

no_init_file = True

if no_init_file:
    top_dir = input("Please enter the top level directory of the database: ")
    exp_dir = input("Please enter the experiment subdir: ")
    exp_prefix = input("Please enter the experiment prefix: ")

    db.init_database(top_dir, exp_dir, exp_prefix)
    quit()

    # Let's create a JSON object for an experiment  
    # Python can automagically serialize the following types into JSON:
    #   dict -> object
    #   list,tuple -> array
    #   str -> string
    #   int,long,float -> number 
    #   True -> true
    #   False -> false
    #   None -> null
    # These should be sufficient
