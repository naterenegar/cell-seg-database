# cell-seg-database
This project provides a way to manage sets of unannotated time series images. The need for this stemmed from my own experiences 
labelling [microscopy images](https://ieee-dataport.org/open-access/measurements-cancer-cell-proliferation-using-lab-cmos-capacitance-sensor-time-lapse) for a research project, where manual organization, especially when collaborating, was tedious and fatiguing. 

# Features
Currently, a lot of desired features are unimplemented. 

## Implemented Features
- Create a new database given a directory structure. Image attributes are specific to the project I developed this tool for, but can be changed easily.
- Matplotlib GUI for creating new (unannotated) annotation set from pool of images.
TODO

## Planned Features

### Integrate an active learning loop into the database. 
Might look like this:
- Pull JSON files describing which pixels of which images are annotated
- Construct training set from these annotated pixels (usually in the form of 256x256 subimages)
- Train N models, do annotation suggestion
- Create new annotation set from annotation suggestion
- Keep track of all of this by updating the database records
The main reason this tool is useful for active learning is that it can automatically find annotated and unannotated sampled images to use in the loop. Previously this is done by hand.

# Usage
Run `init_database.py` to get started. This file searchs for a `.db.json` in the working directory and creates a new database if it doesn't find one. It then asks you about the directory tree structure of your files (in my case, images).

# Dependencies
Requires `python3` and some packages:
- matplotlib
- numpy
- cv2

TODO: put all required packages into `pip`-style requirements.txt
