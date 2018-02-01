import re
import glob
import os.path
from functools import partial

# third party imports
import pyproj
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import transform
import shapely.wkt
import numpy as np
from openquake.hazardlib.geo.geodetic import min_distance_to_segment
from strec.subtype import SubductionSelector

def get_weights(origin, config, tensor_params):
    """Get list of GMPEs and their weights for a given earthquake.

    Args:
        origin (Origin object): ShakeMap Origin object, containing earthquake info.
        config (dict-like): Configuration information regarding earthquake type.
        tensor_params (dict): Containing fields NP1/NP2, each a dict with strike/dip/rake.
    Returns:
        list: String GMPEs selected for this earthquake.
        ndarray: Float weights for corresponding GMPEs.
        Series: Pandas series containing STREC output.
    """
    tprobs, strec_results = get_probs(origin, config,
                                     tensor_params)
    gmpelist = []
    weightlist = []
    

    # remove all probabilities that are == 0
    probs = {}
    for key,value in tprobs.items():
        if value > 0.0:
            probs[key] = value
    all_keylist = list(probs.keys())
    
    for region,rdict in config['tectonic_regions'].items():
        if region == 'subduction':
            if 'crustal' in probs:
                gmpelist += rdict['crustal']['gmpe']
                weightlist.append(probs['crustal'])
            if 'interface' in probs:
                gmpelist += rdict['interface']['gmpe']
                weightlist.append(probs['interface'])
            if 'intraslab' in probs:
                gmpelist += rdict['intraslab']['gmpe']
                weightlist.append(probs['intraslab'])
        else:
            pat = re.compile(region+'_')
            keylist = sorted(list(filter(pat.search,all_keylist)))
            if len(keylist):
                gmpelist += rdict['gmpe']
                for key in keylist:
                    weightlist.append(probs[key])

    weightlist = np.array(weightlist)
    return gmpelist,weightlist,strec_results

def get_probs(origin, config, tensor_params):
    """Calculate probabilities for each earthquake type.

    The results here contain probabilities that can be rolled up in many ways:
      - The probabilities of acr,scr,volcanic, and subduction should sum to 1.
      - The probabilities of acr_X,scr_X,volcanic_X, crustal, interface and intraslab 
        should sum to 1.
      - The probabilities of acr_X should sum to acr, and so on.

    Args:
        origin (Origin object): ShakeMap Origin object, containing earthquake info.
        config (dict-like): Configuration information regarding earthquake type.
        tensor_params (dict): Containing fields NP1/NP2, each a dict with strike/dip/rake.
    Returns:
        dict: Probabilities for each earthquake type, with fields:
              - acr Probability that the earthquake is in an active region.
              - acr_X Probability that the earthquake is in a depth layer of ACR, 
                      starting from the top.
              - scr Probability that the earthquake is in a stable region.
              - scr_X Probability that the earthquake is in a depth layer of SCR, 
                      starting from the top.
              - volcanic Probability that the earthquake is in a volcanic region.
              - volcanic_X Probability that the earthquake is in a depth layer of 
                           Volcanic, starting from the top.
              - subduction Probability that the earthquake is in a subduction zone.
              - crustal Probability that the earthquake is in the crust above an interface.
              - interface Probability that the earthquake is on the interface.
              - intraslab Probability that the earthquake is in the slab below interface.

    """
    selector = SubductionSelector()
    lat,lon,depth,mag = origin.lat,origin.lon,origin.depth,origin.mag
    eid = origin.eventsourcecode
    strec_results = selector.getSubductionType(lat, lon, depth,
                                              tensor_params=tensor_params)
    region_probs = get_region_probs(eid, depth, strec_results, config)
    in_subduction = strec_results['TectonicRegion'] == 'Subduction'
    above_slab = not np.isnan(strec_results['SlabModelDepth'])
    if in_subduction:
        subduction_probs = get_subduction_probs(strec_results, depth, mag, config,
                                                above_slab)
        for key,value in subduction_probs.items():
            subduction_probs[key] = value*region_probs['subduction']
    else:
        subduction_probs = {'crustal':0.0,
                            'interface':0.0,
                            'intraslab':0.0}
        
    region_probs.update(subduction_probs)
    return (region_probs,strec_results)

def get_region_probs(eid, depth, strec_results, config):
    """Calculate the regional probabilities (not including subduction interface etc).

    Args:
        eid (str): Earthquake ID (i.e., us1000cdn0)
        depth (float): Depth of earthquake.
        strec_results (Series): Pandas series containing STREC output.
        config (dict-like): Configuration information regarding earthquake type.
    Returns:
        dict: Probabilities for each earthquake type, with fields:
              - acr Probability that the earthquake is in an active region.
              - acr_X Probability that the earthquake is in a depth layer of ACR, 
                      starting from the top.
              - scr Probability that the earthquake is in a stable region.
              - scr_X Probability that the earthquake is in a depth layer of SCR, 
                      starting from the top.
              - volcanic Probability that the earthquake is in a volcanic region.
              - volcanic_X Probability that the earthquake is in a depth layer of 
                           Volcanic, starting from the top.
              - subduction Probability that the earthquake is in a subduction zone.

    """
    region_probs = {}
    region_mapping = {'scr':'DistanceToStable',
                      'acr':'DistanceToActive',
                      'volcanic':'DistanceToVolcanic',
                      'subduction':'DistanceToSubduction'}
    layer_probs = {}
    for region,rdict in config['tectonic_regions'].items():
        distance = strec_results[region_mapping[region]]
        # If we're considering subduction zones but not IN a subduction zone
        x1 = 0.0
        p2 = 0.0
        if region == 'subduction':
            x2 = 100.0 #this doesn't matter
            if distance > 0:
                p1 = 0.0
            else:
                p1 = 1.0
        else:
            p1 = 1.0
            x2 = rdict['horizontal_buffer']
            
        region_prob = get_probability(distance,x1,p1,x2,p2)
        region_probs[region] = region_prob

        if region == 'subduction':
            continue

        region_layer_probs = {}
        #now do the weights for each depth zone
        for i in range(0,len(rdict['min_depth'])):
            x1 = rdict['min_depth'][i]
            p1 = 1.0
            x2 = rdict['max_depth'][i] + rdict['vertical_buffer']
            p2 = 0.0
            p_layer = get_probability(depth,x1,p1,x2,p2)
            region_layer_probs['%s_%i' % (region,i)] = p_layer
        probsum = sum([lp for lp in list(region_layer_probs.values())])
        if probsum > 0:
            for key,value in region_layer_probs.items():
                region_layer_probs[key] = value/probsum

        # running list of all region layer probabilities
        layer_probs.update(region_layer_probs)

    # divide the weights by the total weight
    probsum = sum(list(region_probs.values()))
    for region,prob in region_probs.items():
        region_probs[region] = prob/probsum
        pat = re.compile(region)
        layerkeys = list(layer_probs.keys())
        reg_layers = list(filter(pat.search,layerkeys))
        for reg_layer in reg_layers:
            layer_probs[reg_layer] = layer_probs[reg_layer] * region_probs[region]

    region_probs.update(layer_probs)
            
    return region_probs

def get_subduction_probs(strec_results, depth, mag, config,
                         above_slab):
    """Get probabilities of earthquake being crustal, interface or intraslab.

    Args:
        strec_results (Series): Pandas series containing STREC output.
        depth (float): Depth of earthquake.
        mag (float): Earthquake magnitude.
        config (dict-like): Configuration information regarding earthquake type.
        above_slab (bool): Is earthquake above a defined slab?
    Returns:
        dict: Probabilities for each earthquake type, with fields:
              - crustal Probability that the earthquake is in the crust above an interface.
              - interface Probability that the earthquake is on the interface.
              - intraslab Probability that the earthquake is in the slab below interface.

    """
    subcfg = config['subduction']
    if above_slab:
        # the angle between moment tensor and slab
        kagan = strec_results['KaganAngle'] #can be nan

        # Depth to slab
        slab_depth = strec_results['SlabModelDepth']

        # Error in depth to slab
        slab_depth_error = strec_results['SlabModelDepthUncertainty']

        # what is the effective bottom of the interface zone?
        max_interface_depth = strec_results['SlabModelMaximumDepth']

        # Calculate the probability of interface given the
        # (absolute value of) difference between hypocenter and depth to slab.
        dz = np.abs(depth - slab_depth)
        
        x1 = subcfg['p_int_hypo']['x1'] + slab_depth_error
        x2 = subcfg['p_int_hypo']['x2'] + slab_depth_error
        p1 = subcfg['p_int_hypo']['p1']
        p2 = subcfg['p_int_hypo']['p2']
        p_int_hypo = get_probability(dz,x1,p1,x2,p2)

        # Calculate probability of interface given Kagan's angle
        if np.isfinite(kagan):
            x1 = subcfg['p_int_kagan']['x1']
            x2 = subcfg['p_int_kagan']['x2']
            p1 = subcfg['p_int_kagan']['p1']
            p2 = subcfg['p_int_kagan']['p2']
            p_int_kagan = get_probability(kagan,x1,p1,x2,p2)
        else:
            p_int_kagan = subcfg['p_kagan_default']

        # Calculate probability that event occurred above bottom of seismogenic
        # zone, given to us by the Slab model.
        x1 = max_interface_depth + subcfg['p_int_sz']['x1']
        x2 = max_interface_depth + subcfg['p_int_sz']['x2']
        p1 = subcfg['p_int_sz']['p1']
        p2 = subcfg['p_int_sz']['p2']
        p_int_sz = get_probability(depth,x1,p1,x2,p2)

        # Calculate combined probability of interface
        p_int = p_int_hypo * p_int_kagan * p_int_sz
    else:
        slab_depth = subcfg['default_slab_depth']
        # Calculate the probability that an earthquake is interface
        # given magnitude
        x1 = subcfg['p_int_mag']['x1']
        p1 = subcfg['p_int_mag']['p1']
        x2 = subcfg['p_int_mag']['x2']
        p2 = subcfg['p_int_mag']['p2']
        p_int_mag = get_probability(mag, x1, p1, x2, p2)

        # Calculate the probability that the earthquake is
        # interface given depth (two part function).
        # upper portion of function
        x1 = subcfg['p_int_dep_no_slab_upper']['x1']
        p1 = subcfg['p_int_dep_no_slab_upper']['p1']
        x2 = subcfg['p_int_dep_no_slab_upper']['x2']
        p2 = subcfg['p_int_dep_no_slab_upper']['p2']
        p_int_depth_upper = get_probability(depth, x1, p1, x2, p2)

        # lower portion of function
        x1 = subcfg['p_int_dep_no_slab_lower']['x1']
        p1 = subcfg['p_int_dep_no_slab_lower']['p1']
        x2 = subcfg['p_int_dep_no_slab_lower']['x2']
        p2 = subcfg['p_int_dep_no_slab_lower']['p2']
        p_int_depth_lower = get_probability(depth, x1, p1, x2, p2)

        p_int_depth = p_int_depth_upper + p_int_depth_lower

        p_int = p_int_mag * p_int_depth

    # Calculate probability that the earthquake lies above the slab
    # and is thus crustal.
    x1 = subcfg['p_crust_slab']['x1']
    x2 = subcfg['p_crust_slab']['x2']
    p1 = subcfg['p_crust_slab']['p1']
    p2 = subcfg['p_crust_slab']['p2']
    
    p_crust_slab = get_probability((depth-slab_depth),x1,p1,x2,p2)

    # Calculate probability that the earthquake lies within the crust
    x1 = subcfg['p_crust_hypo']['x1']
    x2 = subcfg['p_crust_hypo']['x2']
    p1 = subcfg['p_crust_hypo']['p1']
    p2 = subcfg['p_crust_hypo']['p2']
    p_crust_hypo = get_probability(depth,x1,p1,x2,p2)
    
    # Calculate probability of crustal
    p_crustal = (1 - p_int) * p_crust_slab * p_crust_hypo

    # Calculate probability of intraslab
    p_slab = 1 - (p_int + p_crustal)

    probs = {'crustal' : p_crustal,
             'interface' : p_int,
             'intraslab' : p_slab}
    return probs

def get_probability(x,x1,p1,x2,p2):
    """Calculate probability using a ramped function.

    The subsections and parameters below reflect a series of ramp functions
    we use to calculate various probabilities.
    p1  |----x1
        |     \
        |      \
        |       \
    p2  |        x2------
        |
        ------------------
    
    Args:
        x (float): Quantity for which we want corresponding probability.
        x1 (float): Minimum X value.
        p1 (float): Probability at or below minimum X value.
        x2 (float): Maximum X value.
        p2 (float): Probability at or below maximum X value.
    Returns:
        float: Probability at input x value.
    """
    if x <= x1:
        prob = p1
    elif x >= x2:
        prob = p2
    else:
        slope = (p1-p2)/(x1-x2)
        intercept = p1 - slope * x1
        prob = x * slope + intercept
    return prob

