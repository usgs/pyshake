#!/usr/bin/env python

import os.path
import pytest

import numpy as np
from shapely.geometry import Point

homedir = os.path.dirname(os.path.abspath(__file__))
shakedir = os.path.abspath(os.path.join(homedir, '..', '..'))

from shakemap.utils.layers import (get_layer_distances,
                                   dist_to_layer,
                                   get_probability,
                                   get_subduction_probabilities,
                                   get_tectonic_regions)

from shakemap.utils.config import get_data_path


def layers_equal(layer1, layer2):
    assert sorted(layer1.keys()) == sorted(layer2.keys())
    assert np.allclose(sorted(layer1.values()), sorted(layer2.values()))


def test_layers():
    data_path = get_data_path()
    layer_path = os.path.join(data_path, 'layers')

    elon = -117.0
    elat = 33.0
    layer_distances = get_layer_distances(elon, elat, layer_path)
    reference = {'induced': 1578.3879076203307,
                 'japan': 7972.1138613743387,
                 'taiwan': 11022.339157753582,
                 'california': 0.0}
    layers_equal(layer_distances, reference)

    elon = -97.5
    elat = 36.5
    layer_distances = get_layer_distances(elon, elat, layer_path)
    reference = {'induced': 0.0,
                 'japan': 8935.9779110700729,
                 'taiwan': 11997.837464370788,
                 'california': 1508.2155746648657}
    layers_equal(layer_distances, reference)

    elon = 121.0
    elat = 22.5
    layer_distances = get_layer_distances(elon, elat, layer_path)
    reference = {'induced': 12041.424518656486,
                 'japan': 1231.8954391427453,
                 'taiwan': 0.0,
                 'california': 10085.281293655946}
    layers_equal(layer_distances, reference)

    #
    # Test for geometry type exception in dist_to_layer by
    # handing it a Point rather than a Polygon or MultiPolygon
    #
    p = Point()
    with pytest.raises(TypeError):
        distance = dist_to_layer(0.0, 0.0, p)

def test_get_probability():
    x1 = 0.0
    p1 = 0.9
    x2 = 20.0
    p2 = 0.1

    # test maximum probability
    y1 = get_probability(0.0,x1,p1,x2,p2)
    assert y1 == 0.9

    # test minimum probability
    y2 = get_probability(20.0,x1,p1,x2,p2)
    assert y2 == 0.1

    # make sure that minimum probability is a floor
    y3 = get_probability(40.0,x1,p1,x2,p2)
    assert y3 == 0.1

    # test probability function
    y4 = get_probability(10.0,x1,p1,x2,p2)
    np.testing.assert_almost_equal(y4,0.5)

def test_get_subduction_probabilities():
    # we don't have slab depth or kagan angle, but we're crustal
    results = {'SlabModelDepth':np.nan,
               'TectonicSubtype':'ACR',
               'KaganAngle':np.nan,
               'SlabModelDepthUncertainty':np.nan,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,0.0)
    assert crustal == 0.8
    assert interface == 0.1
    assert intraslab == 0.1

    # we don't have slab depth or kagan angle, but we're interface
    results['TectonicSubtype'] = 'SZInter'
    crustal,interface,intraslab = get_subduction_probabilities(results,20.0)
    assert crustal == 0.1
    assert interface == 0.8
    assert intraslab == 0.1

    # we don't have slab depth or kagan angle, but we're intraslab
    results['TectonicSubtype'] = 'SZIntra'
    crustal,interface,intraslab = get_subduction_probabilities(results,100.0)
    assert crustal == 0.1
    assert interface == 0.1
    assert intraslab == 0.8

    # we do have slab depth, no kagan angle, and RS mechanism
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':np.nan,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'RS'}
    crustal,interface,intraslab = get_subduction_probabilities(results,20.0)
    np.testing.assert_almost_equal(crustal,0.1625)
    np.testing.assert_almost_equal(interface,0.675)
    np.testing.assert_almost_equal(intraslab,0.1625)

    # we do have slab depth, no kagan angle, and non-RS mechanism
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':np.nan,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,20.0)
    np.testing.assert_almost_equal(crustal,0.275)
    np.testing.assert_almost_equal(interface,0.45)
    np.testing.assert_almost_equal(intraslab,0.275)

    # we have slab depth and kagan angle
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':0.0,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,20.0)
    np.testing.assert_almost_equal(crustal,0.05)
    np.testing.assert_almost_equal(interface,0.9)
    np.testing.assert_almost_equal(intraslab,0.05)

    # we have slab depth and kagan angle, not right on the slab
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':0.0,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,10.0)
    np.testing.assert_almost_equal(crustal,0.25)
    np.testing.assert_almost_equal(interface,0.5)
    np.testing.assert_almost_equal(intraslab,0.25)

    # we have slab depth and kagan angle, on the slab but kagan = 30
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':30.0,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,20.0)
    np.testing.assert_almost_equal(crustal,0.2525)
    np.testing.assert_almost_equal(interface,0.495)
    np.testing.assert_almost_equal(intraslab,0.2525)

    # we have slab depth and kagan angle, off the slab and kagan = 30
    results = {'SlabModelDepth':20.0,
               'TectonicSubtype':'ACR',
               'KaganAngle':30.0,
               'SlabModelDepthUncertainty':10.0,
               'TensorType':'composite',
               'FocalMechanism':'ALL'}
    crustal,interface,intraslab = get_subduction_probabilities(results,10.0)
    np.testing.assert_almost_equal(crustal,0.3625,decimal=4)
    np.testing.assert_almost_equal(interface,0.275,decimal=4)
    np.testing.assert_almost_equal(intraslab,0.3625,decimal=4)

    

    
    
    
        
if __name__ == '__main__':
    test_layers()
    test_get_probability()
    test_get_subduction_probabilities()
