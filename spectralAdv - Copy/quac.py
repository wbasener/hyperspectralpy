import sys
import os
import numpy as np
import scipy.ndimage
import matplotlib.pyplot as plt
from spectral import *
from . import plotDisplay
from . import atmosphericConversions as atm
import pathlib
import pickle
import copy
import statsmodels.api as sm

class data_struc:
    def __init__(self):
        self.make_plots = 0          ##
        self.num_endmembers = 0      ##
        self.im = 0                  ##
        self.bad_bands = 0           ##
        self.wl = 0                  ##
        self.indices_row_col = 0     ## contains row and column indices to locate original locations from tiles subsets
        self.rad = 0                 ## original radiance image with bad bands and edges remvoed, then offset subtracted - use for getting endmembers
        self.rad_for_offset = 0      # modified several times to prepare for computing the offset
        self.rad_original = 0        ## origonal radiance image with bad bands removed - use for final applicaiotn of gains and offsets
        self.rad_subset_wl_solar_normalized = 0 ## origonal radiance image with bad bands removed, then solar normalized and spectrally subset
        self.mean_full_wl = 0
        self.nrows = 0
        self.ncols = 0
        self.nbands = 0
        self.wl_peak_ref_val = 0
        self.offset = 0
        self.radiance_mean = 0
        self.subset_wl = 0
        self.nbands_subset_wl = 0
        self.subset_wl_indices = 0
        self.rad_list_subset_wl = 0
        self.endmembers = 0
        self.endmembers_solar_normalized = 0
        self.em_mean = 0
        self.em_mean_solar_normalized = 0
        self.ideal_mean = 0
        self.mean_ref = 0
        
        
def planck(wav, T):
    wav = wav/1000000.
    h = 6.626e-34
    c = 3.0e+8
    k = 1.38e-23
    a = 2.0*h*c**2
    b = h*c/(wav*k*T)
    intensity = a/ ( (wav**5) * (np.exp(b) - 1.0) )
    return intensity

def interpolate_nans(x):
    # removes / interpolates / extrapolates over a vector with a few nans and/or infs
    non_nan_indices = np.where(np.isfinite(x))[0]
    if len(np.where(np.isfinite(x)==False)[0]) > 0:
        for idx in np.where(np.isfinite(x)==False)[0]:
            if idx < np.min(non_nan_indices):
                x[idx] = x[np.min(non_nan_indices)]
            elif idx > np.max(non_nan_indices):
                x[idx] = x[np.max(non_nan_indices)]
            else:
                x[idx] = (x[np.max(non_nan_indices[np.where(non_nan_indices < idx)])]+
                          x[np.min(non_nan_indices[np.where(non_nan_indices > idx)])])/2
    return x

def load_image(fname_im, num_endmembers, make_plots):
    data = data_struc()
    data.num_endmembers = num_endmembers
    data.make_plots = make_plots
    # load the image and wavelengths
    im = envi.open(fname_im+'.hdr')
    data.rad = im.load() 
    nrows,ncols,nbands = np.shape(data.rad)
    wl = np.asarray(im.bands.centers)
    if np.mean(wl) > 100:
        wl = wl/1000.
        im.bands.centers = [ x/1000. for x in im.bands.centers] 
    data.im = im
    data.wl = wl
    data.make_plots = make_plots
    return data
    
def remove_bad_bands(data,bad_ranges):
    # remove bad bands if bad range is provided
    if len(bad_ranges)>0:
        data.bad_bands = np.zeros(len(data.wl))# create array of zeros
        for r in bad_ranges:
                data.bad_bands[(data.wl>r[0]) & (data.wl<r[1])]=1
        data.wl = data.wl[data.bad_bands==0]
        data.rad = data.rad[:,:,data.bad_bands==0]
    data.rad_original = data.rad[:]
    data.rad_for_offset = data.rad[:]
    return data
    
def find_peak_wavelength_index(data):
    # find the wavelength index for the (near peak) for approximate reflectance
    data.wl_peak_ref_val = np.argmin(abs(data.wl-1.))
    return data
    
def pre_offset_cleanup(data):
    fp = np.zeros([3,3,3])
    fp[1,0,1] = 1
    fp[1,1,1] = 1
    fp[1,2,1] = 1
    data.rad_for_offset = scipy.ndimage.filters.median_filter(data.rad, footprint=fp) # median filter cross track direction
    data.rad_for_offset = scipy.ndimage.filters.gaussian_filter(data.rad_for_offset, sigma=[1,1,0]) # smooth spatial (not spectral) directions
    return data 
    
def remove_edge_pixels(data):
    # remove edge pixels
    data.rad = data.rad[5:data.nrows-5,5:data.ncols-5,:]
    data.rad_for_offset = data.rad_for_offset[5:data.nrows-5,5:data.ncols-5,:]
    data.nrows, data.ncols, data.nbands = np.shape(data.rad)
    data.radiance_mean = np.mean(np.mean(data.rad,axis=0),axis=0)
    # create array to track row and column positons
    # created here because this the the first point where we have the final array size    
    data.indices_row_col = np.zeros([data.nrows,data.ncols,2],dtype=int)
    for r in range(data.nrows): data.indices_row_col[r,:,0] = r
    for c in range(data.ncols): data.indices_row_col[:,c,1] = c
    return data
    
def create_subset_indices(data,subset_wl_desired):
    # determine indices to subset at
    data.subset_indices = []
    for w in subset_wl_desired:
        data.subset_indices.append(np.argmin(abs(data.wl-w)))
    data.subset_wl = data.wl[data.subset_indices]
    data.nbands_subset_wl = len(data.subset_indices)
    return data
    
def compute_offsets(data):
    # compute the offsets 
    data.offset = np.min(np.min(data.rad_for_offset,axis=0),axis=0)
    return data       
    
def subtract_solar_black_body(data):
    # divide by the black body for the sun (approx)
    bb = planck(data.subset_wl, 4250)
    bb_tile = np.tile(bb**(-1.),[data.nrows,data.ncols,1])
    data_offset_tile = np.tile(data.offset[data.subset_indices],[data.nrows,data.ncols,1])
    data.rad_subset_wl_solar_normalized = (data.rad[:,:,data.subset_indices]-data_offset_tile)*bb_tile
    data.rad_subset_wl_solar_normalized = data.rad_subset_wl_solar_normalized*0.4/np.mean(data.rad_subset_wl_solar_normalized)
    data_offset_tile = np.tile(data.offset,[data.nrows,data.ncols,1])
    data.rad = data.rad-data_offset_tile
    data.solar_bb = planck(data.wl, 4250)
    bb_tile = np.tile(data.solar_bb**(-1.),[data.nrows,data.ncols,1])
    data.rad_full_wl_solar_normalized = data.rad*bb_tile
    return data
    
def compute_pseudo_reflectance(data):
    data.mean_full_wl = np.tile(np.mean(np.mean(data.rad_full_wl_solar_normalized,0),0),(data.nrows,data.ncols,1))
    data.rad_full_wl_solar_normalized = data.rad_full_wl_solar_normalized/data.mean_full_wl
    mean_subset_wl = np.tile(np.mean(np.mean(data.rad_subset_wl_solar_normalized,0),0),(data.nrows,data.ncols,1))
    data.rad_subset_wl_solar_normalized = data.rad_subset_wl_solar_normalized/mean_subset_wl
    return data       
    
def remove_veg(data):
    # compute NDVI
    idx_650nm = np.argmin(abs(data.wl-0.65))
    idx_850nm = np.argmin(abs(data.wl-0.85))
    band_650nm = data.rad_full_wl_solar_normalized[:,:,idx_650nm]
    band_850nm = data.rad_full_wl_solar_normalized[:,:,idx_850nm]
    NDVI = (band_850nm-band_650nm)/(band_850nm+band_650nm)
    NDVI[np.isnan(NDVI)] = 0
    NDVI_mask = NDVI<0.1 # mask is True (=1) where there is not veg, is False (=0) for veg
    veg_idx = np.where(NDVI_mask == 0)
    veg_spectra = data.rad_full_wl_solar_normalized[veg_idx[0], veg_idx[1], :]
    data.mean_solar_nomralized_veg = np.mean(veg_spectra,axis=0)
    for idx in range(data.nbands_subset_wl):
        data.rad_subset_wl_solar_normalized[:,:,idx] = data.rad_subset_wl_solar_normalized[:,:,idx]*NDVI_mask
    # compute NDMI1
    idx_795nm = np.argmin(abs(data.wl-0.795))
    idx_990nm = np.argmin(abs(data.wl-0.99))
    band_795nm = data.rad_full_wl_solar_normalized[:,:,idx_795nm]
    band_990nm = data.rad_full_wl_solar_normalized[:,:,idx_990nm]
    # compute numerator and denominator seperately to remove 0 from denominator
    NDMI_numerator = (band_795nm-band_990nm)
    NDMI_denominator = (band_795nm+band_990nm) + 0.0001*np.max(NDMI_numerator)
    NDMI = NDMI_numerator/NDMI_denominator
    NDMI_mask = NDMI<0.3 # mask is True (=1) where there is not mud, is False (=0) for mud
    for idx in range(data.nbands_subset_wl):
        data.rad_subset_wl_solar_normalized[:,:,idx] = data.rad_subset_wl_solar_normalized[:,:,idx]*NDMI_mask
    return data
    
   
def SMACC_endmembers_tiled(data):
    tile_rows = 12
    tile_cols = 5
    num_tiles = tile_rows*tile_cols
    tile_width = int(np.floor(data.ncols/tile_cols))
    tile_height = int(np.floor(data.nrows/tile_rows))
    # get the endmembers
    data.endmembers = np.zeros([data.num_endmembers*num_tiles,data.nbands])
    if data.make_plots:
        data.endmembers_solar_normalized = np.zeros([data.num_endmembers*num_tiles,data.nbands])
    endmember_count = 0
    for tile_row in range(tile_rows):
        for tile_column in range(tile_cols):
            row_start = int(tile_row*tile_height)
            row_end = int(row_start+tile_height)
            column_start = int(tile_column*tile_width)
            column_end = int(column_start+tile_width)
            # subset rad_subset_wl_solar_normalized
            tile_rad_subset_wl_solar_normalized = np.reshape(data.rad_subset_wl_solar_normalized[row_start:row_end,column_start:column_end,:],[tile_height*tile_width,data.nbands_subset_wl])
            ref = tile_rad_subset_wl_solar_normalized
            # subset indices_row_col
            tile_indices_row_col = np.reshape(data.indices_row_col[row_start:row_end,column_start:column_end,:],[tile_height*tile_width,2])            
            endmember_index = np.argmax(np.linalg.norm(tile_rad_subset_wl_solar_normalized,axis=1))
            em_row = tile_indices_row_col[endmember_index,0]
            em_col = tile_indices_row_col[endmember_index,1]
            data.endmembers[endmember_count,:] = data.rad[em_row,em_col,:]
            if data.make_plots:
                data.endmembers_solar_normalized[endmember_count,:] = data.rad_full_wl_solar_normalized[em_row,em_col,:]
            endmember_count = endmember_count+1
            for i in range(1,data.num_endmembers):
                ## project out previous endmember ##
                # normalize the latest endember
                e_proj = ref[endmember_index,:]
                e = e_proj/np.linalg.norm(e_proj)
                # (scalar) project the background spectra onto normalized latest endmember
                scalar_proj = np.matmul(ref,e) 
                # multiply to make this a vector projection
                vector_proj = np.matmul(np.reshape(scalar_proj,[len(scalar_proj),1]),np.reshape(e,[1,len(e)]))
                # subtract the vecotor projection from the background spectra
                ref = ref - vector_proj
                # find index for the projected spectrum with the largest norm
                endmember_index = np.argmax(np.linalg.norm(ref,axis=1))
                em_row = tile_indices_row_col[endmember_index,0]
                em_col = tile_indices_row_col[endmember_index,1]
                data.endmembers[endmember_count,:] = data.rad[em_row,em_col,:]
                if data.make_plots:
                    data.endmembers_solar_normalized[endmember_count,:] = data.rad_full_wl_solar_normalized[em_row,em_col,:]
                endmember_count = endmember_count+1
                
    data = NDVI_filter(data)
    i,data.endmembers,c = cull_library(data.endmembers,0.95,50,60)
    data.em_mean = np.mean(data.endmembers,axis=0)    
    if data.make_plots:
        data.em_mean_solar_normalized = np.mean(data.endmembers_solar_normalized,axis=0)
    return data
    
    
def load_ideal_endmember_library(data,fname_em):
    # Open and resample endmember library
    lib = envi.open(fname_em+'.hdr')    
    # convert library to image wavelength units
    if np.mean(data.wl) < 100:
        # image units are micrometers
        if np.mean(lib.bands.centers) < 100:
            wl_scale = 1.
        else:
            wl_scale = 1/1000.
            if verbose==1:
                print('Converting library from nanometers to microns.')
    else:
        # image units are nanometers
        if np.mean(lib.bands.centers) < 100:
            wl_scale = 1000.
            if verbose==1:
                print('Converting library from microns to nanometers.')
        else:
            wl_scale = 1
    lib.bands.centers = wl_scale*np.array(lib.bands.centers)
    
    # resample library to origonal image bands
    resample = resampling.BandResampler(lib.bands, data.im.bands)
    lib.spectra = np.matmul(lib.spectra,resample.matrix.T)
    lib.bands.centers = data.im.bands.centers
    i,culled_spectra,c = cull_library(lib.spectra,0.95,50,60)
    data.ideal_mean = np.mean(culled_spectra,axis=0)
    data.ideal_mean = data.ideal_mean[data.bad_bands==0]
    return data
    
def compute_gain(data):
    # compute gain
    data.gain = data.ideal_mean/data.em_mean 
    # modifying gains below 650nm to be nearly constant
    band_650nm_idx = np.argmin(abs(data.wl-0.65))
    for idx in range(data.nbands):
        if idx < band_650nm_idx:
            data.gain[idx] = np.sqrt(data.gain[idx]*data.gain[band_650nm_idx])
    return data
    
    
def correct_and_save_image(data,fname_imout):
    # final correction
    nrows,ncols,nbands = np.shape(data.rad_original)
    offset_tile = np.tile(data.offset,[nrows,ncols,1])
    gain_tile = np.tile(data.gain,[nrows,ncols,1])
    data.ref = (data.rad_original-offset_tile)*gain_tile
    data.mean_ref = np.mean(data.ref)
    data.ref = data.ref*0.4/data.mean_ref
    envi.save_image(fname_imout+'.hdr',data.ref.astype('float32'),
        metadata={'wavelength': list(map(str,data.wl))},
        ext='',
        force=True)        
    #envi.save_image(fname_imout+'_subsetwl.hdr',data.rad_subset_wl_solar_normalized,
    #    metadata={'wavelength': map(str,data.subset_wl)},
    #    force=True)
    return data
    
    
def plot_quac_components(data):
    if data.make_plots:
        
        # create a plotDisplay window to hold the plots
        pltWindow1 = plotDisplay.pltDisplay(title="QUAC Components 1", width=2400, height=1200, settings=None)
        pltWindow2 = plotDisplay.pltDisplay(title="QUAC Components 2", width=2400, height=1200, settings=None)

        # setup plots
        wl = data.wl # we will use wl as the x-axis in most plots, so this will simply code
        # axis for plot window 1
        ax_offset = pltWindow1.figure.add_subplot(2, 3, 1)
        ax_chunk_endmembers = pltWindow1.figure.add_subplot(2, 3, 2)
        ax_baseline_subtracted_endmembers = pltWindow1.figure.add_subplot(2, 3, 3)
        ax_solar_normalized_veg = pltWindow1.figure.add_subplot(2, 3, 4)
        ax_corr_endmembers = pltWindow1.figure.add_subplot(2, 3, 5)
        ax_gain = pltWindow1.figure.add_subplot(2, 3, 6)
        # axis for plot window 2
        ax_mean_radiance = pltWindow2.figure.add_subplot(2, 3, 1)
        ax_solar_blackbody = pltWindow2.figure.add_subplot(2, 3, 2)
        ax_solar_normalized = pltWindow2.figure.add_subplot(2, 3, 3)
        ax_ideal_endmember_mean = pltWindow2.figure.add_subplot(2, 3, 4)
        ax_image_endmember_mean = pltWindow2.figure.add_subplot(2, 3, 5)
        #ax_empty = pltWindow2.figure.add_subplot(2, 3, 6)

        
        # plot mean radiance
        ax_mean_radiance.plot(wl,data.radiance_mean)
        ax_mean_radiance.set_xlabel('wavelength (microns)')
        ax_mean_radiance.set_ylabel('Radiance')
        ax_mean_radiance.set_title('Mean Radiance of Prepared Image')
        
        # plot the offset
        ax_offset.plot(wl,data.offset)
        ax_offset.set_xlabel('wavelength (microns)')
        ax_offset.set_ylabel('Offset')
        ax_offset.set_title('Offset')
            
        # plot the solar black body
        ax_solar_blackbody.plot(wl,data.solar_bb,)
        ax_solar_blackbody.set_xlabel('wavelength (microns)')
        ax_solar_blackbody.set_ylabel('Intensity')
        ax_solar_blackbody.set_title('Solar Black Body')
        
        # plot the solar normalized mean
        ax_solar_normalized.plot(wl,np.mean(np.mean(data.rad_full_wl_solar_normalized,axis=0),axis=0))
        ax_solar_normalized.set_ylim([0,1.1*np.mean(data.rad_full_wl_solar_normalized)])
        ax_solar_normalized.set_xlabel('wavelength (microns)')
        ax_solar_normalized.set_title('Mean of initial solar-normalized image')
        
        # plot the mean solar normalized endmember
        ax_image_endmember_mean.plot(wl,data.em_mean_solar_normalized)
        ax_image_endmember_mean.set_xlabel('wavelength (microns)')
        ax_image_endmember_mean.set_ylabel('Solar Normalized Endmember')
        ax_image_endmember_mean.set_title('Solar Normalized Chunk Endmembers')
        
        # plot the endmembers ax_corr_endmembers
        ne, nb, = np.shape(data.endmembers_solar_normalized)
        for idx in range(ne):
            ax_chunk_endmembers.plot(wl,np.reshape(data.endmembers_solar_normalized[idx,:],np.shape(wl)))
            ax_baseline_subtracted_endmembers.plot(wl,np.reshape(data.endmembers_solar_normalized[idx,:],np.shape(wl)))
        ax_chunk_endmembers.set_xlabel('wavelength (microns)')
        ax_chunk_endmembers.set_ylabel('Solar Normalized Endmember')
        ax_chunk_endmembers.set_title('Solar Normalized Chunk Endmembers')
        ax_baseline_subtracted_endmembers.set_xlabel('wavelength (microns)')
        ax_baseline_subtracted_endmembers.set_ylabel('Solar Normalized Endmember')
        ax_baseline_subtracted_endmembers.set_title('Baseline Subtracted Solar Normalized Endmmebers')

        # plot the average solar notmalized vegetation

        ax_solar_normalized_veg.plot(wl,data.mean_solar_nomralized_veg)
        ax_solar_normalized_veg.set_xlabel('wavelength (microns)')
        ax_solar_normalized_veg.set_ylabel('Solar Normalized Radiance')
        ax_solar_normalized_veg.set_title('Avg Strong Solar Nomalized Vegetation')


        # plot the ideal mean
        ax_ideal_endmember_mean.plot(wl,data.ideal_mean)
        ax_ideal_endmember_mean.set_xlabel('wavelength (microns)')
        ax_ideal_endmember_mean.set_ylabel('Reflactance')
        ax_ideal_endmember_mean.set_title('Ideal Endmember Mean')
        
        # plot the gain
        ax_gain.plot(wl,data.gain)
        ax_gain.set_xlabel('wavelength (microns)')
        ax_gain.set_ylabel('Gain')
        ax_gain.set_title('Gain')
        
        # plot the corrected endmembers 
        ne, nb, = np.shape(data.endmembers)
        em_mean = np.zeros(nb)
        for idx in range(ne):
            em_mean = em_mean + ((np.reshape(data.endmembers[idx,:],np.shape(wl)))*data.gain)/ne
            ax_corr_endmembers.plot(wl,(np.reshape(data.endmembers[idx,:],np.shape(wl)))*data.gain)
        ax_corr_endmembers.set_xlabel('wavelength (microns)')
        ax_corr_endmembers.set_ylabel('Solar Normalized Endmember')
        ax_corr_endmembers.set_title('Atmosphericly Corrected Endmembers')
        ax_ideal_endmember_mean.plot(wl,em_mean,'r.')

        pltWindow1.canvas.draw()
        fname = pathlib.Path(current_dir, "QUAC_plots_1.png")
        pltWindow1.savefig(fname)

        pltWindow2.canvas.draw()
        fname = pathlib.Path(current_dir, "QUAC_plots_2.png")
        pltWindow2.savefig(fname)
    
    
def cull_library(spec,corr_threshold,min_num,max_num):
    # This function will select a subset of the library with 
    # the final number of spectra between min_num and max_num, 
    # and not including spectra with correlation less than
    # corr_threshold except when needed to satisfy the
    # minimum number of spectra.
    
    # the maximum spectra cannot be more than the number spectra in the library
    nspec,nbands = np.shape(spec)
    max_num = min([max_num,nspec]) 
    # corr_threshold has to be between -1 and 1
    corr_threshold = min([corr_threshold,1.])
    corr_threshold = max([corr_threshold,-1.])
    # min_num has to be at least 0
    min_num = max([min_num,0])
    
    corr = np.corrcoef(spec) # matrix of all pairwise correlations
    # First spectra to choose: spectra most similar to the others, on average
    # This is a good first representativs for the library
    indices = [np.argmin(abs(np.mean(corr,axis=0)))]
    next_corr_to_subset = -1
    continue_check = True
    while continue_check:
        max_corr_in_subset = next_corr_to_subset
        corr_to_subset = corr[indices,:]
        max_corr_to_subset = np.max(corr_to_subset,axis=0)
        next_index = np.argmin(max_corr_to_subset)
        next_corr_to_subset = max_corr_to_subset[next_index]
        indices.append(next_index)
        # stop if adding more spectra will exceed the maximum number:
        if 1+len(indices) > max_num:
            continue_check = False
            max_corr_in_subset = next_corr_to_subset
        # stop and remove the latest spectrum if we have enough spectra 
        # and the new spectrum is too correlated to the subset
        if (len(indices) > min_num) and (next_corr_to_subset > corr_threshold):
            indices.pop()
            continue_check = False
    return indices, spec[indices,:], max_corr_in_subset
    
def NDVI_filter(data):
    # remove up to half of endmembers with high NDVI
    endmembers_for_NDVI = data.endmembers+np.min(data.endmembers)
    idx_650nm = np.argmin(abs(data.wl-0.65))
    idx_850nm = np.argmin(abs(data.wl-0.85))
    band_650nm = endmembers_for_NDVI[:,idx_650nm]/data.mean_full_wl[1,1,idx_650nm]
    band_850nm = endmembers_for_NDVI[:,idx_850nm]/data.mean_full_wl[1,1,idx_850nm]
    NDVI = (band_850nm-band_650nm)/(band_850nm+band_650nm)
    # determine NDVI threshold
    NDVI_thresh = max([np.median(NDVI),0.05])
    data.endmembers = data.endmembers[NDVI<NDVI_thresh,:]
    if data.make_plots:
        data.endmembers_solar_normalized = data.endmembers_solar_normalized[NDVI<NDVI_thresh,:]
    return data


def compute_poly_coeff(data):
    # get the path and file name for the ideal wl and mean
    current_dir = pathlib.Path(__file__).parent.resolve()
    wl_fname = pathlib.Path(current_dir, "wl_ref.npy")
    m_fname = pathlib.Path(current_dir, "m_ref.npy")
    wl_ref = np.load(wl_fname)
    m_ref = np.load(m_fname)
    wl_full = copy.deepcopy(wl_ref)
    m_full = copy.deepcopy(m_ref)
    # resample the ideal mean and fill in any NaNs
    resample = resampling.BandResampler(wl_ref, data.wl)
    m_ref = np.matmul(m_ref, resample.matrix.T)
    m_ref = interpolate_nans(m_ref)

    # get the atmospheric coefficients
    pkl_file = open(pathlib.Path(current_dir, 'atm_gas_dict.pkl'), 'rb')
    atm_dict = pickle.load(pkl_file)
    # read the atmospheric coefficients (for 2nd order polynonmial per MODTRAN runs varying parameters)
    ok, atm_coeff = atm.read_atmospheric_coefficients()
    # reampls the atmospheric gases dictionary
    atm_dict_resampled = atm.resample_atm_dict(atm_dict, data.wl)
    atm_dict_full = atm.resample_atm_dict(atm_dict, wl_full)
    # create an atmospheric dictionary selection that has all gases, but exponents of zero (transmittance = 1 across all bands)
    atm_dict_selection = dict()
    atm_dict_selection['checked names'] = []#atm_dict_resampled.keys() # Not
    atm_dict_selection['density modifiers'] = np.zeros(len(atm_dict_selection['checked names']))

    m = m_ref
    wl = data.wl
    spec_radiance = data.em_mean # mean of the endmembers
    spec_atm_comp = np.zeros(data.nbands) # enemember mean converted to reflectance
    conversion_type = 'rad_to_ref'
    likelihood_max = 0
    likelihood_sum = 0
    likelihoods = []
    spectra = []
    max_idx = np.argmin(np.abs(wl - 2.5))
    min_idx = np.argmin(np.abs(wl - 0.45))

    for solar_zenith_angle in range(5, 85, 5):  # 5, 10, ..., 80, 85
        print(solar_zenith_angle)
        for atmospheric_index in range(6):  # 0,1,2,3,4,5
            for aerosol_index in range(12):  # 0, 1, 2, ..., 10, 11
                    #for water_coeff in range(-200,200,10):
                    # Apply to the spectrum to convert to reflectance
                    #atm_dict_selection['density modifiers'][0] = water_coeff
                    ###########################################################
                    ##### SOMEWHERE IN HERE I GET:
                    ##### spectral:INFO: No overlap for target band 29 (0.655792 / -0.000981)
                    ###########################################################
                    ok, spec = atm.convert_spectrum(spec_radiance, wl, atm_coeff, conversion_type, solar_zenith_angle,
                                                    atmospheric_index, aerosol_index, atm_dict_resampled, atm_dict_selection)
                    spec = interpolate_nans(spec)
                    if ok and (np.isnan(np.sum(spec))==False):
                        result = sm.OLS(m[min_idx:max_idx], spec[min_idx:max_idx]).fit()
                        likelihood = np.exp(-result.bic / 2)
                        if np.isfinite(result.bic):
                            if (likelihood > likelihood_max / 20):
                                spec = result.predict(spec)
                                print([likelihood, solar_zenith_angle, atmospheric_index, aerosol_index])
                                likelihoods.append(likelihood)
                                spectra.append(spec * np.mean(m[min_idx:max_idx]) / np.mean(spec[min_idx:max_idx]))
                                likelihood_max = likelihood
                                spec_atm_comp = spec_atm_comp + spec * likelihood * np.mean(m[min_idx:max_idx]) / np.mean(
                                    spec[min_idx:max_idx])
                    else:
                        print('not ok')

    nLik = len(likelihoods)
    for i in range(nLik):
        for j in range(i,nLik):
            result = sm.OLS(m[min_idx:max_idx], np.vstack((spectra[i][min_idx:max_idx],spectra[j][min_idx:max_idx])).T ).fit()
            spec = result.predict(np.vstack((spectra[i],spectra[j])).T)
            spectra.append(spec * np.mean(m[min_idx:max_idx]) / np.mean(spec[min_idx:max_idx]))
            likelihood = np.exp(-result.bic / 2)
            print(likelihood)
            likelihoods.append(likelihood)
            spec_atm_comp = spec_atm_comp + spec * likelihood * np.mean(m[min_idx:max_idx]) / np.mean(
                spec[min_idx:max_idx])

    spec_atm_comp = spec_atm_comp / np.sum(likelihoods)
    likelihoods

    plt.figure(figsize=(20,20))
    # check the data with a plot
    plt.plot(wl, spec_atm_comp, c='b');
    plt.plot(wl, m, c='k');
    plt.ylim([0, 1])
    fname = pathlib.Path(current_dir, "test_results_bma_single_2element_.png")
    plt.savefig(fname)

    plt.figure(figsize=(20,20))
    # Examine the Model Averaging Results
    for s in spectra:
        plt.plot(wl,s, c='b', alpha=0.5)
    plt.plot(wl,m,c='k', linewidth=4, label='Ideal Reflectance')
    plt.plot(wl,spec_atm_comp,'--m', linewidth=4, label='Atm Comp Reflectance')
    plt.legend()
    plt.ylim(0,1);
    fname = pathlib.Path(current_dir,"test_results_bma_all_2element_.png")
    plt.savefig(fname)



    return data