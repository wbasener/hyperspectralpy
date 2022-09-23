# this imports the numpy package
import numpy as np
# this imports matplotlib
import matplotlib
import matplotlib.pyplot as plt
# this imports the spectral package (see http://www.spectralpython.net/index.html)
from spectral import *

# this is the file name for your image
fname_image = 'C:/Users/wfbsm/OneDrive/Data/AVIRIS Northern VA/f090706t01p00r13rdn_b/processed/radiance_subset_quac'

# this uses the spectral package to read the image data
im = envi.open(fname_image + '.hdr')
# thsi loads the image array
im_arr = im.load()

# here is how we output some of the metadata
print('Number of bands: %d' % im.nbands)
print('Number of rows: %d and columns: %d' % (im.nrows, im.ncols))
print('First 10 band centers:', im.bands.centers[0:9])

# compute the mean spectrum of the image
mean_spectrum = np.mean(np.mean(im_arr,0),0)
# plot the mean
plt.plot(im.bands.centers, mean_spectrum)

# display an RGB image
bands = [30,20,10] # chose the bands to display [red, green, blue]
rgbArray = np.zeros((im.nrows, im.ncols, 3), 'float32') # create the 3D image array
for i in range(2): # loop through the three bands and populate the array from im_arr
    rgbArray[..., i] = np.reshape(im_arr[:, :, int(bands[i])], [im.nrows, im.ncols])
plt.imshow(rgbArray*10) # show the image