#!/usr/bin/env python3

import database

db = database.Database() # Database parser. Looks for a JSON file in the working directory

if not db.is_initialized():
    top_dir = input("Please enter the top level directory of the database, or press enter for default (db): ")
    exp_dir = input("Please enter the experiment subdir, or press enter for default (exps):")
    exp_prefix = input("Please enter the experiment prefix, or press enter for default (exp): ")
    ann_dir = input("Please enter the annotation subdir, or press enter for default (anns): ")

    db.init_database(top_dir=(top_dir if top_dir != '' else 'db'), 
                     exp_dir=(exp_dir if exp_dir != '' else 'exps'),
                     exp_prefix=(exp_prefix if exp_prefix != '' else 'exp'),
                     ann_dir=(ann_dir if ann_dir != '' else 'anns')) 

db.start_command_CLI()


# Active learning loop should look a little bit like this....

# 1. Ask the database to generate a new unlabelled pool, or to load a
# previously generated pool
# 2. Do our active learning steps
# 3. Get a list of suggested annotations, complete with standard image metadata
# 4. Save those annotations into the annotation portion of the database, and
# remove them from the unlabelled pool

# Now, annotating is going to be difficult because you might as well be looking
# at a random sequence of images. This is where the ImageJ tool comes in: we
# open up N images centered around the current Caliban image in ImageJ 

# This should be relatively simple... maybe we can do some NPZ shuffling to
# have Caliban open up one image at a time and save it back to the database...

# Maybe there can be a command to list all of the unannotated images... then a
# "annotate next" which pulls up caliban with the image, and then ImageJ with
# the contextual images.
#
# Again, if I need contextual images to increase the accuracy of my
# annotations, should the network have them? How would that be incorporated

# Also, I should get an estimate on how many hours one active learning loop
# takes. This can be done empircally by recording annotation and training times


quit()
