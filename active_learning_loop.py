#!/usr/bin/env python3

# This script will suggest `k` images for annotation based on ensemble
# uncertainty and similarity between uncertain images. 

import database
import numpy as np
import copy
import json

K = 100
k = 50

db = database.Database() # Database parser. Looks for a JSON file in the working directory

pool_name = "pool3" # Change or get user input if you have a different pool
loop_tag = "activeloop3"
(X, metadata) = db.load_image_pool(pool_name)

print(len(metadata['images']))

# Convert to grayscale (is this needed??? How much faster does it really make things?)
red = X[:, :, :, 0]                                                                                                                
green = X[:, :, :, 1]                                                                                                              
blue = X[:, :, :, 2]                                                                                                               

gray = (                                                                                                                  
    0.299 * red                                                                                                                    
    + 0.587 * green                                                                                                                
    + 0.114 * blue)                                                                                                                

X_color = X.copy()
X = np.expand_dims(gray, axis=-1)
num_imgs = X.shape[0]

# ### Run PCA on images
# First we need to reshape our images, then we will run PCA and transform the
# images down to the 95% explained variance point. This `d` dimensional vector
# will give a good way to compare images once we need to measure similarity.

# Flatten images
from functools import reduce
import operator

X_newshape = (X.shape[0], reduce(operator.mul, X.shape[1:], 1))
X_flat = np.reshape(X, X_newshape)

print('New shape for flattened pool:', X_flat.shape)

from sklearn.decomposition import PCA
import time

# WARNING: You may need to use the incremental PCA class from sklearn if you run out of memory

print('Starting PCA on images...')
t1 = time.perf_counter()
color_pca = PCA(n_components=0.95)
X_proj = color_pca.fit_transform(X_flat)
t2 = time.perf_counter()
print(f'PCA on images took {t2 - t1:0.4f} seconds')
print('95% explained variance dimension:', X_proj.shape[1])


# ### Predict Annotations
# Now that we have a representation of images for similarity metrics, the next step is to run the images through all of the models. 

# Load and run each model on the images. Save just the predicted annotation
import os
from tensorflow import keras
from deepcell import model_zoo

models_dir = '../training/data/models/active_s1'
model_names = os.listdir(models_dir)

# TODO: This assumes something about the structure of the network... Is there a way to save the network structure?
model_names = list(filter(lambda x: True if '.h5' in x else False, model_names)) # get just the names that are h5 weight archives

receptive_field = 127
n_skips = 3

# We'll use this same model for all iterations, just with swapped weights
fgbg_model = model_zoo.bn_feature_net_skip_2D(
    n_features=2, # foreground, background (i.e. cell, not cell)
    receptive_field=receptive_field,
    n_skips=n_skips,
    n_conv_filters=64,
    n_dense_filters=128,
    input_shape=tuple(X.shape[1:]),
    last_only=False
)

pixelwise_uncertainty = np.zeros(X.shape[:-1])
gran = 10

t1 = time.perf_counter()
for n in range(0, X.shape[0], gran):
    images = X[n:n+gran] if n + gran <= X.shape[0] else X[n:]
    predictions = np.zeros(tuple([len(model_names)]) + images.shape[:-1] + tuple([2]))
    for i, mp in enumerate(model_names):
        fgbg_model.load_weights(os.path.join(models_dir, mp))
        predictions[i] = fgbg_model.predict(images)[-1] 
    uncertainty = np.sum(np.var(predictions, axis=0), axis=-1) # calculate variance across all classes and sum
    if n + 10 <= X.shape[0]:
        pixelwise_uncertainty[n:n+gran] = uncertainty.copy()
    else:
        pixelwise_uncertainty[n:] = uncertainty.copy()
    
    t2 = time.perf_counter()
    print(gran + n, 'of', X.shape[0], f'images done in {t2 - t1:0.2f} seconds...')


# Per image uncertainty is the mean uncertainty of all pixels in the image
mean_newshape = (pixelwise_uncertainty.shape[0], reduce(operator.mul, pixelwise_uncertainty.shape[1:], 1))
imagewise_uncertainty = np.mean(np.reshape(pixelwise_uncertainty, mean_newshape), axis=1)

# ### Suggest Annotations
# Annotation Suggestion, once the uncertainties are calculated, takes three steps:
# 1. Find the K most uncertain images
# 2. Calculate the pairwise similarities of those K images with all images in the pool
# 3. Use those similarities to greedily approximate a k-subset of the K images that is most representative of the pool

# Find the top K most uncertain images
Sc = [] # Candidate set
tmp = imagewise_uncertainty.copy()
for i in range(K):
    idx = np.argmax(tmp)
    Sc.append(idx)
    tmp[idx] = 0

from sklearn.metrics.pairwise import cosine_similarity

# Compute all of the image cross similarities 
t1 = time.perf_counter()
sims = np.zeros((K, X_proj.shape[0])) # K x num_imgs array
for i in range(K):
    I_Sc = np.expand_dims(X_proj[Sc[i]], 0)
    
    for j in range(X_proj.shape[0]):
        I_Sa = np.expand_dims(X_proj[j], 0)
        sims[i][j] = abs(cosine_similarity(I_Sc, I_Sa)[0][0])
        
t2 = time.perf_counter()
print(K, f"sets of cross similarities computed in {t2 - t1:0.4f} seconds...")

# Assumes that sims is |Sc| x |Su| array of cosine similarities.
def F_presims(Sa, sims):
    rep = 0
    for x in range(sims.shape[1]):
        rep = rep + max([sims[i][x] for i in Sa])
    return rep

# Find a k-subset (k < K) of K_uncertain that 
# is the most representative of the full image pool
Sa = [] # Suggested Annotation set
Sc_idxs = list(range(len(Sc)))
t1 = time.perf_counter()
for i in range(k):
    max_rep = 0
    max_rep_idx = 0
    
    # Find the maximum marginal representativeness by adding the 
    # remaining images to the set one at a time
    for idx in Sc_idxs: 
        Sa_tmp = Sa + [idx]
        rep_tmp = F_presims(Sa_tmp, sims)
        if rep_tmp >= max_rep:
            max_rep = rep_tmp
            max_rep_idx = idx
    
    Sc_idxs.remove(max_rep_idx)
    Sa.append(max_rep_idx)

t2 = time.perf_counter()
print("Found representative subset of", k, f"images in {t2 - t1:0.2f} seconds")
Sa = [Sc[i] for i in Sa] # Change Sa from indicies of Sc to indices of Su


# ### Save results
# Remove the suggested annotations from the pool, then save the new pool and the suggested images.

# Remove suggested annotations from pool, then save the two new sets
#X_color = imgs['X']
image_data = metadata['images']

sanns = np.zeros(tuple([len(Sa)]) + X_color.shape[1:])
sanns_data = []
for i, idx in enumerate(sorted(Sa, reverse=True)):
    sanns[i] = X_color[idx]
    sanns_data.append(copy.deepcopy(image_data[idx]))
    del(image_data[idx])    

X_color = np.delete(X_color, Sa, axis=0)
db.save_image_pool(pool_name, X_color, image_data)
db.add_blank_annotations(sanns_data, tag=loop_tag)
db.save()
