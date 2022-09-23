from .specTools import *
from os import listdir
from os import remove
from os import path
from os.path import join
from sys import argv
from sys import exit
import csv
import shapefile
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
import pyqtgraph as pg
import pyqtgraph.opengl as gl

def class_data_from_ROIs_with_Cov(ROIdata):

    # prepare the variables to hold the data
    names = list(ROIdata.keys())
    X = ROIdata[names[0]].spectra
    y = np.zeros(ROIdata[names[0]].npts)

    nBands = len(X[0,])
    Cov = np.zeros((nBands,nBands))
    for idx in range(ROIdata[names[i]].npts):
        Cov = Cov + np.matmul(ROIdata[names[i]].spectra[idx,].T,ROIdata[names[i]].spectra[idx,])

    #read the data
    for i in range(1,len(names)):
        X = np.vstack((X,ROIdata[names[i]].spectra))
        y = np.hstack((y,np.zeros(ROIdata[names[i]].npts)+i))
    return Cov, X, y

def class_data_from_ROIs(ROIdata):

    # prepare the variables to hold the data
    names = list(ROIdata.keys())
    X = ROIdata[names[0]].spectra
    y = np.zeros(ROIdata[names[0]].npts)

    #read the data
    for i in range(1,len(names)):
        X = np.vstack((X,ROIdata[names[i]].spectra))
        y = np.hstack((y,np.zeros(ROIdata[names[i]].npts)+i))

    return X, y

def compute_accuracy(y_pred,y_test):
    nClasses = int(np.max(y_test)+1)
    confusionMatrix = np.zeros([nClasses,nClasses])
    isClass = np.zeros([nClasses,len(y_test)])
    predClass = np.zeros([nClasses,len(y_test)])
    for i in range(nClasses):
        isClass[i,:] = y_test == i
        predClass[i,:] = y_pred == i
    for i in range(nClasses):
        for j in range(nClasses):
            confusionMatrix[i,j] = sum(isClass[i,:]*predClass[j,:])/sum(isClass[i,:])
    accuracy = float(sum(y_test == y_pred))/len(y_test)
    return accuracy, confusionMatrix

def compute_lda_seperation(lda, ROIdata):
    cov = lda
    icov = np.linalg.inv(cov)

    names = list(ROIdata.keys())
    spectra = ROIdata[names[0]].spectra
    means = np.mean(spectra, 0)
    for key in names:
        spectra = ROIdata[key].spectra
        ROIdata[key].mean = np.mean(spectra, 0)

    seperationMatrix = np.zeros((len(names),len(names)))
    for i in range(len(names)):
        for j in range(len(names)):
            mi = ROIdata[names[i]].mean
            mj = ROIdata[names[j]].mean
            seperationMatrix[i,j] = np.sqrt(np.dot(np.dot((mi - mj).T, icov), (mi - mj)))

    return seperationMatrix

def ROI_class_learner(ROIdata, wl, methods):
    # create disctionary to hold the learners
    learners = {}
    validation = {}
    # get the class data
    X, y = class_data_from_ROIs(ROIdata)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)

    # do the classification
    if 'LDA' in methods:
        lda = LinearDiscriminantAnalysis(solver="svd", store_covariance=True, tol = 10^-3)
        y_pred = lda.fit(X_train, y_train).predict(X_test)
        accuracy, confusionMatrix = compute_accuracy(y_pred,y_test)
        learners['LDA'] = lda.fit(X, y)
        seperationMatrix = compute_lda_seperation(learners['LDA'].covariance_, ROIdata)

        # # plot the LDA band importance
        # fig, ax_LDA_BI = plt.subplots()
        # # prepare wavleengths
        # xlabel = 'Wavelength'
        # nBands = len(np.mean(ROIdata[list(ROIdata.keys())[0]].spectra, 0))
        # if len(wl) != nBands:
        #     wl = range(nBands)
        #     xlabel = 'Band Number'
        #
        # for key in ROIdata.keys():
        #     spectra = ROIdata[key].spectra
        #     mean = np.mean(spectra,0)
        #     ax_LDA_BI.plot(wl, mean, label=ROIdata[key].name, color=ROIdata[key].color/255.)
        #
        # # compute band importance
        # lda_bndImp = np.zeros(len(wl))
        # for i in range(len(wl)):
        #     e = np.zeros(len(wl)).reshape(1, -1)
        #     e[0, i] = 1
        #     lda_bndImp[i] = np.linalg.norm(learners['LDA'].transform(e))
        #
        # lda_bndImp = lda_bndImp*(np.max(mean)-np.min(mean))/(np.max(lda_bndImp)-np.min(lda_bndImp))
        # lda_bndImp = lda_bndImp - np.min(lda_bndImp) + np.min(mean)
        # ax_LDA_BI.plot(wl, lda_bndImp, label='RF Band Importance')
        # ax_LDA_BI.legend()
        # ax_LDA_BI.set(xlabel=xlabel, title='Random Forest Band Importance with Class Means')
        # ax_LDA_BI.grid()
        # plt.show()

        validation['LDA'] = {'accuracy':accuracy,  'confusionMatrix':confusionMatrix}
    if 'QDA' in methods:
        qda = QuadraticDiscriminantAnalysis(store_covariance=True)
        y_pred = qda.fit(X_train, y_train).predict(X_test)
        accuracy, confusionMatrix = compute_accuracy(y_pred,y_test)
        learners['QDA'] = qda.fit(X, y)
        validation['QDA'] = {'accuracy':accuracy,  'confusionMatrix':confusionMatrix}
    if 'RF' in methods:
        rf = RandomForestClassifier(n_estimators = 200)
        y_pred = rf.fit(X_train, y_train).predict(X_test)
        accuracy, confusionMatrix = compute_accuracy(y_pred,y_test)
        learners['RF'] = rf.fit(X, y)
        # plot the band importance
        fig, ax_RF_BI = plt.subplots()
        # prepare wavleengths
        xlabel = 'Wavelength'
        if len(wl) != len(rf.feature_importances_):
            wl = range(len(rf.feature_importances_))
            xlabel = 'Band Number'

        for key in ROIdata.keys():
            spectra = ROIdata[key].spectra
            mean = np.mean(spectra,0)
            ax_RF_BI.plot(wl, mean, label=ROIdata[key].name, color=ROIdata[key].color/255.)
        bndImp = rf.feature_importances_
        bndImp = bndImp*(np.max(mean)-np.min(mean))/(np.max(bndImp)-np.min(bndImp))
        bndImp = bndImp - np.min(bndImp) + np.min(mean)
        ax_RF_BI.plot(wl, bndImp, label='RF Band Importance')
        ax_RF_BI.legend()
        ax_RF_BI.set(xlabel=xlabel, title='Random Forest Band Importance with Class Means')
        ax_RF_BI.grid()
        plt.show()

        validation['RF'] = {'accuracy':accuracy,  'confusionMatrix':confusionMatrix}

    #output the accuracy
    for method in methods:
        acc_text = method+' Accuracy: %4.3f' % validation[method]['accuracy']
        print(acc_text)
        print(validation[method]['confusionMatrix'])

    return learners, validation

def dimension_reduction_plots(ROIdata, methods):

    # create the viarable to hold the plot data (currently just a placeholder)
    plot_data = []

    # get the class data
    X, y = class_data_from_ROIs(ROIdata)
    target_names = ROIdata.keys()
    plot_dims = max([2,len(target_names)])

    if 'PCA' in methods:
        pca = PCA(n_components=len(target_names))
        X_r = pca.fit(X).transform(X)

        # Percentage of variance explained for each components
        print('PCA explained variance ratio (first two components): %s'
              % str(pca.explained_variance_ratio_))

        # 2D SCatterplot
        plotWidget = pg.plot(title="PCA 2D Scatterplot")
        for i, target_name in enumerate(target_names):
            # pg.plot(x, y, pen=None, symbol='o')  ## setting pen=None disables line drawing
            plotWidget.plot(X_r[y == i, 0], X_r[y == i, 1], pen=None, symbol='o',
                symbolBrush=(ROIdata[target_name].color[0],ROIdata[target_name].color[1],ROIdata[target_name].color[2]))

        # 3D SCatterplot
        if plot_dims > 2:
            w3d_pca = gl.GLViewWidget()
            w3d_pca.opts['distance'] = 20
            w3d_pca.show()
            w3d_pca.setWindowTitle('PCA 3D Scatterplot')

            # add the axis grid
            g = gl.GLGridItem()
            w3d_pca.addItem(g)

            for i, target_name in enumerate(target_names):
                pos = np.vstack((X_r[y == i, 0], X_r[y == i, 1], X_r[y == i, 2])).T
                color = np.vstack((
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[0],
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[1],
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[2])).T
                sp2 = gl.GLScatterPlotItem(pos=pos, color=color/255.)

                w3d_pca.addItem(sp2)

    if 'LDA' in methods:
        lda = LinearDiscriminantAnalysis(n_components=len(target_names)-1)
        X_r2 = lda.fit(X, y).transform(X)

        # 2D SCatterplot
        plotWidget = pg.plot(title="LDA 2D Scatterplot")
        for i, target_name in enumerate(target_names):
            # pg.plot(x, y, pen=None, symbol='o')  ## setting pen=None disables line drawing
            plotWidget.plot(X_r2[y == i, 0], X_r2[y == i, 1], pen=None, symbol='o',
                symbolBrush=(ROIdata[target_name].color[0],ROIdata[target_name].color[1],ROIdata[target_name].color[2]))

        # 3D SCatterplot
        plot_dims_lda = len(target_names) - 1
        if plot_dims_lda > 2:
            w3d_lda = gl.GLViewWidget()
            w3d_lda.opts['distance'] = np.max(X_r2)
            w3d_lda.show()
            w3d_lda.setWindowTitle('LDA 3D Scatterplot')

            # add the axis grid
            g = gl.GLGridItem()
            w3d_lda.addItem(g)

            for i, target_name in enumerate(target_names):
                pos = np.vstack((X_r2[y == i, 0], X_r2[y == i, 1], X_r2[y == i, 2])).T
                color = np.vstack((
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[0],
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[1],
                    np.ones((pos.shape[0])) * ROIdata[target_name].color[2])).T
                sp2 = gl.GLScatterPlotItem(pos=pos, color=color)

                w3d_lda.addItem(sp2)

        return plot_data

def image_calssification(im_arr, learners):

    # reshape image from 3D to 2D
    [nRows, nCols, nBands] = np.shape(im_arr)
    imlist = np.reshape(im_arr, (nRows * nCols, nBands))

    # create a progress bar dialog
    progressDialog = QProgressDialog("Applying classifiers to image...", "Cancel", 0, len(learners))
    progressDialog.setWindowTitle('Progress')
    progressDialog.setModal(True)
    progressDialog.show()
    progress = 0

    learnerMethods = learners.keys()
    class_results = {}
    prob_results = {}
    # Apply the classification to the image
    for learnerMethod in learnerMethods:
        learner = learners[learnerMethod]
        class_result_1d = learner.predict(imlist)
        class_result_2d = np.reshape(class_result_1d, [nRows, nCols])
        class_results[learnerMethod] = class_result_2d

        try:
            nClasses = len(learners[learnerMethod].classes_)
            prob_result_1d = learner.predict_proba(imlist)
            prob_result_2d = np.reshape(prob_result_1d, [nRows, nCols, nClasses])
            prob_results[learnerMethod] = prob_result_2d
        except:
            pass

        # update progress dialog
        progress += 1
        progressDialog.setValue(progress)
        if progressDialog.wasCanceled():
            return class_results, prob_results, None

    return class_results, prob_results
