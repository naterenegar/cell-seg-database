#!/usr/bin/env python3

import database

db = database.Database()

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
quit()
