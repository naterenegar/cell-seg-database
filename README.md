# cell-seg-database
This project provides a CLI for managing and collaborating on semantic
segmentation of large numbers of images. The CLI is essentially glue between a
couple of different tools. 

# Requirements
Software:
- python3.7
- python3.7 venv
- git
- AWS CLI
- deepcell-label

Python package dependencies can be found in the `requirements.txt` file.  The
use of a virtual environment is recommended. 

## Linux
Clone the annotation tools
```
git submodule init
git submodule update
```

Get the python environment set up
```
python3.7 -m venv venv # create a virtual environment
source venv/bin/activate # activate the environment
pip install -r requirements.txt # install packages, but only in the virtual environment
```

Start the database
```
python start_database.py 
```

## Windows (cmd)
Clone the annotation tools
```
git submodule init
git submodule update
```

Get the python environment set up
```
python3.7 -m venv venv # create a virtual environment
venv\Scripts\activate.bat # activate the environment
pip install -r requirements.txt # install packages, but only in the virtual environment
```

Start the database
```
python start_database.py 
```

# TODO:
- Convert the `sequencer.py` GUI code from `matplotlib` to something actually fast (open to web based)
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
