#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from sklearn.cluster import KMeans

from CTLungSeg.method import connected_components_wStats
from CTLungSeg.method import erode, dilate
from CTLungSeg.method import gl2bit

__author__  = ['Riccardo Biondi', 'Nico Curti']
__email__   = ['riccardo.biondi4@studio.unibo.it', 'nico.curti2@unibo.it']


def opening(img, kernel):
    """Perform an erosion followed by a dilation

    Parameters
    ----------
    img : array-like
        image tensor
    kernel : array-like
        kernel used for the morphological operations
    """
    opened = erode(img, kernel=kernel)
    return dilate(opened, kernel=kernel)


def closing(img, kernel):
    """Perform a dilation followed by an erosion

    Parameters
    ----------
    img : array-like
        image tensor
    kernel : array-like
        kernel used for the morphological operations
    """
    closed = dilate(img, kernel=kernel)
    return erode(closed, kernel=kernel)


def remove_spots(img, area):
    """Set to zero the GL of all the connected region with area lesser than area

    Parameters
    ----------
    img: array-like
        binary image from which remove spots
    area: int
        maximun area in pixels of the removed spots

    Returns
    -------
    filled: array-like
        binary image with spot removed
    """
    _, lab, stats, _ = connected_components_wStats(img)

    for i,stat in enumerate(stats):
        for j in stat.query('AREA < {}'.format(str(area))).index:
            lab[i][lab[i] == j] = 0
    lab = lab != 0
    return lab.astype(np.uint8)


def select_greater_connected_regions(img, n_reg):
    """Select the n_reg grater connecter regions in each slice of the stack and remove the others. If the image contains less than n_reg regions, no region will be selected.

    Parameters
    ----------
    img : array-like
        Image tensor; better if the images are binary
    n_reg : int
        number of connected regions to select. The background it is not considered as connected regions
    Return
    ------
    dst : array-like
        binary image with only the n_reg connected regions
    """
    m = []
    _, labs , stats, _ = connected_components_wStats(img)
    for stat, lab in zip(stats, labs):
        stat = stat.drop(index = 0)
        stat = stat.sort_values(by = ['AREA'], ascending = False)

        if len(stat.index ) > n_reg-1:
            for i in range(n_reg):
                index  = stat.query('AREA == {}'.format(str(stat.iat[i, 4]))).index
                lab[lab == np.uint8(index)] = 255
            lab[lab != 255] = 0
        else :
            lab[lab != 0] = 0
        m.append(lab)
    return np.asarray(m, dtype = np.uint8)


def reconstruct_gg_areas(mask):
    """This function interpolate each slice of the input mask to reconstruct the missing gg areas.

    Parameter
    ---------
    mask : array-like
        lung mask to reconstruct
    Return
    ------
    reconstructed : array-like
        reconstructed lung mask
    """
    first  = mask.copy()
    second = mask.copy()
    reconstructed = mask.copy()

    for i in range(first.shape[0] -1):
        first[i + 1] = np.bitwise_or(first[i], first[i + 1], dtype=np.uint8)

    for i in reversed(range(1, second.shape[0], 1)):
        second[i - 1] = np.bitwise_or(second[i - 1], second[i], dtype = np.uint8)

    for i in range(reconstructed.shape[0]):
        reconstructed[i] = np.bitwise_and(first[i], second[i], dtype = np.uint8)
    return reconstructed




def find_ROI(stats) :
    """Found the upper and lower corner of the rectangular ROI according to the connected region stats

    Parameter
    ---------
    stats: pandas dataframe
        dataframe that contains the stats of the connected regions

    Return
    ------
    corners: array-like
        array which contains the coordinates of the upper and lower corner of the ROI organized as [x_top, y_top, x_bottom, y_bottom]
    """
    stats = stats.drop([0], axis = 0)
    corner = np.array([stats.min(axis = 0)['LEFT'], stats.min(axis = 0)['TOP'], np.max(stats['LEFT'] + stats['WIDTH']), np.max(stats['TOP'] + stats['HEIGHT'])])
    return np.nan_to_num(corner, copy=False).astype('int16')


def bit_plane_slices(stack, bits):
    """Convert each voxel GL into its 8-bit binary
    rapresentation and return as output the stack
    resulting from the sum of all the bith
    specified in bits, with them significance.

    Parameters
    ----------
    stack : array-like
        image stack. each GL must be an 8-bit unsigned int
    bits: tuple
        tuple that specify which bit sum

    Returns
    -------
    output : array-like
        images stack in which each GL depends only to the significance of each specfied bit
    """
    binary = gl2bit(stack)
    bit = np.asarray(bits)
    selection = binary[8 - bit, ...]
    significance = np.asarray([2**(i - 1) for i in bit]).reshape(3, 1, 1, 1)
    return (np.sum(selection * significance, axis=0)).astype(np.uint8)


def imlabeling(image, centroids) :
    """Return the labeled image given the original image
    tensor and the centroids

    Parameters
    ----------
    image : array-like
    image to label

    centroids : array-like
        Centroids vector for KMeans clustering

    Return
    ------
    labeled : array-like
        Image in which each GL ia assigned on its label.
    """
    to_label = image.reshape((-1,1))
    res = KMeans(n_clusters=centroids.shape[0], init=centroids, n_init=1).fit(to_label)
    return (res.labels_.reshape(image.shape)).astype(np.uint8)
