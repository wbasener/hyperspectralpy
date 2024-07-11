import numpy as np
import pandas as pd
import rasterio as rio
import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import random
from spectral import *
import csv
import os
import timeit
from os import listdir
from os.path import isfile, join
from distutils.dir_util import copy_tree
from PIL import Image
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from itertools import compress
import scipy.stats as st
from scipy.optimize import nnls
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import * 


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        #self.setFrameShadow(QFrame.Sunken)


class QVLine(QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

class inputs_struc:
    def __init__(self):
        self.abundances = 0
        self.contrast = 0
        self.im_fnames = 0
        self.det_lib_fname = 0
        self.verbose = 1
        
class inputs_bd_struc:
    def __init__(self):
        self.im_fnames = 0
        self.verbose = 1
        
class stats_struc:
    def __init__(self, mean, cov, evals, evecs):
        self.mean = mean
        self.cov = cov
        self.eigenvalues = evals
        self.eigenvectors = evecs
        
class whiten_struc:
    def __init__(self):
        self.W = 0
        self.m = 0
        
class Wim_struc:
    def __init__(self, im3d, im2d):
        self.im3d = im3d
        self.im2d = im2d

class ROI_struc:
    def __init__(self):
        self.name = ''
        self.npts = 0
        self.color = [0,0,0]
        self.locs = ''
        self.spectra = ''
        self.wl = []
        
class image_struc:
    def __init__(self):
        self.im = 0
        self.arr = 0
        self.name = 0
        
class spectral_contrast_struc:
    def __init__(self):
        self.ace_predicted = 0
        self.abundnaces = 0
        self.subpixel_ace = 0
        self.fullpixel_ace = 0
        self.subpixel_ace_std = 0
        self.fullpixel_ace_std = 0
        self.image_rgb = 0
        self.image_data = 0
        self.image_name = []
        self.names = 0
        
class sc_library_plot_data_struc:
    def __init__(self):
        self.wl = 0
        self.dict = {}
        
class sc_ace_predicted_plot_data_struc:
    def __init__(self):
        self.abundances = 0
        self.dict = {}

def timecheck_start(string,verbose):
    start_time = 0
    if verbose > 0:
        start_time = timeit.default_timer()
        print(string)
    return start_time
    
def timecheck_end(start_time,verbose):
    if verbose:
        print('Elapsed time: '+str(timeit.default_timer()-start_time))
        
def open_read_images(fnames,verbose):
    start_time = timecheck_start('Reading Images.',verbose)
    images = []
    for fname in fnames:
        fname,ok = is_image_file(fname)
        image = image_struc()
        image.im = envi.open(fname+'.hdr')
        image.arr = envi_load(image.im)
        image.name = os.path.basename(fname)
        images.append(image)
    timecheck_end(start_time,verbose)
    return images

def envi_load(im):
    # load the image using the envi command from spectralpy
    im_arr = im.load()
    
    # check for a reflectance scale factor
    # (which is used by ENVI, but is not in the spectralpy routine)
    if 'reflectance scale factor' in im.metadata.keys():
        # apply the reflectance scale factor if it exists and is valid
        try:
            im_arr = im_arr*float(im.metadata['reflectance scale factor'])
        except:
            pass
        
    # check for a bad bands list
    # (which is used by ENVI, but is not in the spectralpy routine)
    if 'bbl' in im.metadata.keys():
        # apply the bad bands list if it exists and is valid
        try:
            im_arr = im_arr[:,:,np.asarray(im.metadata['bbl'])==1]
        except:
            pass
    return im_arr

def apply_bbl(im):

    if 'bbl' in im.metadata.keys():
        # apply the bad bands list if it exists and is valid
        try:
            im.bands.centers = [im.bands.centers[i] for i in np.where(im.metadata['bbl'])[0]]
            im.nbands = len(im.bands.centers)
            shape = list(im.shape)
            shape[2] = len(im.bands.centers)
            im.shape = tuple(shape)
            if 'band names' in im.metadata.keys():
                try:
                    im.metadata['band names'] = [im.metadata['band names'][i] for i in np.where(im.metadata['bbl'])[0]]
                except:
                    print('Applying bad bands list to band names failed.')
        except:
            pass
    return im

def is_tiff_image_file(im_fname):
    try:
        # try to open as tiff file
        Im = rasterio.open(im_fname)
        return im_fname, True
    except:
        return im_fname, False

def is_image_file(im_fname):
    try:
        # try to open as ENVI file
        try:
            im = envi.open(im_fname+'.hdr')
            return im_fname, True
        except:
            # sometimes images are saved with ".img" or similar suffix that must be removed from header
            # this will also enable opening an image of the sued selects the header file
            im_fname_nosuffix = im_fname[:im_fname.rfind(".")]
            im_fname_hdr = im_fname_nosuffix+'.hdr'
            im = envi.open(im_fname_hdr, im_fname)
            return im_fname, True
    except:
        return im_fname, False

def is_library_file(lib_fname):
    if (len(lib_fname) > 1):
        lib_fname = lib_fname[0]
    try:
        try:
            print(1)
            lib = envi.open(lib_fname+'.hdr')
            print(2)
            return lib, True
        except:
            print(3)
            # sometimes images are saved with ".img" or similar suffix that must be removed from header
            # this will also enable opening an image of the sued selects the header file
            lib__fname_nosuffix = lib_fname[:lib_fname.rfind(".")]
            lib = envi.open(lib__fname_nosuffix+'.hdr')
            print(4)
            return lib, True
    except:
        return None, False


def spectra_names_html(fname_lib):
    lib = envi.open(fname_lib+'.hdr') 
    text = '<ul>\n'
    for name in lib.names:
        text = text+'<li>'+name+'</li>\n'
    text = text + '</ul>\n'
    return text
        

def load_and_resample_library(fname_lib,im,im_arr,verbose, rescale_x=True, rescale_y=True):
    start_time = timecheck_start('Loading and resampling library.',verbose) 
    # load detection library 
    file_name,extension = os.path.splitext(fname_lib)
    lib = envi.open(file_name+'.hdr')   
    
    if rescale_x == True:
        # convert library to image wavelength units
        if np.mean(im.bands.centers) < 100:
            # image units are micrometers
            if np.mean(lib.bands.centers) < 100:
                wl_scale = 1.
            else:
                wl_scale = 1/1000.
                if verbose==1:
                    print('WARNING: Converting library from nanometers to microns.')
        else:
            # image units are nanometers
            if np.mean(lib.bands.centers) < 100:
                wl_scale = 1000.
                if verbose==1:
                    print('WARNING: Converting library from microns to nanometers.')
            else:
                wl_scale = 1
        lib.bands.centers = wl_scale*np.array(lib.bands.centers)
    
    # resample library to image wavelengths
    # compute resampling matrix
    resample = resampling.BandResampler(lib.bands, im.bands)
    # resample
    lib.spectra = np.matmul(lib.spectra,resample.matrix.T)
    lib.bands.centers = im.bands.centers

    if rescale_y == True:
        # Scale library intensities to image if they an order of magnitude off
        im_arr_mean = np.mean(im_arr)
        lib_mn = np.mean(np.mean(lib.spectra))
        if np.max([im_arr_mean/lib_mn,lib_mn/im_arr_mean]) > 10:
            print('WARNING: Image and library seem to have different measurement scales.  Rescaling library to match image.')
            im_scale = np.ceil(np.log10(im_arr_mean))
            lib_scale = np.ceil(np.log10(lib_mn))
            intensity_scale = 10**(im_scale - lib_scale)
            lib.spectra = intensity_scale*lib.spectra
    timecheck_end(start_time,verbose)
    return lib

def resample_library(lib,im,im_arr,verbose, rescale_x=True, rescale_y=True):
    start_time = timecheck_start('Loading and resampling library.',verbose)
    
    if rescale_x == True:
        # convert library to image wavelength units
        if np.mean(im.bands.centers) < 100:
            # image units are micrometers
            if np.mean(lib.bands.centers) < 100:
                wl_scale = 1.
            else:
                wl_scale = 1/1000.
                if verbose==1:
                    print('WARNING: Converting library from nanometers to microns.')
        else:
            # image units are nanometers
            if np.mean(lib.bands.centers) < 100:
                wl_scale = 1000.
                if verbose==1:
                    print('WARNING: Converting library from microns to nanometers.')
            else:
                wl_scale = 1
        lib.bands.centers = wl_scale*np.array(lib.bands.centers)

    # resample library to image wavelengths
    # compute resampling matrix
    resample = resampling.BandResampler(lib.bands, im.bands)
    # resample
    lib.spectra = np.matmul(lib.spectra,resample.matrix.T)
    lib.bands.centers = im.bands.centers

    if rescale_y == True:
        # Scale library intensities to image if they an order of magnitude off
        im_arr_mean = np.mean(im_arr)
        lib_mn = np.mean(np.mean(lib.spectra))
        if np.max([im_arr_mean/lib_mn,lib_mn/im_arr_mean]) > 10:
            print('WARNING: Image and library seem to have different measurement scales.  Rescaling library to match image.')
            im_scale = np.ceil(np.log10(im_arr_mean))
            lib_scale = np.ceil(np.log10(lib_mn))
            intensity_scale = 10**(im_scale - lib_scale)
            lib.spectra = intensity_scale*lib.spectra
    timecheck_end(start_time,verbose)
    return lib
        
def make_jpg_array(image):
    if np.mean(image.im.bands.centers) > 100:
        idx_red = np.argmin(abs(np.asarray(image.im.bands.centers)-650))
        idx_green = np.argmin(abs(np.asarray(image.im.bands.centers)-550))
        idx_blue = np.argmin(abs(np.asarray(image.im.bands.centers)-450))
    else:
        idx_red = np.argmin(abs(np.asarray(image.im.bands.centers)-0.65))
        idx_green = np.argmin(abs(np.asarray(image.im.bands.centers)-0.55))
        idx_blue = np.argmin(abs(np.asarray(image.im.bands.centers)-0.45))
    rgb_array = image.arr[:,:,[idx_red,idx_green,idx_blue]]
    for idx in range(3):
        band = rgb_array[:,:,idx]
        low = np.max([np.percentile(band,2),0])
        band = band - low
        high = np.percentile(band,98)
        band = band / high
        band[band<0]=0
        band[band>1]=1
        rgb_array[:,:,idx] = band
    return rgb_array
            
def compute_screened_pca(im_arr,verbose):
    start_time = timecheck_start('Computing statistics.',verbose)
    # build the image array as a list
    [nrows,ncols,nbands] = np.shape(im_arr)
    imlist = np.reshape(im_arr,(nrows*ncols,nbands))
    
    ## Compute first covariance ##
    # subtract mean from imlist
    mean = np.mean(imlist,axis=0)
    imlist_meansub = imlist-np.tile(mean,[nrows*ncols,1])     
    # compute the (first stage) covariance
    cov = np.matmul(imlist_meansub.T,imlist_meansub)/(ncols*nrows)
    
    ## whiten the image list and compute RX ##
    # compute eigen values and eigenvectors
    evals,evecs = np.linalg.eig(cov)    
    # remove small and negative eigenvalues
    eval_threshold = np.max(evals)/10**8
    evals[np.where(evals<eval_threshold)] = eval_threshold
    # compute the whiteing matrix and whiten imlist
    W = np.transpose(np.matmul(evecs,(np.diag(1/np.sqrt(evals)))))
    Wimlist = np.matmul(W,imlist.T).T
    # compute RX
    rx = np.linalg.norm(Wimlist,axis=1)
    
    # Threshold originonal imagelist by RX values
    rx_thesh = np.percentile(rx,95)
    imlist = imlist[rx<rx_thesh]
    [nrows,nbands] = np.shape(imlist)
    # subtract mean from imlist
    mean = np.mean(imlist,axis=0)
    imlist_meansub = imlist-np.tile(mean,[nrows,1])  
        
    ## Compute final cov and stats
    cov = np.matmul(imlist_meansub.T,imlist_meansub)/(ncols*nrows)
    evals,evecs = np.linalg.eig(cov)    
    # remove small and negative eigenvalues
    eval_threshold = np.max(evals)/10**8
    evals[np.where(evals<eval_threshold)] = eval_threshold
    timecheck_end(start_time,verbose)
    return stats_struc(mean,cov,evals,evecs)
    
    
def compute_whitening(pc,verbose):  
    start_time = timecheck_start('Computing whiten transform.',verbose)
    W = whiten_struc()    
    W.m = pc.mean
    eval_threshold = np.max(pc.eigenvalues)/10**8
    evals = pc.eigenvalues+0
    # remove small and negative eigenvalues
    evals[np.where(evals<eval_threshold)] = eval_threshold
    # compute the whiteing matrix
    W.W = np.transpose(np.matmul(pc.eigenvectors,(np.diag(1/np.sqrt(evals)))))
    timecheck_end(start_time,verbose)
    return W
    

def whiten_library(lib,W,verbose):
    start_time = timecheck_start('Whitening library.',verbose)
    # Whiten the detect spectra
    wlib = np.zeros(np.shape(lib.spectra))
    counter = 0
    for s in lib.spectra:
        wlib[counter,:] = np.matmul(W.W,s-W.m)
        counter = counter+1
    timecheck_end(start_time,verbose)
    return wlib
    
def whiten_image(W,im_arr,im,verbose):
    start_time = timecheck_start('Whitening the image.',verbose)
    # Whiten the image    
    Wim2d = np.reshape(im_arr,[im.ncols*im.nrows,im.nbands])
    # subtract the mean   
    Wim2d = Wim2d-np.tile(W.m,[im.ncols*im.nrows,1])
    # multiply by whitening matrix
    Wim2d = np.matmul(W.W,Wim2d.T).T    
    # build the 3-dimensional cube
    Wim3d = np.reshape(Wim2d,[im.nrows,im.ncols,im.nbands])
    Wim = Wim_struc(Wim3d, Wim2d)
    timecheck_end(start_time,verbose)
    return Wim
    
def ace(Wim,Wdet_lib,verbose):
    start_time = timecheck_start('Computing ACE on the image.',verbose)
    [nrows,ncols,nbands] = np.shape(Wim.im3d)
    [nspectra,nbands] = np.shape(Wdet_lib)
    # compute the denominator (nor target spectrum times norm pixel spectrum)
    inv_det_norms = 1/np.linalg.norm(Wdet_lib,axis=1)
    inv_det_norms_tiled = np.tile(inv_det_norms,[nrows*ncols,1])
    inv_pix_norms = 1/np.linalg.norm(Wim.im2d,axis=1)
    inv_pix_norms_tiled = np.transpose(np.tile(inv_pix_norms,[nspectra,1]))
    # compute the numerator (pixel spectrum dot product target spectrum)
    XdotT = np.matmul(Wim.im2d,np.transpose(Wdet_lib))
    denominator = np.multiply(inv_det_norms_tiled,inv_pix_norms_tiled)
    # take the ratio, and build into image shape
    ace = np.reshape(np.multiply(XdotT,denominator),[nrows,ncols,nspectra])
    timecheck_end(start_time,verbose)
    return ace
    
def mf(Wim,Wdet_lib,verbose):
    start_time = timecheck_start('Computing MF on the image.',verbose)
    [nrows,ncols,nbands] = np.shape(Wim.im3d)
    [nspectra,nbands] = np.shape(Wdet_lib)
    # compute the denominator (nor target spectrum times norm pixel spectrum)
    inv_det_norms = 1/np.linalg.norm(Wdet_lib,axis=1)
    inv_det_norms_tiled = np.tile(inv_det_norms,[nrows*ncols,1])
    # compute the numerator (pixel spectrum dot product target spectrum)
    XdotT = np.matmul(Wim.im2d,np.transpose(Wdet_lib))
    denominator = np.multiply(inv_det_norms_tiled,inv_det_norms_tiled)
    # take the ratio, and build into image shape
    mf = np.reshape(np.multiply(XdotT,denominator),[nrows,ncols,nspectra])
    timecheck_end(start_time,verbose)
    return mf
        
def make_sc_jpg(image):
    idx_red = np.argmin(abs(np.asarray(image.im.bands.centers)-0.65))
    idx_green = np.argmin(abs(np.asarray(image.im.bands.centers)-0.55))
    idx_blue = np.argmin(abs(np.asarray(image.im.bands.centers)-0.45))
    rgb_array = image.arr[:,:,[idx_red,idx_green,idx_blue]]
    for idx in range(3):
        rgb_array[:,:,idx] = rgb_array[:,:,idx] - np.min(rgb_array[:,:,idx])
        rgb_array[:,:,idx] = 255*rgb_array[:,:,idx] / np.max(rgb_array[:,:,idx])
    rgb_im = Image.fromarray(rgb_array.astype(np.uint8))
    return rgb_im
            
def write_sc_library_analysis(sc_list,images,inputs):
    # write file in stdev units
    myFile = open(os.path.join(inputs.output_dirname,os.path.basename(inputs.det_lib_fname)+'_analysis_stdev.csv'), 'wb')
    with myFile:  
        writer = csv.writer(myFile)
        header = ['Spectrum Name']
        for image in images:
            image_name = os.path.basename(image.name)
            header.append(image_name+' subpixel')
            header.append(image_name+' fullpixel')
        writer.writerow(header)
        for spec_idx in range(len(sc_list[0].names)):
            row_text = [sc_list[0].names[spec_idx]]
            for sc_idx in range(len(sc_list)):
                row_text.append('{:.2f}'.format(sc_list[sc_idx].subpixel_ace_std[spec_idx]))
                row_text.append('{:.2f}'.format(sc_list[sc_idx].fullpixel_ace_std[spec_idx]))
            writer.writerow(row_text)
    # rwite file in EFAR units
    myFile = open(os.path.join(inputs.output_dirname,os.path.basename(inputs.det_lib_fname)+'_analysis_ace.csv'), 'wb')
    with myFile:  
        writer = csv.writer(myFile)
        header = ['Spectrum Name']
        for image in images:
            image_name = os.path.basename(image.name)
            header.append(image_name+' subpixel')
            header.append(image_name+' fullpixel')
        writer.writerow(header)
        for spec_idx in range(len(sc_list[0].names)):
            row_text = [sc_list[0].names[spec_idx]]
            for sc_idx in range(len(sc_list)):
                row_text.append('{:.2f}'.format(sc_list[sc_idx].subpixel_ace[spec_idx]))
                row_text.append('{:.2f}'.format(sc_list[sc_idx].fullpixel_ace[spec_idx]))
            writer.writerow(row_text)
    
def spectral_contrast(Wim,Wdet_lib,det_lib,sample_size,abundances,im_mean,im_name,image_rgb,verbose):
    start_time = timecheck_start('Computing spectral contrast.',verbose)
    num_abundnaces = len(abundances)
    [npix,nbands] = np.shape(Wim.im2d)
    [nspectra,nbands] = np.shape(Wdet_lib)
    # pull random sample of image spectra
    indices = random.sample(range(npix),sample_size)
    sample = Wim.im2d[indices,:]
    mixtures = np.zeros([sample_size*num_abundnaces,nbands])
    ace_predicted = np.zeros([nspectra,num_abundnaces])
    subpixel_ace = np.zeros(nspectra)
    fullpixel_ace = np.zeros(nspectra)
    subpixel_ace_std = np.zeros(nspectra)
    fullpixel_ace_std = np.zeros(nspectra)
    stdev = np.zeros(nspectra)
    
    for spec_idx in range(nspectra):
        # compute ace score at required abundances
        s = Wdet_lib[spec_idx,:]
        s_tiled = np.tile(s,[sample_size,1])
        # adding noise
        noise = np.random.normal(loc=0, scale=np.std(sample), size=np.shape(s_tiled))
        s_tiled = s_tiled + noise
        for i in range(num_abundnaces):
            mixtures[range(i*sample_size,i*sample_size+sample_size),:] = (abundances[i]/100.)*s_tiled + (1.-abundances[i]/100.)*sample    
        # compute the denominator (nor target spectrum times norm pixel spectrum)
        inv_det_norm_repeated = np.ones(sample_size*num_abundnaces)/np.linalg.norm(s)
        inv_pix_norms = 1/np.linalg.norm(mixtures,axis=1)
        # compute the numerator (pixel spectrum dot product target spectrum)
        XdotT = np.matmul(mixtures,np.transpose(s))
        denominator = np.multiply(inv_det_norm_repeated,inv_pix_norms)
        # take the ratio, and build into image shape
        ace_array = np.reshape(np.multiply(XdotT,denominator),[num_abundnaces,sample_size])
        
        # compute standard deviation on background sample
        # compute the denominator (nor target spectrum times norm pixel spectrum)
        inv_det_norm_repeated = np.ones(sample_size)/np.linalg.norm(s)
        inv_pix_norms = 1/np.linalg.norm(sample,axis=1)
        # compute the numerator (pixel spectrum dot product target spectrum)
        XdotT = np.matmul(sample,np.transpose(s))
        denominator = np.multiply(inv_det_norm_repeated,inv_pix_norms)
        stdev[spec_idx] = np.std(np.multiply(XdotT,denominator))
        
        # compute results to save
        ace_predicted[spec_idx,:] = np.mean(ace_array,axis=1)
        idx_10 = np.argmin(abs(np.asarray(abundances)-10))
        idx_80 = np.argmin(abs(np.asarray(abundances)-80))
        subpixel_ace[spec_idx] = ace_predicted[spec_idx,idx_10]
        fullpixel_ace[spec_idx] = ace_predicted[spec_idx,idx_80]
        subpixel_ace_std[spec_idx] = ace_predicted[spec_idx,idx_10]/stdev[spec_idx]
        fullpixel_ace_std[spec_idx] = ace_predicted[spec_idx,idx_80]/stdev[spec_idx]
        if verbose:
            print('Spectral Prediction: ['+'{:.2f}'.format(subpixel_ace[spec_idx])+'|'+'{:.2f}'.format(fullpixel_ace[spec_idx])+'] '+det_lib.names[spec_idx])
            
    # put results in a structure
    spectral_contrast = spectral_contrast_struc()
    spectral_contrast.ace_predicted = ace_predicted
    spectral_contrast.abundances = abundances
    spectral_contrast.fullpixel_ace = fullpixel_ace
    spectral_contrast.subpixel_ace_std = subpixel_ace_std
    spectral_contrast.fullpixel_ace_std = fullpixel_ace_std
    spectral_contrast.subpixel_ace = subpixel_ace
    spectral_contrast.names = det_lib.names
    spectral_contrast.image_rgb = image_rgb
    spectral_contrast.image_data = im_mean
    spectral_contrast.image_name = im_name
    timecheck_end(start_time,verbose)
    return spectral_contrast
   
def compute_sc_library_analysis(inputs):
    ### Read that Data
    # Read the image files
    start_time = timecheck_start('Computing Spectral Contrast.',inputs.verbose)
    images = open_read_images(inputs.im_fnames,inputs.verbose) 
    
    sc_list = []
    for image in images:
        # get the name of the image
        im_name = os.path.basename(image.name)

        # Save a jpg of the iamge
        image_rgb = make_sc_jpg(image)
        
        # Read the detection library
        det_lib = load_and_resample_library(inputs.det_lib_fname,image.im,image.arr,inputs.verbose)
        
        # Compute Statistics and Whitening Transform
        pc = compute_screened_pca(image.arr,inputs.verbose)
        W = compute_whitening(pc,inputs.verbose)
        
        # Whiten the detection library
        Wdet_lib = whiten_library(det_lib,W,inputs.verbose)
        # Whiten the image
        Wim = whiten_image(W,image.arr,image.im,inputs.verbose)
        
        # Compute the spectral contrast metrics
        m1 = np.mean(image.arr, axis=0)
        im_mean = np.mean(m1, axis=0)
        #Use this to enable plots of ACE vs Abundance
        sc_list.append(spectral_contrast(Wim,Wdet_lib,det_lib,inputs.sample_size,inputs.abundances,im_mean,im_name,image_rgb,inputs.verbose))
    
    # save the result
    #write_sc_library_analysis(sc_list,images,inputs) # no need to output a csv - analysis in viewer is sufficient
    timecheck_end(start_time,inputs.verbose)   
    return sc_list

def make_sc_list_dictionary(sc_list,images,inputs):
    # This function reformats the spectral contrast data into a list for viewing
    # in the Spectral Contrast GUI
    
    # construct the header labels
    print('starting spectra contrast list dictionary')
    header_labels = ['Spectrum Name']
    for image in images:
        image_name = os.path.basename(image.name)
        header_labels.append(image_name+'\n subpixel')
        header_labels.append(image_name+'\n fullpixel')
    for image in images:
        image_name = os.path.basename(image.name)
        header_labels.append(image_name+'\n subpixel')
        header_labels.append(image_name+'\n fullpixel')
         
    # add the spectra as a list (stdev untis)
    data_list = []
    for spec_idx in range(len(sc_list[0].names)):
        row_text = [sc_list[0].names[spec_idx]]
        for sc_idx in range(len(sc_list)):
            row_text.append('{:.2f}'.format(sc_list[sc_idx].subpixel_ace_std[spec_idx]))
            row_text.append('{:.2f}'.format(sc_list[sc_idx].fullpixel_ace_std[spec_idx]))
        for sc_idx in range(len(sc_list)):
            row_text.append('{:.2f}'.format(sc_list[sc_idx].subpixel_ace[spec_idx]))
            row_text.append('{:.2f}'.format(sc_list[sc_idx].fullpixel_ace[spec_idx]))
        data_list.append(tuple(row_text))
        
    # add the spectra as a list (ACE units)
    data_list_ACE_units = []
    for spec_idx in range(len(sc_list[0].names)):
        row_text = [sc_list[0].names[spec_idx]]
        for sc_idx in range(len(sc_list)):
            row_text.append('{:.2f}'.format(sc_list[sc_idx].subpixel_ace[spec_idx]))
            row_text.append('{:.2f}'.format(sc_list[sc_idx].fullpixel_ace[spec_idx]))
        data_list_ACE_units.append(tuple(row_text))
    
    return header_labels, data_list, data_list_ACE_units
    
def package_spectral_contrast_plot_data(sc_list, images, header_labels, inputs):
    # this function builds the structures needed for plots in the spectral contrast viewer 
    print('packaging spectral contrast plot data')
    
    # build the image data structure
    print('building image plot data')
    sc_image_plot_data = {}    
    for i in range(len(images)):
        image = images[i]
        image_mean = np.mean(np.mean(image.arr,axis=0),axis=0)
        image_wl = image.im.bands.centers
        key1 = header_labels[2*i+1]
        key2 = header_labels[2*i+2]
        print('computing endmembers with smacc')
        endmembers = SMACC_endmembers(image,15)
        sc_image_plot_data[key1] = {'wl':image_wl,'mean':image_mean,'endmembers':endmembers}
        sc_image_plot_data[key2] = {'wl':image_wl,'mean':image_mean,'endmembers':endmembers}
    
    print('building library plot data')
    # build the spectral library data structure
    sc_library_plot_data = sc_library_plot_data_struc()
    # Read the detection library
    file_name,extension = os.path.splitext(inputs.det_lib_fname)
    lib = envi.open(file_name+'.hdr')   
    sc_library_plot_data.wl = lib.bands.centers
    sc_library_plot_data.dict = {}    
    nSpectra = lib.spectra.shape[0]
    for i in range(nSpectra):
        sc_library_plot_data.dict[lib.names[i]] = lib.spectra[i,]
    
    print('building ace vs abundance plot data')
    # add the data for plots of the predicted ACE values
    ace_predicted_plot_data = sc_ace_predicted_plot_data_struc()
    ace_predicted_plot_data.abundances = inputs.abundances
    for sc in sc_list:
        for spec_idx in range(len(sc.names)):
            ace_predicted_plot_data.dict[sc.image_name,sc.names[spec_idx]] = sc.ace_predicted[spec_idx,] 
    
    return sc_image_plot_data, sc_library_plot_data, ace_predicted_plot_data

def bhattacharyya_distance(arr1, arr2, nPCs, inputs):
    
    # build the image array as a list
    [nrows,ncols,nbands] = np.shape(arr1)
    imlist = np.reshape(arr1,(nrows*ncols,nbands))
    # subtract mean from imlist
    mean1 = np.mean(imlist,axis=0)
    imlist_meansub = imlist-np.tile(mean1,[nrows*ncols,1])     
    # compute the (first stage) covariance
    cov1 = np.matmul(imlist_meansub.T,imlist_meansub)/(ncols*nrows)
    # compute eigen values and eigenvectors
    evals1,evecs1 = np.linalg.eig(cov1)    
    idx = evals1.argsort()[::-1]   
    evals1 = evals1[idx]
    evecs1 = evecs1[:,idx]
    # Compute the inverse of C2 using the desired number of PCs.
    D = (1./evals1)
    D[nPCs:] = 0
    D = np.diag(D)
    iC1 = np.matmul( np.matmul(evecs1,D), np.transpose(evecs1))
    
    # build the image array as a list
    [nrows,ncols,nbands] = np.shape(arr2)
    imlist = np.reshape(arr2,(nrows*ncols,nbands))
    # subtract mean from imlist
    mean2 = np.mean(imlist,axis=0)
    imlist_meansub = imlist-np.tile(mean2,[nrows*ncols,1])
    # compute the (first stage) covariance
    cov2 = np.matmul(imlist_meansub.T,imlist_meansub)/(ncols*nrows)
    # compute eigen values and eigenvectors
    evals2,evecs2 = np.linalg.eig(cov2)    
    idx = evals2.argsort()[::-1]   
    evals2 = evals2[idx]
    evecs2 = evecs2[:,idx]
    # Compute the inverse of C2 using the desired number of PCs.
    D = (1./evals2)
    D[nPCs:] = 0
    D = np.diag(D)
    iC2 = np.matmul( np.matmul(evecs2,D), np.transpose(evecs2))
    
    # compute the average covariance and related statistics
    C = (cov1+cov2)/2
    # compute eigenvalues and eigenvectors
    eigenValues, eigenVectors = np.linalg.eig(C)
    # sort by eigenValues (largest first)
    idx = eigenValues.argsort()[::-1]
    eigenValues = eigenValues[idx]
    eigenVectors = eigenVectors[:,idx]
    # Compute the inverse of C using the desired number of PCs.
    D = (1./eigenValues)
    D[nPCs:] = 0
    D = np.diag(D)
    iC = np.matmul( np.matmul(eigenVectors,D), np.transpose(eigenVectors))
    
    # compute the components of the Bhattacharyya distance
    mean_diff_part  = np.matmul( np.matmul(np.transpose(mean1-mean2), iC), (mean1-mean2))
    eval_diff_part = np.log( np.prod(eigenValues[:nPCs])/np.sqrt( np.prod(evals1[:nPCs]) * np.prod(evals2[:nPCs]) ) )
    bhat_distance =  0.125*mean_diff_part + 0.5*eval_diff_part
    MD_avg = (np.matmul( np.matmul(np.transpose(mean1-mean2), iC1), (mean1-mean2)) + np.matmul( np.matmul(np.transpose(mean1-mean2), iC2), (mean1-mean2)))/2.0
    return bhat_distance, mean_diff_part, eval_diff_part, MD_avg, mean1, evals1, mean2, evals2


def SMACC_endmembers(image,nEndmembers):
    nrows = image.im.nrows
    ncols = image.im.ncols
    nbands = image.im.nbands
    # get the endmembers
    endmembers = np.zeros([nEndmembers,nbands])
    endmember_count = 0
    im2d = np.reshape(image.arr,[nrows*ncols,nbands])
    im2d_proj = im2d[:]
    endmember_index = np.argmax(np.linalg.norm(im2d_proj,axis=1))
    endmembers[endmember_count,:] = im2d[endmember_index,:]
    endmember_count = endmember_count + 1
    for i in range(nEndmembers-1):
        ## project out previous endmember ##
        # normalize the latest endember
        e_proj = im2d_proj[endmember_index,:]
        e = e_proj/np.linalg.norm(e_proj)
        # (scalar) project the background spectra onto normalized latest endmember
        scalar_proj = np.matmul(im2d_proj,e) 
        # multiply to make this a vector projection
        vector_proj = np.matmul(np.reshape(scalar_proj,[len(scalar_proj),1]),np.reshape(e,[1,len(e)]))
        # subtract the vecotor projection from the background spectra
        im2d_proj = im2d_proj - vector_proj
        # find index for the projected spectrum with the largest norm
        endmember_index = np.argmax(np.linalg.norm(im2d_proj,axis=1))
        endmembers[endmember_count,:] = im2d[endmember_index,:]
        endmember_count = endmember_count+1
    return endmembers

def select_library(self,prompt="Choose a library"):
    if self.libraryDir is None:
        fname_library = QFileDialog.getOpenFileName(self, prompt)
    else:
        try:
            fname_library = QFileDialog.getOpenFileName(self, prompt, self.libraryDir)
        except:
            fname_library = QFileDialog.getOpenFileName(self, prompt)
    if fname_library == '':
        return None, ok

    #fname_library = fname_library[0]
    lib, ok = is_library_file(fname_library)
    print(ok)
    if ok:
        return lib, ok
    else:
        try:
            QMessageBox.warning(self,"File error",
                "File %s is not a valid spectral library."%(os.path.basename(fname_library)))
            return None, ok
        except:
            QMessageBox.warning(self,"File error",
                "File is not a valid spectral library.")
            return None, ok

def list_multiply(l,x):
    if type(l) is list:
        l = (np.asarray(l)*x).tolist()
    return l

def find_indices(string_search,string_list):
    # create a list of True and False for txt in string_list containing the search string
    string_check = [(string_search in txt) for txt in string_list]
    # get the indices of the Trues
    indices = list(compress(range(len(string_check)), string_check))
    return indices

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def read_roi_file(fname):
    # read tje file with pandas
    df = pd.read_csv(fname)

    # parse the ROI file for ROI metadata
    names = list(np.unique(df['Name'])) # empty list
    ROIs = {} # empty dictionary
    for name in names:
        ROIs[name] = ROI_struc()
        ROIs[name].name = name
        df_subset = df.loc[df['Name'] == name]
        ROIs[name].color = np.asarray(hex_to_rgb(df_subset.iloc[0,1]), dtype=float)
        ROIs[name].npts = df_subset.shape[0]
        ROIs[name].locs = df_subset.iloc[:, 2:4].to_numpy()
        ROIs[name].spectra = df_subset.iloc[:, 4:df_subset.shape[1]].to_numpy()
        ROIs[name].wl = np.asarray(df_subset.columns.values.tolist()[4:df_subset.shape[1]], dtype=float)

    return True, ROIs


def read_roi_asci_file(fname):

    # read the ROI ASCII file as text
    with open(fname) as f:
        content = f.readlines()
    # you may also want to remove whitespace characters like `\n` at the end of each line
    content = [x.strip() for x in content]

    # parse the ROI file for ROI metadata
    ROIs = {} # empty dictionary
    names = [] # empty list
    nROIs = int(content[1][17:])
    name_txt_indices = find_indices('; ROI name: ',content)
    color_txt_indices = find_indices('; ROI rgb value: ',content)
    npts_txt_indices = find_indices('; ROI npts: ',content)
    for name_idx, color_idx, npts_idx in zip(name_txt_indices, color_txt_indices, npts_txt_indices):
        # get the name for this ROI
        name = content[name_idx][12:len(content[name_idx])]
        names.append(name)
        # create the ROI structure
        ROIs[name] = ROI_struc()
        ROIs[name].name = name
        ROIs[name].npts = int(content[npts_idx][12:len(content[npts_idx])])
        ROIs[name].color = np.asarray([int(x) for x in content[color_idx][18:len(content[color_idx])-1].split(',')])

    # determine the first line after the header (this is the start of the data)
    start_index = 0
    for i in range(len(content)):
        if len(content[i]) > 0:
            if content[i][0] == ';':
                start_index = i+1
            else:
                break
        else:
            break


    # create a progress bar dialog
    progressDialog = QProgressDialog("Reading ROI data....", "Cancel", start_index, len(content))
    progressDialog.setWindowTitle('Progress')
    progressDialog.setModal(True)
    progressDialog.show()
    progress = start_index

    # read the spectra and pixel locations from the ROI file
    for name in names:
        # read the location and spectra information for this ROI
        for line in content[start_index:start_index+ROIs[name].npts]:
            data = [float(x) for x in line.split()]
            spectrum = np.asarray(data[3:len(data)])
            loc = np.asarray( data[1:3])
            if len(ROIs[name].locs) == 0:
                ROIs[name].locs = loc
                ROIs[name].spectra = spectrum
            else:
                ROIs[name].locs = np.vstack((ROIs[name].locs,loc))
                ROIs[name].spectra = np.vstack((ROIs[name].spectra,spectrum))
            # update the progress bar
            progress += 1
            progressDialog.setValue(progress)
            if progressDialog.wasCanceled():
                return False, None
        start_index = start_index + ROIs[name].npts+1
    return True, ROIs

def fuzzy_string_match(query, names):
    # this uses a fuzzy matching score
    # for strings that have a perfect match, they will get an slightly higher score so that
    # strings with the perfect match appearing earlier in the string being scored higher
    nRows = len(names)
    # use a fuzzy string match
    stringMatchScoresPR = [fuzz.partial_ratio(query, names[idx].lower()) for idx in range(nRows)]
    stringMatchScoresSTR = [fuzz.token_sort_ratio(query, names[idx].lower()) for idx in range(nRows)]
    # incriment the string match score by the position of an exact string match, if present
    stringLocation = [names[idx].lower().find(query) for idx in range(nRows)]
    locationScores = [(x > 0) * (max(stringLocation) + 2 - x) / (max(stringLocation) + 2) for x in stringLocation]
    # combine the different scores by summing
    matchScores = [x + y + z for x, y, z in zip(stringMatchScoresPR, stringMatchScoresSTR, locationScores)]
    return matchScores

def get_next_image_viewer_key(keys):
    next_key = 0
    while next_key in keys:
        next_key = next_key + 1
    return next_key

