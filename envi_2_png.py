import os
import numpy as np
from spectral import envi
from PIL import Image


dirname = 'C:\\Users\\wb8by\\Downloads\\Morven_04_26_2024\\Hyperspectral\\2024_04_23_19_22_02_293'
dirname = 'C:\\Users\\wb8by\\Downloads\\Morven_04_26_2024\\Hyperspectral\\2024_04_23_19_53_45_915'

# iterating over all files
for file in os.listdir(dirname):
    if file.endswith('.bin'):
        try:
            fname_hdr = os.path.join(dirname,file[:-4]+'.hdr')
            fname_im = os.path.join(dirname,file)
            print(fname_im)  # printing file name of desired extension
            print(fname_hdr)  # printing file name of desired extension

            im = envi.open(fname_hdr, fname_im)
            wl = np.asarray(im.bands.centers)
            b = np.argmin(np.abs(wl-450))
            g = np.argmin(np.abs(wl-550))
            r = np.argmin(np.abs(wl-650))
            RGB = np.zeros((im.nrows,im.ncols,3))
            RGB[:,:,0] = im.read_band(b)
            RGB[:,:,1] = im.read_band(g)
            RGB[:,:,2] = im.read_band(r)
            for i in range(3):
                bottom = np.percentile(RGB[:,:,i],2)
                top = np.percentile(RGB[:,:,i],98)
                RGB[RGB[:,:,i]<bottom,i]=bottom
                RGB[RGB[:,:,i]>top,i]=top
                RGB[:,:,i] = (RGB[:,:,i]-bottom)*254/(top-bottom)
            im = Image.fromarray(RGB.astype(np.uint8))
            im.save(os.path.join(dirname,file[:-4]+'_rgb.jpg'))
        except:
            print('===================')
            print('Failed: '+file)
            print('===================')
