# cell-seg-database
This project provides a CLI for managing and collaborating on semantic
segmentation of large numbers of images. The CLI is essentially glue between a
couple of different tools. 

# Requirements
Software:
- python3.7 or later
- git
- AWS CLI

Python package dependencies can be found in the `requirements.txt` file, and can be installed with
```
python -m pip instal -r requirements.txt
```

# TODO:
- Convert the `sequencer.py` gui code from `matplotlib` to something actually fast (open to web based)
- Put all required packages into `pip`-style requirements.txt
- Fork the annotation tool and git-submodule it
- Add code to register a database and s3 bucket with the code. Right now this is hard-coded
- Integrate an active learning loop into the database 
    - Pull JSON files describing which pixels of which images are annotated
    - Construct training set from these annotated pixels (usually in the form of
      256x256 subimages)
    - Train N models, do annotation suggestion
    - Create new annotation set from annotation suggestion
    - Keep track of all of this by updating the database records The main reason
      this tool is useful for active learning is that it can automatically find
      annotated and unannotated sampled images to use in the loop. Previously this
      is done by hand.
- Customize the annotation tool (deepcell-label)
- Add permission levels 
- Turn into web-app for ease of use (e.g. for large scale annotation)
