# cell-seg-database
This project provides a way to manage sets of unannotated time series images.
The need for this stemmed from my own experiences labelling [microscopy
images](https://ieee-dataport.org/open-access/measurements-cancer-cell-proliferation-using-lab-cmos-capacitance-sensor-time-lapse)
for a research project, where manual organization, especially when 
collaborating, was tedious and fatiguing. 

# Features
Currently, a lot of desired features are unimplemented, so I'm laying out my
work here. 

## Implemented Features
- Create a new database given a directory structure. Image attributes are
  specific to the project I developed this tool for, but can be changed easily.
- Matplotlib GUI for creating new (unannotated) annotation set from pool of
  images.

## Planned Features

### Integrate an active learning loop into the database Might look like this:
- Pull JSON files describing which pixels of which images are annotated
- Construct training set from these annotated pixels (usually in the form of
  256x256 subimages)
- Train N models, do annotation suggestion
- Create new annotation set from annotation suggestion
- Keep track of all of this by updating the database records The main reason
  this tool is useful for active learning is that it can automatically find
  annotated and unannotated sampled images to use in the loop. Previously this
  is done by hand.

### Develop interface for annotation tools 
The first tool is the one I've been using to do instance segmentation
annotations, [deepcell-label](https://github.com/vanvalenlab/deepcell-label).
This tool is great for labelling cells, but for me has not been so great at
managing lots of images. `cell-seg-database` will create a wrapper around this
tool that does all the miscellaneous management of annotations (e.g. making
sure annotations don't overlap, annotations are in the same data format, etc.). 

It will be difficult to standardize an interface to every tool out there. One
development route could be adding tools one by one, building up a list of
supported tools.


# Usage 
Run `init_database.py` to get started. This file searchs for a `.db.json` in
the working directory and creates a new database if it doesn't find one. It
then asks you about the directory tree structure of your files (in my case,
images).

# Dependencies 
Requires `python3` and some packages:
- matplotlib
- numpy
- cv2

TODO: put all required packages into `pip`-style requirements.txt
