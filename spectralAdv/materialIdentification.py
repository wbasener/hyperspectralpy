from spectral import *
from spectralAdv import specTools
import scipy
import numpy as np
import copy


def single_material_identificaiton(self):
    verbose = False


    ########################################################################
    # Prepare the data
    self.statusBar.showMessage('Preparing data scores...')
    self.progressBar.setValue(0)

    # get the pixel spectrum
    pixel = self.MPWidget_pixel.getFigure().gca().lines[0].get_ydata()

    # resample the selected libraries
    resampled_libraries = []
    selected_libraries_indices = sorted(set(index.row() for index in self.table_view.selectedIndexes()))
    for rowIdx in selected_libraries_indices:
        library_file_name = self.table_view.item(rowIdx, 8).text()
        lib = copy.deepcopy(self.spectral_libraries[library_file_name])
        lib.bands.centers = [wl * float(self.table_view.item(rowIdx, 0).text()) for wl in lib.bands.centers] # apply scale to wl
        lib.spectra =  lib.spectra * float(self.table_view.item(rowIdx, 1).text()) # apply scale to y-values
        resampled_libraries.append(specTools.resample_library(lib, self.im, self.im_arr, verbose, rescale_x=False, rescale_y=False))

    # Merge the libraries
    # - code for implementing scale factor, currently not used as scale is handled in "specTools.resample_library"
    # scale_factor = float(self.table_view.item(0, 0).text())
    # lib_spectra = scale_factor*resampled_libraries[0].spectra
    lib_spectra = resampled_libraries[0].spectra
    spectra_names = resampled_libraries[0].names
    file_names = [resampled_libraries[0].params.filename]*len(spectra_names)
    num_libs = len(resampled_libraries)
    for idx in range(1,num_libs):
        # - code for implementing scale factor, currently not used as scale is handled in "specTools.resample_library"
        #scale_factor = float(self.table_view.item(idx, 0).text())
        # lib_spectra =  np.vstack((lib_spectra,scale_factor*resampled_libraries[idx].spectra))
        lib_spectra =  np.vstack((lib_spectra,resampled_libraries[idx].spectra))
        spectra_names = spectra_names + resampled_libraries[idx].names
        file_names = file_names + [resampled_libraries[idx].params.filename]*len(spectra_names)
    nSpectra = len(spectra_names)
    nBands = len(pixel)

    # Collect Endmembers
    endmembers = self.endmembers
    # add manual endmembers if spectra are present
    if len(self.MPWidget_endmember.getFigure().gca().lines) > 0:
        for line in self.MPWidget_endmember.getFigure().gca().lines:
            endmembers = np.vstack((endmembers, line.get_ydata()))
    nEndmembers = np.shape(endmembers)[0]

    # create the spectra with wl subsets
    # create copies of the full spectra
    lib_spectra_full_wl = lib_spectra
    pixel_full_wl = pixel
    endmembers_full_wl = endmembers
    nBands_full_wl = nBands
    # create a bad bands list (0 = not selected wl, 1 = selected wl)
    if len(self.band_region_wl_ranges) > 0:
        bad_bands_list = np.zeros(nBands)
        for wl_range in self.band_region_wl_ranges:
            for idx in range(nBands):
                if wl_range[0] < self.wl[idx] < wl_range[1]:
                    bad_bands_list[idx] = 1
        # resample to the selected wavelengths
        lib_spectra = lib_spectra_full_wl[:,(bad_bands_list== 1)]
        pixel = pixel_full_wl[(bad_bands_list== 1)]
        endmembers = endmembers[:,(bad_bands_list== 1)]
        nBands = int(np.sum(bad_bands_list))
        ### Recompute stats
        im_arr_gbands = self.im_arr[:,:,(bad_bands_list== 1)]
        pc_gbands = specTools.compute_screened_pca(im_arr_gbands,False)
        Whitening_gbands = specTools.compute_whitening(pc_gbands,False)
        W = Whitening_gbands.W
        m = Whitening_gbands.m
    else:
        W = self.W.W
        m = self.W.m


    ########################################################################
    #### COMPUTE ACE ####
    self.statusBar.showMessage('Computing ACE scores...')
    self.progressBar.setValue(5)

    # whiten the library
    # subtract the mean
#    W_lib_spectra = lib_spectra-np.tile(m,[nSpectra,1])
    # multiply by whitening matrix
#    W_lib_spectra = np.matmul(W,W_lib_spectra.T).T

    W_lib_spectra = np.zeros(np.shape(lib_spectra))
    counter = 0
    for s in lib_spectra:
        W_lib_spectra[counter,:] = np.matmul(W,s-m)
        counter = counter+1

    # Whiten the pixel
    # subtract the mean
    W_pixel = pixel - m
    # multiply by whitening matrix
    W_pixel = np.matmul(W,W_pixel.T).T

    # compute the ACE scores
    # compute the norms in the denomenator of ACE
    inv_lib_norms = 1/np.linalg.norm(W_lib_spectra,axis=1)
    inv_pix_norm = 1/np.linalg.norm(W_pixel)
    # compute the numerator (pixel spectrum dot product target spectrum)
    XdotT = np.matmul(W_pixel,np.transpose(W_lib_spectra))
    denominator_ACE = np.multiply(inv_lib_norms,inv_pix_norm)
    # take the ratio, and build into image shape
    ACE = np.multiply(XdotT, denominator_ACE)



    ########################################################################
    #### COMPUTE MF (Abundance) ####
    self.statusBar.showMessage('Computing MF scores...')
    self.progressBar.setValue(10)
    denominator_MF = np.multiply(inv_lib_norms,inv_lib_norms)
    MF = np.multiply(XdotT, denominator_MF)



    ########################################################################
    #### COMPUTE Correlation ####
    self.statusBar.showMessage('Computing Correlation values...')
    self.progressBar.setValue(15)
    # normalize the pixel (subtact mean, then divide by standard deviation)
    pixel_normalized = (pixel - np.mean(pixel))/np.std(pixel)

    # normalize the library (subtact mean, then divide by standard deviation)
    lib_spectra_means = np.tile(np.mean(lib_spectra, axis=1).T, [nBands, 1]).T
    lib_spectra_stds = np.tile(np.std(lib_spectra, axis=1).T, [nBands, 1]).T
    lib_spectra_normalized = (lib_spectra-lib_spectra_means)/lib_spectra_stds

    # compute correlation
    Corr = np.matmul(pixel_normalized, lib_spectra_normalized.T)/nBands



    ########################################################################
    #### compute probabilities from single element model averaging ####
    self.statusBar.showMessage('Computing probabilities...')
    self.progressBar.setValue(20)
    df = 12
    # compute coefficients with MF
    #coefficients = np.tile(MF,[nBands,1]).T
    #models = coefficients*W_lib_spectra
    # compute coefficients with linear regression
    coefficients = np.zeros(nSpectra)
    models = np.zeros((nSpectra,nBands))
    for idx in range(nSpectra):
        # linear regression: https://en.wikipedia.org/wiki/Simple_linear_regression
        x = W_lib_spectra[idx,:]
        b = np.dot(x - np.mean(x), W_pixel - np.mean(W_pixel)) / np.sum((x - np.mean(x)) ** 2)
        a = np.mean(W_pixel) - b * np.mean(x)
        models[idx, :] = a + b * x
        #MF[idx] = b
    pixel_tiled = np.tile(W_pixel, [nSpectra, 1])
    MSE = (1 / nBands) * np.sum((pixel_tiled - models)**2, axis=1)
    likelihoods = MSE**(-df/2) # could add "*df**(-1/2)" but this will cancel out since we are only using 1-element models
    probability = likelihoods/np.sum(likelihoods)



    ########################################################################
    #### Compute background removal and correlation
    self.statusBar.showMessage('Computing background removal and spectral fit scores...')
    self.progressBar.setValue(25)
    df = 5.

    # remove endmembers with ACE > 0.02
    ACE_thresh = 0.02
    # whiten the library
    # subtract the endmembers
    W_endmembers = endmembers-np.tile(m,[nEndmembers,1])
    # multiply by whitening matrix
    W_endmembers = np.matmul(W,W_endmembers.T).T

    # compute the ACE scores
    # compute the norms in the denomenator of ACE
    inv_lib_norms = 1/np.linalg.norm(W_endmembers,axis=1)
    # compute the numerator (pixel spectrum dot product target spectrum)
    XdotT = np.matmul(W_pixel,np.transpose(W_endmembers))
    denominator_ACE = np.multiply(inv_lib_norms,inv_pix_norm)
    # take the ratio, and build into image shape
    ACE_endmembers = np.multiply(XdotT, denominator_ACE)

    # remove endmembers with ACE < ACE_thresh (but keep at least 5)
    if np.sum((ACE_endmembers < ACE_thresh)) > 5:
        endmembers = endmembers[(ACE_endmembers < ACE_thresh)]
        endmembers_full_wl = endmembers_full_wl[(ACE_endmembers < ACE_thresh)]
        nEndmembers = np.shape(endmembers)[0]
    else:
        endmembers = endmembers[(ACE_endmembers < np.sort(ACE_endmembers)[5])]
        endmembers_full_wl = endmembers_full_wl[(ACE_endmembers < np.sort(ACE_endmembers)[5])]
        nEndmembers = np.shape(endmembers)[0]

    # iterate through lib_spectra
    background_removed_spectra_plot = None
    for idx in range(nSpectra):
        endemembers_this_lib = endmembers
        endemembers_this_lib_full_wl = endmembers_full_wl
        self.progressBar.setValue(30 + 70*idx/nSpectra)
        lib_spectrum = lib_spectra[idx,]
        lib_spectrum_full_wl = lib_spectra_full_wl[idx,] # full wl for plots
        likelihood_sum = 0
        background_removed_spectrum_avg = np.zeros(nBands)
        # full wl for the plots
        background_removed_spectrum_avg_full_wl = np.zeros(nBands_full_wl)
        while len(endemembers_this_lib[:,0]) > 1:
            unmix_spectra = np.vstack((endemembers_this_lib, lib_spectrum)).T
            nnls_result = scipy.optimize.nnls(unmix_spectra, pixel)
            coeff = nnls_result[0]
            em_coeff = coeff[0:-1]
            background = np.matmul(endemembers_this_lib.T,em_coeff)
            background_full_wl = np.matmul(endemembers_this_lib_full_wl.T,em_coeff)
            background_removed_spectrum = pixel - background
            background_removed_spectrum_full_wl = pixel_full_wl - background_full_wl # full wl for plots

            # compute the likelihood for this br spectrum
            # linear regression: https://en.wikipedia.org/wiki/Simple_linear_regression
            x = background_removed_spectrum
            y = pixel
            b = np.dot(x-np.mean(x),y - np.mean(y)) / np.sum((x-np.mean(x))**2)
            a = np.mean(y) - b*np.mean(x)
            model = a + b*background_removed_spectrum
            # compute the mean squared error and likelihood
            MSE = (1 / nBands) * np.sum((lib_spectrum - model) ** 2)
            likelihood = MSE**(-df/2)

            # add this background removed spectrum to the avg
            background_removed_spectrum_avg = background_removed_spectrum_avg + likelihood*background_removed_spectrum
            background_removed_spectrum_avg_full_wl = background_removed_spectrum_avg_full_wl + likelihood*background_removed_spectrum_full_wl # full wl for plots
            likelihood_sum = likelihood_sum + likelihood
            endemembers_this_lib = endemembers_this_lib[em_coeff > np.min(em_coeff)]
            endemembers_this_lib_full_wl = endemembers_this_lib_full_wl[em_coeff > np.min(em_coeff)]

        # compute the averaged br spectrum
        background_removed_spectrum_avg = background_removed_spectrum_avg/likelihood_sum
        background_removed_spectrum_avg_full_wl = background_removed_spectrum_avg_full_wl/likelihood_sum # full wl for plots

        background_removed_spectrum_normalized = (background_removed_spectrum_avg - np.mean(background_removed_spectrum_avg)) / np.std(background_removed_spectrum_avg)
        lib_spectrum_normalized = (lib_spectrum - np.mean(lib_spectrum)) / np.std(lib_spectrum)
        spectral_fit_this_lib = np.asarray(np.matmul(lib_spectrum_normalized, background_removed_spectrum_normalized.T) / nBands)
        # normalize background_removed_spectrumto match library spectrum for plots
        background_removed_spectrum_normalized_full_wl = (background_removed_spectrum_avg_full_wl - np.mean(background_removed_spectrum_avg)) / np.std(background_removed_spectrum_avg)
        background_removed_spectrum_plot = background_removed_spectrum_normalized_full_wl*np.std(lib_spectrum) + np.mean(lib_spectrum)

        # add result for current library spectrum to variables
        if background_removed_spectra_plot is None:
            background_removed_spectra_plot = np.asarray(background_removed_spectrum_plot)
            spectral_fit = np.asarray(spectral_fit_this_lib)
        else:
            background_removed_spectra_plot = np.vstack((background_removed_spectra_plot,background_removed_spectrum_plot))
            spectral_fit = np.append(spectral_fit,spectral_fit_this_lib)



    self.progressBar.setValue(100)
    self.statusBar.clearMessage()
    self.progressBar.setValue(0)


    result = {'spectra names':spectra_names, 'file names':file_names, 'ACE':ACE, 'MF': MF, 'Corr':Corr,
              'lib spectra':lib_spectra_full_wl, 'probability':probability, 'spectral fit':spectral_fit,
              'spectral fit':spectral_fit, 'background removed spectra plot':background_removed_spectra_plot}
    return result

def get_wl_scale_factor(lib_wl,pixel_wl):
    
    # onlye rescale if there is no overlap - ie if:
    # library is on a larger scale than pixel (ie library in nm, pixel in microns)
    # or pixel is on a larger scale than library (ie pixel in nm, library in microns)
    if (np.min(lib_wl)> np.max(pixel_wl)) or (np.min(pixel_wl) > np.max(lib_wl)):
        mean_lib = np.mean(lib_wl)
        mean_pixel = np.mean(pixel_wl)
        scale = 10**round(np.log10(mean_pixel/mean_lib))
    else:
        scale = 1

    return scale


def feature_matching(self):
    verbose = False


    ########################################################################
    # Prepare the data
    self.statusBar.showMessage('Preparing data scores...')
    self.progressBar.setValue(0)

    # get the pixel spectrum
    pixel = self.MPWidget_pixel.getFigure().gca().lines[0].get_ydata()
    wl = self.MPWidget_pixel.getFigure().gca().lines[0].get_xdata()

    # resample the selected libraries
    resampled_libraries = []
    selected_libraries_indices = sorted(set(index.row() for index in self.table_view.selectedIndexes()))
    for rowIdx in selected_libraries_indices:
        library_file_name = self.table_view.item(rowIdx, 8).text()
        lib = copy.deepcopy(self.spectral_libraries[library_file_name])
        lib.bands.centers = [wl * float(self.table_view.item(rowIdx, 0).text()) for wl in lib.bands.centers] # apply scale to wl
        lib.spectra =  lib.spectra * float(self.table_view.item(rowIdx, 1).text()) # apply scale to y-values

        # check if we need to resample the library
        lib_need_to_resample = True
        if len(lib.bands.centers) == len(list(wl)):
            if lib.bands.centers == list(wl):
                lib_need_to_resample = False

        # resample if needed
        if lib_need_to_resample:
            # resample library to pixel wavelengths
            # compute resampling matrix
            lib_placeholder = copy.deepcopy(lib)
            lib_placeholder.bands.centers = list(wl)
            lib_placeholder.bands.bandwidths = None
            resample = resampling.BandResampler(lib.bands, lib_placeholder.bands)
            # resample
            lib.spectra = np.matmul(lib.spectra, resample.matrix.T)
            lib.bands.centers = list(wl)
            resampled_libraries.append(lib)
        else:
            resampled_libraries.append(lib)

    # Merge the libraries
    lib_spectra = resampled_libraries[0].spectra
    spectra_names = resampled_libraries[0].names
    file_names = [resampled_libraries[0].params.filename]*len(spectra_names)
    num_libs = len(resampled_libraries)
    for idx in range(1,num_libs):
        lib_spectra =  np.vstack((lib_spectra,resampled_libraries[idx].spectra))
        spectra_names = spectra_names + resampled_libraries[idx].names
        file_names = file_names +[resampled_libraries[idx].params.filename]*len(spectra_names)
    nSpectra = len(spectra_names)
    nBands = len(pixel)
    nFeatures = len(self.features)

    # library spectra: lib_spectra
    # pixel spectrum: pixel
    # wavelengths: wl

    feature_scores = np.zeros((nSpectra,nFeatures))

    idx = 0
    for key in self.features.keys():
        feature = self.features[key]
        indices = feature.idxdata.astype(int)
        lib_data = lib_spectra[:,indices]
        pixel_data = pixel[indices]

        # compute the R-squared coefficient
        pixel_data__ms_tiled = np.tile(pixel_data-np.mean(pixel_data), [nSpectra, 1])
        lib_data_ms = lib_data - np.transpose(np.tile(np.mean(lib_data, axis=1), [len(indices),1]))
        prod = np.multiply(lib_data_ms, pixel_data__ms_tiled)
        prod = prod.sum(axis=1)/len(indices)
        std_pix = np.std(pixel_data)
        std_lib = np.std(lib_data, axis=1)
        std_both = std_pix*std_lib
        std_both[std_both <= 0] = 0.0000001
        R = prod/std_both
        R[R>1] = 1
        R[R<-1] = -1
        feature_scores[:,idx] = R
        idx = idx + 1

    return spectra_names, feature_scores, lib_spectra
