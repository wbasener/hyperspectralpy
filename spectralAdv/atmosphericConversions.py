import numpy as np
import h5py
import os
import spectral


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


def convert_spectrum(spectrum, wl, atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index, aerosol_index , atm_dict_resampled, atm_dict_selection):
    """
    This function gets the desried coefficients from the coefficients array.
    inputs:
        spectrum = spectrum to convert
        wl = wavelengths
        atm_coeff = The atmospherics dictionary
        conversion_type = The conversiton type, either ref_to_rad or rad_to_ref
        solar_zenith_angle = solar zenitgh angle - must be between 0 and 90
        atmospheric_index = atmospheric index:
            0 = Tropical
            1 = Midlat_summer
            2 = Midlat_winter
            3 = Subarc_summer
            4 = Subarc_winter
            5 = US_standard_1976
        aerosol_index: aerosol index:
            0 = Rural: light pollution
            1 = Rural: medium level pollution
            2 = Rural: heavy pollution
            3 = Urban: light pollution
            4 = Urban: medium level pollution
            5 = Urban: heavy pollution
            6 = Desert: light pollution
            7 = Desert: medium level pollution
            8 = Desert: heavy pollution
            9 = Maritime_Navy: light pollution
            10 = Maritime_Navy: medium level pollution
            11 = Maritime_Navy: heavy pollution
    output:
        ok = check for errors
        spectrum = the converted spectrum
    """

    # get the coefficients for the desired conversion
    ok, atm_poly_coeff = get_atm_poly_coeff(atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index,
                                            aerosol_index)
    if ok == False:
        # treturn ok with the value of False and the error message from get_atm_poly_coeff
        return ok, atm_poly_coeff

    # check that wavelengths match those for microscene
    wl_check = True
    if len(wl) == len(atm_coeff['wl']):
        # convert to micrometers if needed
        if np.mean(wl) > 100:
            wl = wl/1000
        # check minimum diff between wavelength bands
        if np.max(wl - atm_coeff['wl']) > 10**(-3):
                wl_check = False
    else:
        wl_check = False

    if wl_check == False:
        # the sensor wavelengths are different that Microscene
        # In this case we resample the coefficients to the sensor wavelengths,
        # Some research is needed to determine if this is a valid method to
        # approximate the coefficients for a non-microscene sensor.

        # convert to micrometers if needed
        if np.mean(wl) > 100:
            wl = wl/1000
        # build the band resampling function
        resample = spectral.BandResampler(atm_coeff['wl'], wl)
        atm_poly_coeff_resampled = np.zeros([len(wl), 3])
        # resample the coefficients
        for i in range(3):
            atm_poly_coeff[:, i] = interpolate_nans(atm_poly_coeff[:, i])
            atm_poly_coeff_resampled[:, i] = resample(atm_poly_coeff[:, i])
            atm_poly_coeff_resampled[:, i] = interpolate_nans(atm_poly_coeff_resampled[:, i])

        # apply the conversion coefficients
        spectrum_out = atm_poly_coeff_resampled[:,0]*spectrum**2 + atm_poly_coeff_resampled[:,1]*spectrum + atm_poly_coeff_resampled[:,2]
    else:
        # apply the conversion coefficients
        spectrum_out = atm_poly_coeff[:,0]*spectrum**2 + atm_poly_coeff[:,1]*spectrum + atm_poly_coeff[:,2]

    # apply the gas absorption
    spectrum_out = appy_gas_absorption(spectrum_out, atm_dict_resampled, atm_dict_selection)
    return True, spectrum_out

def convert_image(image_arr, wl, atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index, aerosol_index):
    """
    This function gets the desried coefficients from the coefficients array.
    This function gets the desried coefficients from the coefficients array.
    inputs:
        image_arr = image array
        wl = wavelengths
        atm_coeff = The atmospherics dictionary
        conversion_type = The conversiton type, either ref_to_rad or rad_to_ref
        solar_zenith_angle = solar zenitgh angle - must be between 0 and 90
        atmospheric_index = atmospheric index:
            0 = Tropical
            1 = Midlat_summer
            2 = Midlat_winter
            3 = Subarc_summer
            4 = Subarc_winter
            5 = US_standard_1976
        aerosol_index: aerosol index:
            0 = Rural: light pollution
            1 = Rural: medium level pollution
            2 = Rural: heavy pollution
            3 = Urban: light pollution
            4 = Urban: medium level pollution
            5 = Urban: heavy pollution
            6 = Desert: light pollution
            7 = Desert: medium level pollution
            8 = Desert: heavy pollution
            9 = Maritime_Navy: light pollution
            10 = Maritime_Navy: medium level pollution
            11 = Maritime_Navy: heavy pollution
    output:
        ok = check for errors
        image_arr_out = the converted spectrum
    """

    # get the coefficients for the desired conversion
    ok, atm_poly_coeff = get_atm_poly_coeff(atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index,
                                            aerosol_index)
    if ok == False:
        # treturn ok with the value of False and the error message from get_atm_poly_coeff
        return ok, atm_poly_coeff

    # check that wavelengths match those for microscene
    wl_check = True
    if len(wl) == len(atm_coeff['wl']):
        # convert to micrometers if needed
        if np.mean(wl) > 100:
            wl = wl/1000
        # check minimum diff between wavelength bands
        if np.max(wl - atm_coeff['wl']) > 10**(-3):
                wl_check = False
    else:
        wl_check = False
    if wl_check == False:
        # the sensor wavelengths are different that Microscene
        # In this case we resample the coefficients to the sensor wavelengths,
        # Some research is needed to determine if this is a valid method to
        # approximate the coefficients for a non-microscene sensor.

        # convert to micrometers if needed
        if np.mean(wl) > 100:
            wl = wl/1000
        # build the band resampling function
        resample = spectral.BandResampler(atm_coeff['wl'], wl)
        atm_poly_coeff_resampled = np.zeros([len(wl), 3])
        # resample the coefficients
        for i in range(3):
            atm_poly_coeff_resampled[:, i] = resample(atm_poly_coeff[:, i])

        # apply the conversion coefficients
        image_arr_out = np.zeros(np.shape(image_arr))
        for band_idx in range(len(wl)):
            image_arr_out[:, :, band_idx] = np.squeeze(
                atm_poly_coeff[band_idx, 0] * image_arr[:, :, band_idx] ** 2 +
                atm_poly_coeff[band_idx, 1] * image_arr[:, :, band_idx] +
                atm_poly_coeff[band_idx, 2])
            #image_arr_out[:, :, band_idx] = np.squeeze(
            #    atm_poly_coeff[band_idx, 2] * image_arr[:, :, band_idx] ** 2 +
            #    atm_poly_coeff[band_idx, 1] * image_arr[:, :, band_idx] +
            #    atm_poly_coeff[band_idx, 0])

        return True, image_arr_out

    # apply the conversion coefficients
    image_arr_out = np.zeros(np.shape(image_arr))
    for band_idx in range(len(wl)):
        image_arr_out[:,:,band_idx] = np.squeeze(
                atm_poly_coeff[band_idx, 0] * image_arr[:, :,band_idx]**2 +
                atm_poly_coeff[band_idx, 1] * image_arr[:, :,band_idx] +
                atm_poly_coeff[band_idx, 2])
        #image_arr_out[:,:,band_idx] = np.squeeze(
        #        atm_poly_coeff[band_idx, 2] * image_arr[:, :,band_idx]**2 +
        #        atm_poly_coeff[band_idx, 1] * image_arr[:, :,band_idx] +
        #        atm_poly_coeff[band_idx, 0])

    return True, image_arr_out

def resample_atm_dict(atm_dict,wl):
    atm_dict_resampled = {}
    gas_names = atm_dict.keys()
    for name in gas_names:
        resample = spectral.BandResampler(atm_dict[name]['wl'], wl)
        atm_dict_resampled[name] = resample(atm_dict[name]['transmission'])
        # replace any NaNs (from non-overlapping wavelengths, where gas spectra not availalbe) to 1
        atm_dict_resampled[name][np.isnan(atm_dict_resampled[name])] = 1
    return atm_dict_resampled

def appy_gas_absorption(spectrum, atm_dict_resampled, atm_dict_selection):
    for name,exponent in zip(atm_dict_selection['checked names'], atm_dict_selection['density modifiers']):
        gas_spectrum =  atm_dict_resampled[name]
        spectrum = (gas_spectrum**exponent)*spectrum
    return spectrum

#def modify_gas_content(gas_wl, gas_transmission_spectrum, wl, specctrum, exponent):
#    if exponent == 0:
#        return specctrum
#    # build the band resampling function
#    resample = spectral.BandResampler(gas_wl, wl)
#    gas_spectrum_resampled = resample(gas_transmission_spectrum)
#    return (gas_spectrum_resampled**exponent)*specctrum


def get_atm_poly_coeff(atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index, aerosol_index):
    """
    This function gets the desried coefficients from the coefficients array.
    inputs:
        atm_coeff = The atmospherics dictionary
        conversion_type = The conversiton type, either ref_to_rad or rad_to_ref
        solar_zenith_angle = solar zenitgh angle - must be between 0 and 90
        atmospheric_index = atmospheric index:
            0 = Tropical
            1 = Midlat_summer
            2 = Midlat_winter
            3 = Subarc_summer
            4 = Subarc_winter
            5 = US_standard_1976
        aerosol_index = aerosol index:
            0 = Rural: light pollution
            1 = Rural: medium level pollution
            2 = Rural: heavy pollution
            3 = Urban: light pollution
            4 = Urban: medium level pollution
            5 = Urban: heavy pollution
            6 = Desert: light pollution
            7 = Desert: medium level pollution
            8 = Desert: heavy pollution
            9 = Maritime_Navy: light pollution
            10 = Maritime_Navy: medium level pollution
            11 = Maritime_Navy: heavy pollution
    output:
        ok = check for errors
        atm_poly_coeff = the coefficients for the atmospheric conversion:
            These coefficients are used as follows:
            x = input (radiance or reflectiance)
            y = outout (reflectance or radiance)
            [c0,c1,c2] = atm_poly_coeff
            y = c0*x^2 + c1*x + c3
    """

    # check for valid inputs
    err_msg = []
    ok = True
    if not (conversion_type == 'ref_to_rad' or conversion_type == 'rad_to_ref'):
        err_msg = err_msg + ['error: unknown conversion_type']
        ok = False
    if not (solar_zenith_angle > 0 and solar_zenith_angle < 90):
        err_msg = err_msg + ['error: solar_zenith_angle out of bounds (0-90)']
        ok = False
    if not (atmospheric_index >= 0 and atmospheric_index <= 5):
        err_msg = err_msg + ['error: atmospheric_index out of bounds (0-5)']
        ok = False
    if not (aerosol_index >= 0 and aerosol_index <= 11):
        err_msg = err_msg + ['error: aerosol_index out of bounds (0-11)']
        ok = False
    # print error message and quit
    if ok == False:
        for msg in err_msg:
            print(msg)
        return ok, msg

    # create the key for the atm_coeff dict
    key = conversion_type + '_sza' + str(solar_zenith_angle)

    # fill out the polynomial coefficients from the array
    atm_poly_coeff = np.zeros([453,3])
    for band_index in range(453):
        index = (band_index)*72 + atmospheric_index*12 + aerosol_index
        atm_poly_coeff[band_index, :] = atm_coeff[key][:, index]

    return ok, atm_poly_coeff

def read_atmospheric_coefficients():
    """
    This function reads the atmostpheric coefficients file.
    """

    try:
        os.chdir(os.path.dirname(__file__))
        f = h5py.File('coefficients_all_to_W.mat', 'r')
        atm_coeff = dict()
        # Read the coefficients for converting reflectance to radiance
        atm_coeff['ref_to_rad_sza5'] = np.array(f.get('coeff_ref_to_rad_sza5'))
        atm_coeff['ref_to_rad_sza10'] = np.array(f.get('coeff_ref_to_rad_sza10'))
        atm_coeff['ref_to_rad_sza15'] = np.array(f.get('coeff_ref_to_rad_sza15'))
        atm_coeff['ref_to_rad_sza20'] = np.array(f.get('coeff_ref_to_rad_sza20'))
        atm_coeff['ref_to_rad_sza25'] = np.array(f.get('coeff_ref_to_rad_sza25'))
        atm_coeff['ref_to_rad_sza30'] = np.array(f.get('coeff_ref_to_rad_sza30'))
        atm_coeff['ref_to_rad_sza35'] = np.array(f.get('coeff_ref_to_rad_sza35'))
        atm_coeff['ref_to_rad_sza40'] = np.array(f.get('coeff_ref_to_rad_sza40'))
        atm_coeff['ref_to_rad_sza45'] = np.array(f.get('coeff_ref_to_rad_sza45'))
        atm_coeff['ref_to_rad_sza50'] = np.array(f.get('coeff_ref_to_rad_sza50'))
        atm_coeff['ref_to_rad_sza55'] = np.array(f.get('coeff_ref_to_rad_sza55'))
        atm_coeff['ref_to_rad_sza60'] = np.array(f.get('coeff_ref_to_rad_sza60'))
        atm_coeff['ref_to_rad_sza65'] = np.array(f.get('coeff_ref_to_rad_sza65'))
        atm_coeff['ref_to_rad_sza70'] = np.array(f.get('coeff_ref_to_rad_sza70'))
        atm_coeff['ref_to_rad_sza75'] = np.array(f.get('coeff_ref_to_rad_sza75'))
        atm_coeff['ref_to_rad_sza80'] = np.array(f.get('coeff_ref_to_rad_sza80'))
        atm_coeff['ref_to_rad_sza85'] = np.array(f.get('coeff_ref_to_rad_sza85'))
        # Read the coefficients for converting radiance to reflectance
        atm_coeff['rad_to_ref_sza5'] = np.array(f.get('coeff_rad_to_ref_sza5'))
        atm_coeff['rad_to_ref_sza10'] = np.array(f.get('coeff_rad_to_ref_sza10'))
        atm_coeff['rad_to_ref_sza15'] = np.array(f.get('coeff_rad_to_ref_sza15'))
        atm_coeff['rad_to_ref_sza20'] = np.array(f.get('coeff_rad_to_ref_sza20'))
        atm_coeff['rad_to_ref_sza25'] = np.array(f.get('coeff_rad_to_ref_sza25'))
        atm_coeff['rad_to_ref_sza30'] = np.array(f.get('coeff_rad_to_ref_sza30'))
        atm_coeff['rad_to_ref_sza35'] = np.array(f.get('coeff_rad_to_ref_sza35'))
        atm_coeff['rad_to_ref_sza40'] = np.array(f.get('coeff_rad_to_ref_sza40'))
        atm_coeff['rad_to_ref_sza45'] = np.array(f.get('coeff_rad_to_ref_sza45'))
        atm_coeff['rad_to_ref_sza50'] = np.array(f.get('coeff_rad_to_ref_sza50'))
        atm_coeff['rad_to_ref_sza55'] = np.array(f.get('coeff_rad_to_ref_sza55'))
        atm_coeff['rad_to_ref_sza60'] = np.array(f.get('coeff_rad_to_ref_sza60'))
        atm_coeff['rad_to_ref_sza65'] = np.array(f.get('coeff_rad_to_ref_sza65'))
        atm_coeff['rad_to_ref_sza70'] = np.array(f.get('coeff_rad_to_ref_sza70'))
        atm_coeff['rad_to_ref_sza75'] = np.array(f.get('coeff_rad_to_ref_sza75'))
        atm_coeff['rad_to_ref_sza80'] = np.array(f.get('coeff_rad_to_ref_sza80'))
        atm_coeff['rad_to_ref_sza85'] = np.array(f.get('coeff_rad_to_ref_sza85'))
        atm_coeff['wl'] = np.array(f.get('wavelengths')).flatten()
        return True, atm_coeff
    except:
        err_msg = ['error: atmoespheric coefficencts file invalid or not found.']
        print(err_msg[0])
        return False, err_msg


def test():
    ok, atm_coeff = read_atmospheric_coefficients()
    conversion_type = 'ref_to_rad'
    solar_zenith_angle = 15
    atmospheric_index = 5
    aerosol_index = 3
    ok, atm_poly_coeff = get_atm_poly_coeff(atm_coeff, conversion_type, solar_zenith_angle, atmospheric_index, aerosol_index)
    import matplotlib.pyplot as plt
    plt.plot(atm_poly_coeff)