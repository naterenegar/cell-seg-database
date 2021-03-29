
Database Features:
- Add function to find subset of database that is unannotated, given pairs of
  (x,y) coordinates that define an annotated ROI.
- Add function that takes in an image or set of images, and returns a bool
  denoting if they have been annotated or not
- Given an index into a list of images, pull up an image viewing tool (such as
  ImageJ), with that image and N frames around it. This allows annotators to
  use temporal context clues to better segment the cells. 
- Add support for best-fit temporal indexing across multiple datatypes. e.g. we
  should be able to pull up an image and the capacitance readings that are 
  closest to that image in time
- Add support for annotation tool integration. One way to do this would be a
  user-supplied command for launching the annotation tool

Collaboration Features:
- Devise syncing scheme between annotating agents so no two people mistakenly
  annotate the same thing 

Segmentation:
- Determine how to incorporate temporal context clues into the networks model
  of segmentation

Sensor Correlation:
- 
