import sys
import os
import numpy as np
import matplotlib.pyplot as plt 
from spectral import *
from spectralAdv import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

os.chdir(os.getcwd())

class MenuBar(QMainWindow):
    pasteSpectrum = pyqtSignal(dict)

    def __init__(self):
        super(MenuBar, self).__init__()
        self.setWindowTitle("Spectral Tools 1.0")
        self.setWindowIcon(QIcon('icon.ico'))
        self.setParameters()
        if self.settings.screen_width > 3000:
            self.setGeometry(20, 80, 1200, 10)
        else:
            self.setGeometry(20, 80, 600, 10)

        openImageAction = QAction("Open Image",self)
        openImageAction.setShortcut("Ctrl+O")
        openImageAction.triggered.connect(self.open_image)
        openLibraryAction = QAction("Open Library",self)
        openLibraryAction.setShortcut("Ctrl+L")
        openLibraryAction.triggered.connect(self.open_library)
        changeSettingsAction = QAction("Settings",self)
        #changeSettingsAction.setShortcut("Ctrl+S")
        changeSettingsAction.triggered.connect(self.change_settings)
        quitAction = QAction("Quit",self)
        #quitAction.setShortcut("Ctrl+Q")
        quitAction.triggered.connect(self.close_application)
        
        pcaAction = QAction("Principle Components Whiten",self)
        pcaAction.triggered.connect(self.pc_whiten)        
        aceAction = QAction("Target Detection: ACE",self)
        aceAction.triggered.connect(self.ace_target_detection)        
        mfAction = QAction("Target Detection: Matched Filter",self)
        mfAction.triggered.connect(self.mf_target_detection)
        quacAction = QAction("QUAC Atmospheric Compensation",self)
        quacAction.triggered.connect(self.quac_atmospheric_compensation)
        classAnalysisAction = QAction("Class Analysis",self)
        classAnalysisAction.triggered.connect(self.class_analysis)

        libraryManagerAction = QAction("Spectral Library Manager",self)
        libraryManagerAction.triggered.connect(self.spectral_library_manager)
        spectralContrastViewerAction = QAction("Spectral Contrast Viewer",self)
        spectralContrastViewerAction.triggered.connect(self.spectral_contrast_viewer)
        confuserFinderAction = QAction("Confuser Finder",self)
        confuserFinderAction.triggered.connect(self.not_supportrd)
        libraryBuilderAction = QAction("Library Builder",self)
        libraryBuilderAction.triggered.connect(self.not_supportrd)

        atmostphericConversionAction = QAction("Atmospheric Conversion",self)
        atmostphericConversionAction.triggered.connect(self.atmostpheric_conversion)

        materialIdentificationAction = QAction("Material Identification",self)
        materialIdentificationAction.triggered.connect(self.material_identification)

        batchImageComparisonAction = QAction("Bhattacharyya Distance",self)
        batchImageComparisonAction.triggered.connect(self.bhattacharyya_comparison)
                
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu("&File ")
        fileMenu.addAction(openImageAction)
        fileMenu.addAction(openLibraryAction)
        fileMenu.addAction(changeSettingsAction)
        fileMenu.addAction(quitAction)
        fileMenu = mainMenu.addMenu("&Spectral Images ")
        fileMenu.addAction(pcaAction)
        fileMenu.addAction(aceAction)
        fileMenu.addAction(mfAction)
        fileMenu.addAction(classAnalysisAction)
        fileMenu.addAction(quacAction)
        fileMenu.addAction(atmostphericConversionAction)
        fileMenu = mainMenu.addMenu("&Spectral Libraries ")
        fileMenu.addAction(libraryManagerAction)
        fileMenu.addAction(spectralContrastViewerAction)
        fileMenu.addAction(confuserFinderAction)
        fileMenu.addAction(libraryBuilderAction)
        fileMenu = mainMenu.addMenu("Material &Identification ")
        fileMenu.addAction(materialIdentificationAction)
        fileMenu = mainMenu.addMenu("&Microscene ")
        fileMenu.addAction(batchImageComparisonAction)

        self.show()

    def keyPressEvent(self, event):
        soundEffects = {'Trek': [Qt.Key_T,Qt.Key_R,Qt.Key_E,Qt.Key_K]}
        if type(event) == QKeyEvent:
            if event.key() == Qt.Key_End:
                self.easterEggKey = []
                self.sounds = None
                self.setStyleSheet("color: rgb(0, 0, 0);")
            if event.key() == Qt.Key_Escape:
                self.easterEggKey = []
            else:
                self.easterEggKey.append(event.key())
        else:
            event.ignore()
        for key in soundEffects.keys():
            if self.easterEggKey == soundEffects[key]:
                self.sounds = key
                # change text to red:
                self.setStyleSheet("color: rgb(255, 0, 0);")

    def change_settings(self):
        settingsDialog = settings.settingsDialog(self)
        settingsDialog.show()

    def setParameters(self):
        self.imageDir = None
        self.libraryDir = None
        self.outputDir = None
        self.openImages = None
        self.easterEggKey = []
        self.copied_spectrum = None
        self.sounds = None
        self.spectral_libraries = {}
        self.settings = settings.settings_struc()
        self.settings.screen_width = app.desktop().screenGeometry().width()
        self.settings.screen_height = app.desktop().screenGeometry().height()
        self.imageViewerDict = {}
        self.linked_keys = []
        
    def close_application(self):
        print("Closing...")
        sys.exit()
        
    def not_supportrd(self):
        QMessageBox.information(self, "Not Supported","That functionality is not yet supported.")

    def copy_spectrum(self, copied_spectrum):
        self.copied_spectrum = copied_spectrum

    def paste_spectrum_request(self, i):
        if self.copied_spectrum == None:
            QMessageBox.warning(self, "No spectrum available for paste.",
                                "A spectrum must be copied.  Use either of the follwoing methods:\n "+
                                "  - Select desired spectrum from the 'Copy Spectrum' 'menu in a spectral plot\n"+
                                "  - Right-click in a spectral plot and select the desired spectrum from the popup menu\n"+
                                "  - Left-click on plot of the desired spectrum and press the 'C' key")
            return

        # emit the signal to send data back
        self.pasteSpectrum.emit(self.copied_spectrum)
        
    def open_image(self):
        try:
            easterEggSounds.play(self.sounds,'open_image')
        except:
            pass

        im_fname,ok = self.select_image()
        if ok:
            new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
            self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings, sounds = self.sounds, im_fname=im_fname)
            self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
            self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
            self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
            self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
            self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
            self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
            self.imageViewerDict[new_key].show()

    def imvClosed(self, key):
        del self.imageViewerDict[key]
        if key in self.linked_keys:
            del self.linked_keys[key]
            if len(self.linked_keys) == 1:
                self.linked_keys = []

    def linkImageViewers(self, key):
        self.linker = imageViewerLinker.imageViewerLinker(key=key, settings=self.settings,
                                                          linked_keys = self.linked_keys,
                                                          imageViewerDict = self.imageViewerDict)
        # create the linking GUI for user selection
        self.linker.show()
        # if the users accepts a linking, create it
        if self.linker.exec():

            # get teh viewer parameters of the of the initiating viewer viewer
            view_parameters = self.imageViewerDict[key].getViewParameters()
            # get the keys for all linked viewers as a list
            self.linked_keys = self.linker.linked_keys

            # if only one viewer is selected, deselect all
            if len(self.linked_keys) < 2:
                self.linked_keys = []
                for key in list(self.imageViewerDict.keys()):
                    self.imageViewerDict[key].widget_toggle_linked_image_btn.setVisible(False)
            else:
                # adjust viewer parameters for all viewers to match the initiating viewer
                for key in self.linked_keys:
                    self.imageViewerDict[key].setViewParameters(view_parameters)
                    self.imageViewerDict[key].widget_toggle_linked_image_btn.setVisible(True)
        else:
            self.linked_keys = []
            for key in list(self.imageViewerDic.keys()):
                self.imageViewerDict[key].widget_toggle_linked_image_btn.setVisible(False)

    def updateLinkedViewerParameters(self, initiating_key):
        if initiating_key in self.linked_keys:
            view_parameters = self.imageViewerDict[initiating_key].getViewParameters()
            for key in self.linked_keys:
                if key != initiating_key:
                    # use a try catch in case this image viewer was closed
                    try:
                        self.imageViewerDict[key].setViewParameters(view_parameters)
                    except:
                        pass

    def requestLinkedPixmap(self, idx, requesting_key):
        # this function retreives a pixmap (for the displayed image)
        # when requested from a linked image viewer

        #return if there are no linked keys
        if len(self.linked_keys) == 0:
            return

        if idx >= len(self.linked_keys):
            idx = 0

        if self.linked_keys[idx] == requesting_key:
            idx = idx + 1
            if idx >= len(self.linked_keys):
                idx = 0

        pixmap_key = self.linked_keys[idx]
        pixmap = self.imageViewerDict[pixmap_key].getPixmap()
        self.imageViewerDict[requesting_key].show_liked_image(pixmap, idx)
        print(idx)
        print(pixmap_key)

    def open_library(self):
        try:
            easterEggSounds.play(self.sounds,'open_image')
        except:
            pass

        lib, ok = specTools.select_library(self, prompt="Choose a library")
        if ok:
            self.spectral_library_manager()
            self.libraryManager.add_to_table(lib)
            self.spectral_library_viewer(lib)

    def spectral_library_viewer(self,lib):
        try:
            self.libraryViewer = libraryViewer.libraryViewer(parent=self,
                                                             settings=self.settings,
                                                             libraryDir=self.libraryDir,
                                                             lib=lib)
            self.libraryViewer.copiedSpectrum.connect(self.copy_spectrum)
            self.libraryViewer.openedLibrary.connect(self.opened_library_in_viewer)
            self.libraryViewer.pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.libraryViewer.paste_spectrum)
            self.libraryViewer.show()
        except:
            QMessageBox.warning(self,"Warning",
                "Error with spectral library viewer.")

    def opened_library_in_viewer(self, lib_dict):
        lib = lib_dict['lib']# unpack from the dictionary
        # pass the library to the manager
        self.libraryManager.add_to_table(lib)
        
    def pc_whiten(self):
        try:
            easterEggSounds.play(self.sounds,'other')
        except:
            pass

        # Get files from user
        fname_image,ok = self.select_image()
        if not ok:
            return
        fname_save,ok = self.select_output_filename(default_name="PCA")
        if not ok:
            return
        
        try:
            ## Read Files and Compute Matched Filder
            # Read the image files
            im = envi.open(fname_image+'.hdr')
            im = specTools.apply_bbl(im)
            im_arr = specTools.envi_load(im)
            # Compute Statistics and Whitening Transform
            pc = specTools.compute_screened_pca(im_arr,0)
            W = specTools.compute_whitening(pc,0)
            # Whiten the image
            Wim = specTools.whiten_image(W,im_arr,im,0) 
            
            # save the result      
            # create pca band names
            bnames = ['PCA '+s for s in map(str, range(im.nbands))]              
            envi.save_image(fname_save+'.hdr',Wim.im3d.astype('float32'),metadata={'band names': bnames},ext='',force=True)
            new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
            self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings, sounds = self.sounds, im_fname=fname_save)
            self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
            self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
            self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
            self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
            self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
            self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
            self.imageViewerDict[new_key].show()
            QMessageBox.information(self, "Completed: PCA",
                "Image: %s\n\nNumber of Bands: %d"%
                (os.path.basename(fname_image),im.nbands))
        except:
            QMessageBox.warning(self,"Failed: PCA", 
                "Image: %s"%os.path.basename(fname_image))

        
    def ace_target_detection(self):
        try:
            easterEggSounds.play(self.sounds,'other')
        except:
            pass
        # Get files from user
        fname_image,ok = self.select_image()
        fname_library,ok = self.select_library()  
        fname_save,ok = self.select_output_filename(default_name="ACE")
        
        try:
            ## Read Files and Compute Matched Filder
            # Read the image files
            v = 0 # verboes (0 = no output, 1 = more output)
            im = envi.open(fname_image+'.hdr')
            im = specTools.apply_bbl(im)
            im_arr = specTools.envi_load(im)
            # Read the detection library
            det_lib = specTools.load_and_resample_library(fname_library,im,im_arr,v)        
            # Compute Statistics and Whitening Transform
            pc = specTools.compute_screened_pca(im_arr,v)
            W = specTools.compute_whitening(pc,1)        
            # Whiten the detection library
            Wdet_lib = specTools.whiten_library(det_lib,W,v)
            # Whiten the image
            Wim = specTools.whiten_image(W,im_arr,im,v)        
            # Compute matched filter
            ace_arr = specTools.ace(Wim,Wdet_lib,v)
            
            # save the result        
            envi.save_image(fname_save+'.hdr',ace_arr.astype('float32'),
                metadata={'band names': det_lib.names, 'default stretch': '0.000000 1.000000 linear'},ext='',force=True)
            new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
            self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings, sounds = self.sounds, im_fname=fname_save)
            self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
            self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
            self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
            self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
            self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
            self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
            self.imageViewerDict[new_key].show()
            QMessageBox.information(self, "Completed: ACE", 
                "Image: %s\n\nLibrary: %s\n\nNumber of Spectra: %d"% 
                (os.path.basename(fname_image),os.path.basename(fname_library),len(det_lib.names)))
        except:
            QMessageBox.warning(self,"Failed: ACE", 
                "Image: %s\n\nLibrary: %s"%(os.path.basename(fname_image),os.path.basename(fname_library)))
        
    
    def mf_target_detection(self):         
        # Get files from user
        fname_image,ok = self.select_image()
        fname_library,ok = self.select_library()        
        fname_save,ok = self.select_output_filename(default_name="MF")
            
        try:
            ## Read Files and Compute Matched Filder
            # Read the image files
            v = 0 # verboes (0 = no output, 1 = more output)
            im = envi.open(fname_image+'.hdr')
            im = specTools.apply_bbl(im)
            im_arr = specTools.envi_load(im)
            # Read the detection library
            det_lib = specTools.load_and_resample_library(fname_library,im,im_arr,v)
            # Compute Statistics and Whitening Transform
            pc = specTools.compute_screened_pca(im_arr,v)
            W = specTools.compute_whitening(pc,v)        
            # Whiten the detection library
            Wdet_lib = specTools.whiten_library(det_lib,W,v)
            # Whiten the image
            Wim = specTools.whiten_image(W,im_arr,im,v)        
            # Compute matched filter
            mf_arr = specTools.mf(Wim,Wdet_lib,v)
            
            # save the result
            envi.save_image(fname_save+'.hdr',mf_arr.astype('float32'),
                metadata={'band names': det_lib.names, 'default stretch': '0.000000 1.000000 linear'},ext='',force=True)
            new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
            self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings, sounds = self.sounds, im_fname=fname_save)
            self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
            self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
            self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
            self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
            self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
            self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
            self.imageViewerDict[new_key].show()
            QMessageBox.information(self, "Completed: Matched Filter", 
                "Image: %s\n\nLibrary: %s\n\nNumber of Spectra: %d"% 
                (os.path.basename(fname_image),os.path.basename(fname_library),len(det_lib.names)))
        except:
            QMessageBox.warning(self,"Failed: Matched Filter", 
                "Image: %s\n\nLibrary: %s"%(os.path.basename(fname_image),os.path.basename(fname_library)))
        
    
    def quac_atmospheric_compensation(self):
        # Get files from user
        fname_im,ok = self.select_image(prompt="Choose an image for atmospheric compensation")
                        
                                          
        if os.path.isfile('quac_endmembers'):
            fname_em = 'quac_endmembers'
        else:
            QMessageBox.warning(self, "Warning","quac_endmembers file not found.  You will be prompted for the quac_endmembers file provided with this software.  "+
                "If this file is located in the direcotry with menu.py then you will not have to select it manually in the future.")
            fname_em,ok = QFileDialog.getOpenFileName(self, "Choose the quac_endmembers file",'quac_endmembers')
            fname_em = fname_em[0]
            if not ok:
                return                    
        
        fname_imout,ok = self.select_output_filename(default_name="reflectance_quac")
        
        try:
            #fname_em = 'endmembers'
            bad_ranges = [[1.3,1.425],[1.79,1.96]]
            subset_wl_desired = [1,1.1,1.2,1.2,1.3,1.6,1.65,1.7,2.15,2.2,2.25,2.35]
            #subset_wl_desired = [1.1,1.3,1.65,2.2,2.35]
            num_endmembers = 8 # number of endmembers per tile
            make_plots = 1
            
            # load radiance image (and initiate data structure)
            data = quac.load_image(fname_im, num_endmembers, make_plots)        
            # remove bad bands
            # NOTE: This determines the output wavelengths
            data = quac.remove_bad_bands(data,bad_ranges)        
            # cleanup image for offset computation
            #data = quac.pre_offset_cleanup(data)        
            # remove edge pixels
            data = quac.remove_edge_pixels(data)        
            # create a list of the radiance spectra at subset wavelengths
            data = quac.create_subset_indices(data,subset_wl_desired)        
            # Compute offsets (and subtract offset from radiance list)
            data = quac.compute_offsets(data)        
            # Compute and normalize for solar black body
            data = quac.subtract_solar_black_body(data)        
            # compute pseudo reflectance (by dividing by mean)
            data = quac.compute_pseudo_reflectance(data)        
            # Remove Vegetation and wet soil form consideration as endmembers
            data = quac.remove_veg(data)        
            # get the endmembers
            data = quac.SMACC_endmembers_tiled(data)        
            # open and resample endmember library
            data = quac.load_ideal_endmember_library(data,fname_em)        
            # compute gain
            #data = quac.compute_poly_coeff(data)  # TEMP ADDED
            data = quac.compute_gain(data)        
            # apply correction and save reflectance image
            data = quac.correct_and_save_image(data,fname_imout)        
            # plot the components if desired
            quac.plot_quac_components(data)
            QMessageBox.information(self, "Completed: QUAC", 
                "Output Reflectance Image: \n%s"% fname_imout)
            new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
            self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings, sounds = self.sounds, im_fname=fname_imout)
            self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
            self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
            self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
            self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
            self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
            self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
            self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
            self.imageViewerDict[new_key].show()
        except:
            QMessageBox.warning(self, "Warning","QUAC failed for unknown reason.")

    def spectral_contrast_viewer(self):
        if not hasattr(self, 'spectralContrastViewer'):
            # open the viewer -
            self.spectralContrastViewer = spectralContrastViewer.MyWindow(settings=self.settings)
        self.spectralContrastViewer.show()
        #spectralContrastViewer = spectralContrastViewer.MyWindow(parent=self, settings=self.settings)
        #spectralContrastViewer.show()

    def spectral_library_manager(self):
        if not hasattr(self, 'libraryManager'):
            # open the viewer -
            self.libraryManager = libraryManager.libraryManager(settings=self.settings)
            self.libraryManager.openedLibraryInManager.connect(self.opened_library_in_manager)
            self.libraryManager.library_changed.connect(self.library_changed_in_manager)
        self.libraryManager.show()

    def library_changed_in_manager(self, lib_dict):
        self.spectral_libraries = lib_dict

    def opened_library_in_manager(self, lib_dict):
        lib = lib_dict['lib']
        self.spectral_library_manager()
        self.spectral_library_viewer(lib)

    def bhattacharyya_comparison(self):
        if not hasattr(self, 'bhattacharyyaComparison'):
            # open the viewer -
            self.bhattacharyyaComparison = bhattacharyyaComparison.MyWindow(settings=self.settings)
        self.bhattacharyyaComparison.show()
        #bhattacharyyaComparison = bhattacharyyaComparison.MyWindow(parent=self, settings=self.settings)
        #bhattacharyyaComparison.show()

    def material_identification(self):
        # use this to open the material id if we do not want it to reset when closed
        #if not hasattr(self, 'materialIdentificationViewer'):
        #    # open the viewer -
        #    self.materialIdentificationViewer = materialIdentificationViewer.materialIdentificationViewer(
        #        imageDir=self.imageDir, libraryDir=self.libraryDir,
        #        spectral_libraries = self.spectral_libraries)
        try:
            easterEggSounds.play(self.sounds,'material_identification')
        except:
            pass

        self.materialIdentificationViewer = materialIdentificationViewer.materialIdentificationViewer(
            settings=self.settings, imageDir=self.imageDir, libraryDir=self.libraryDir,
            spectral_libraries=self.spectral_libraries)
        self.materialIdentificationViewer.pasteSpectrumRequest.connect(self.paste_spectrum_request)
        self.pasteSpectrum.connect(self.materialIdentificationViewer.paste_spectrum)
        self.materialIdentificationViewer.show()
        self.materialIdentificationViewer.openedLibraryInMaterialId.connect(self.opened_library_in_material_id)
        self.materialIdentificationViewer.openedImageInMaterialId.connect(self.opened_image_in_material_id)

    def atmostpheric_conversion(self):
        self.atmosphericConversionsGUI = atmosphericConversionsGUI.atmosphericConversionsGUI(
            settings=self.settings, imageDir=self.imageDir, libraryDir = self.libraryDir)
        self.atmosphericConversionsGUI.pasteSpectrumRequest.connect(self.paste_spectrum_request)
        self.pasteSpectrum.connect(self.atmosphericConversionsGUI.paste_spectrum)
        self.atmosphericConversionsGUI.show()

    def opened_library_in_material_id(self, lib_dict):
        lib = lib_dict['lib']
        if not hasattr(self, 'libraryManager'):
            # open the viewer -
            self.libraryManager = libraryManager.libraryManager(settings=self.settings)
            self.libraryManager.openedLibraryInManager.connect(self.opened_library_in_manager)
            self.libraryManager.library_changed.connect(self.library_changed_in_manager)
        # pass the library to the manager
        self.libraryManager.add_to_table(lib)

    def opened_image_in_material_id(self, im_dict):
        new_key = specTools.get_next_image_viewer_key(self.imageViewerDict.keys())
        self.imageViewerDict[new_key] = imageViewer.imageViewer(parent=self, key = new_key, settings=self.settings,
                                                im_fname=im_dict['fname_image'],
                                                im=im_dict['im'], im_arr=im_dict['im_arr'])
        self.imageViewerDict[new_key].viewerClosed.connect(self.imvClosed)
        self.imageViewerDict[new_key].linkViewers.connect(self.linkImageViewers)
        self.imageViewerDict[new_key].requestLinkedPixmap.connect(self.requestLinkedPixmap)
        self.imageViewerDict[new_key].viewerParametersChanged.connect(self.updateLinkedViewerParameters)
        self.imageViewerDict[new_key].copiedSpectrum.connect(self.copy_spectrum)
        self.imageViewerDict[new_key].pasteSpectrumRequest.connect(self.paste_spectrum_request)
        self.pasteSpectrum.connect(self.imageViewerDict[new_key].paste_spectrum)
        self.imageViewerDict[new_key].show()

    def class_analysis(self):
        try:
            easterEggSounds.play(self.sounds,'classAnalysis')
        except:
            pass
        classAnalysisGUI = classificationViewer.classAnalysisGUI(parent=self, settings=self.settings)
        classAnalysisGUI.show()
        
    def select_image(self,prompt="Choose an image"):  
        if self.imageDir is None:
            fname_image = QFileDialog.getOpenFileName(self, prompt)
            fname_image = fname_image[0]
        else:
            try:
                fname_image = QFileDialog.getOpenFileName(self, prompt, self.imageDir)
                fname_image = fname_image[0]
            except:
                fname_image = QFileDialog.getOpenFileName(self, prompt)
                fname_image = fname_image[0]
        if fname_image == '':
            return fname_image, False
        fname_image, ok = specTools.is_image_file(fname_image)
        if ok:
            self.imageDir = os.path.dirname(os.path.abspath(fname_image))
            return fname_image, True
        else:
            QMessageBox.warning(self,"File is not valid ENVI image",
                "File Name: %s"%(os.path.basename(fname_image)))
            return fname_image, False
        
    def select_images(self,prompt="Choose one or more images"):  
        if self.imageDir is None:
            fname_images = QFileDialog.getOpenFileNames(self, prompt)
            fname_image = fname_image[0]
        else:
            try:
                fname_images = QFileDialog.getOpenFileNames(self, prompt, self.imageDir)
                fname_image = fname_image[0]
            except:
                fname_images = QFileDialog.getOpenFileNames(self, prompt)
                fname_image = fname_image[0]
        if fname_images == '':
            return
        self.imageDir = os.path.dirname(os.path.abspath(fname_images[0])) 
        return fname_images
        
    def select_library(self,prompt="Choose a library"): 
        if self.libraryDir is None:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.imageDir)
                fname_library = fname_library[0]
            except:
                fname_library = QFileDialog.getOpenFileName(self, prompt)
                fname_library = fname_library[0]
        else:
            try:
                fname_library = QFileDialog.getOpenFileName(self, prompt, self.libraryDir)
                fname_library = fname_library[0]
            except:
                fname_library = QFileDialog.getOpenFileName(self, prompt)
                fname_library = fname_library[0]
        if fname_library == '':
            return fname_library, False
        self.libraryDir = os.path.dirname(os.path.abspath(fname_library)) 
        return fname_library, True

    def select_output_filename(self,prompt="Choose an output filename",default_name=""): 
        if self.outputDir is None:
            try:
                fname_save = QFileDialog.getSaveFileName(self, prompt, os.path.join(self.imageDir,default_name))
                fname_save = fname_save[0]
            except:
                fname_save = QFileDialog.getSaveFileName(self, prompt,default_name)
                fname_save = fname_save[0]
        else:
            try:
                fname_save = QFileDialog.getSaveFileName(self, prompt, os.path.join(self.outputDir,default_name))
                fname_save = fname_save[0]
            except:
                fname_save = QFileDialog.getSaveFileName(self, prompt,default_name)
                fname_save = fname_save[0]
        if fname_save == '':
            return fname_save, False
        self.outputDir = os.path.dirname(os.path.abspath(fname_save)) 
        return fname_save, True

    def select_output_dir(self,prompt="Choose an output directory"): 
        if self.outputDir is None:
            try:
                outputDir = QFileDialog.getExistingDirectory(self, prompt, self.imageDir)
                outputDir = outputDir[0]
            except:
                outputDir = QFileDialog.getExistingDirectory(self, prompt)
                outputDir = outputDir[0]
        else:
            try:
                outputDir = QFileDialog.getExistingDirectory(self, prompt, self.outputDir)
                outputDir = outputDir[0]
            except:
                outputDir = QFileDialog.getExistingDirectory(self, prompt)
                outputDir = outputDir[0]
        if outputDir == '':
            return outputDir, False
        self.outputDir = os.path.abspath(outputDir)
        return outputDir, True

if __name__ == '__main__':
    #app = QApplication.instance() # when running in Canopy
    app = QApplication(sys.argv)
    GUI = MenuBar()
    sys.exit(app.exec_())