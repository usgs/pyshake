"""
Parse STREC output and create/select a GMPE set for an event.
"""
# stdlib imports
import os.path
import pprint
import shutil
from collections import OrderedDict

# third party imports
import numpy as np
from configobj import ConfigObj
from validate import ValidateError

# local imports
from .base import CoreModule
import shakemap.utils.config as cfg
from shakemap.utils.layers import get_layer_distances, get_tectonic_regions
from shakelib.rupture.origin import Origin


class SelectModule(CoreModule):
    """
    select - Parse STREC output, make a GMPE set, create model_zc.conf.
    """

    command_name = 'select'

    def execute(self):
        '''
        Parses the output of STREC in accordance with the
        configuration file, creates a new GMPE set specific to the event,
        and writes model_zc.conf in the event's 'current' directory.

        Configuration file: select.conf

        Raises:
            NotADirectoryError -- the event's current directory doesn't exist
            FileNotFoundError -- the event.xml file doesn't exist
            ValidateError -- problems with the configuration file
            RuntimeError -- various problems matching the event to a gmpe set
        '''

        # ---------------------------------------------------------------------
        # Get the install and data paths and verify that the even directory
        # exists
        # ---------------------------------------------------------------------
        install_path, data_path = cfg.get_config_paths()
        datadir = os.path.join(data_path, self._eventid, 'current')
        if not os.path.isdir(datadir):
            raise NotADirectoryError('%s is not a valid directory' % datadir)
        # ---------------------------------------------------------------------
        # Open event.xml and make an Origin object
        # ---------------------------------------------------------------------
        eventxml = os.path.join(datadir, 'event.xml')
        if not os.path.isfile(eventxml):
            raise FileNotFoundError('%s does not exist.' % eventxml)
        org = Origin.fromFile(eventxml)

        #
        # Clear away results from previous runs
        #
        products_path = os.path.join(datadir, 'products')
        if os.path.isdir(products_path):
            shutil.rmtree(products_path, ignore_errors=True)

        # ---------------------------------------------------------------------
        # Get config file from install_path/config, parse and
        # validate it
        # ---------------------------------------------------------------------
        config = ConfigObj(os.path.join(install_path, 'config', 'select.conf'))
        validate_config(config, install_path)
        # ---------------------------------------------------------------------
        # Get the strec results
        # ---------------------------------------------------------------------
        strec_out = get_tectonic_regions(org.lon, org.lat, org.depth,
                                         self._eventid,config)
        # ---------------------------------------------------------------------
        # Get the default weighting for this event
        # ---------------------------------------------------------------------
        cfg_tr = config['tectonic_regions']
        str_tr = strec_out['tectonic_regions']
        gmpe_list, weight_list, region_weights = get_gmpes_by_region(str_tr, cfg_tr, org)

        # ---------------------------------------------------------------------
        # Now look at the geographic layers to see if we need to modify or
        # replace the gmpe list
        # ---------------------------------------------------------------------
        #
        # Find the first configured layer the event is within (if any) or the
        # closest layer
        #
        min_dist_to_layer = 999999.9
        nearest_layer_name = None
        if 'layers' in config and 'layer_dir' in config['layers']:
            layer_dir = config['layers']['layer_dir']
            if layer_dir and layer_dir != 'None':
                geo_layers = get_layer_distances(org.lon, org.lat, layer_dir)
            else:
                geo_layers = {}
            for layer in config['layers']:
                if layer == 'layer_dir':
                    continue
                if layer not in geo_layers:
                    self.logger.warning('Error: cannot find layer %s in %s' %
                                        (layer, layer_dir))
                    continue
                ldist = geo_layers[layer]
                if ldist < min_dist_to_layer:
                    min_dist_to_layer = ldist
                    nearest_layer_name = layer
                    if min_dist_to_layer == 0:
                        break
        #
        # If we are in or near a geographic layer, update the gmpe and weight
        # lists
        #
        if nearest_layer_name is not None and \
           (min_dist_to_layer == 0 or
            min_dist_to_layer <=
                config['layers'][nearest_layer_name]['horizontal_buffer']):

            lcfg = config['layers'][nearest_layer_name]
            #
            # Overwrite the tectonic regions with the layer's custom region
            # settings
            #
            for thing in lcfg:
                if thing == 'horizontal_buffer':
                    layer_buff = lcfg[thing]
                    continue
                layer = thing
                for element in lcfg[layer]:
                    cfg_tr[layer][element] = lcfg[layer][element]
            #
            # Now get the gmpes and weights for the custom layer
            #
            layer_gmpes, layer_weights, region_weights = get_gmpes_by_region(
                str_tr, cfg_tr, org)
            if layer_buff == 0:
                #
                # If we're here, min_dist_to_layer must be 0,
                # so the weight is 1
                #
                lwgt = 1.0
            else:
                lwgt = 1.0 - min_dist_to_layer / layer_buff
            #
            # If we're inside the region's boundaries, we just use the custom
            # gmpe and weights. If we are outside the region (but still inside
            # the buffer), we blend the custom gmpe and weights with the
            # generic ones we computed earlier.
            #
            if min_dist_to_layer == 0:
                gmpe_list = layer_gmpes
                weight_list = layer_weights
            else:
                gmpe_list = np.append(gmpe_list, layer_gmpes)
                weight_list = np.append(weight_list * (1.0 - lwgt),
                                        layer_weights * lwgt)
        # ---------------------------------------------------------------------
        # Create ConfigObj object for output to model_zc.conf
        # ---------------------------------------------------------------------
        zc_file = os.path.join(datadir, 'model_zc.conf')
        zc_conf = ConfigObj(indent_type='    ')
        zc_conf.filename = zc_file
        #
        # Add the new gmpe set to the object
        #
        gmpe_set = 'gmpe_' + str(self._eventid) + '_custom'
        zc_conf['gmpe_sets'] = OrderedDict([
            (gmpe_set, OrderedDict([
                ('gmpes', list(gmpe_list)),
                ('weights', list(weight_list)),
                ('weights_larage_dist', 'None'),
                ('dist_cutoff', 'nan'),
                ('site_gmpes', 'None'),
                ('weights_site_gmpes', 'None')
            ]))
        ])
        #
        # Set gmpe to use the new gmpe set
        #
        zc_conf['modeling'] = OrderedDict([
            ('gmpe', gmpe_set),
            ('mechanism', strec_out['focal_mech'])
        ])

        zc_conf.write()


        
# ##########################################################################
# We can't use normal ConfigObj validation because there are
# inconsistent sub-section structures (i.e., acr, scr, and volcanic
# vs. subduction. There are also optional sections with variable
# structure (i.e., the layers). So we do our validation and variable
# conversion here.
# ##########################################################################


def validate_config(mydict, install_path):

    for key in mydict:
        if isinstance(mydict[key], dict):
            validate_config(mydict[key], install_path)
            continue
        if key == 'horizontal_buffer' or key == 'vertical_buffer':
            mydict[key] = cfg.cfg_float(mydict[key])
        elif key == 'gmpe':
            mydict[key] = cfg.gmpe_list(mydict[key], 1)
        elif key == 'min_depth' or key == 'max_depth':
            mydict[key] = cfg.cfg_float_list(mydict[key])
        elif key == 'layer_dir':
            mydict[key] = mydict[key].replace('<INSTALL_DIR>', install_path)
        elif key in  ('x1','x2','p1','p2','p_kagan_default'):
            mydict[key] = float(mydict[key])
        else:
            raise ValidateError('Invalid entry in config: "%s"' % (key))
    return

# ##########################################################################
# Produce a weighted list of GMPE sets based on the earthquake's presence
# in and proximity to the various tectonic regions.
# ##########################################################################

def get_region_weights(strec_tr, cfg,origin):
    regions = {}
    for region in strec_tr:
        reg_dist = strec_tr[region]['distance']
        if region == 'subduction':
            region_weight = 1.0
            gmpes,weights = get_gmpes_from_probs(origin.depth,
                                                 strec_tr[region],
                                                 cfg)
            regions[region] = {'region_weight' : region_weight,
                               'gmpes' : gmpes,
                               'weights' : weights}
        else:
            region_buffer = cfg[region]['horizontal_buffer']
            region_weight = 1.0 - reg_dist / region_buffer
            gmpes, weights = get_gmpes_from_depth(origin.depth, cfg[region])
            regions[region] = {'region_weight' : region_weight,
                               'gmpes' : gmpes,
                               'weights' : weights}
            
        
    return regions, gmpes, weights

def get_gmpes_by_region(strec_tr, cfg, origin):

    gmpe_list = np.array([])
    gmpe_weights = np.array([])
    total_weight = 0
    region_weights = {}
    for reg in strec_tr:
        if reg not in cfg:
            raise RuntimeError('error: unknown tectonic_region: "%s"' % (reg))
        reg_dist = strec_tr[reg]['distance']
        if reg == 'subduction':
            reg_buff = reg_dist
        else:
            reg_buff = cfg[reg]['horizontal_buffer']
        if reg_dist > reg_buff:
            continue
        if reg == 'subduction':
            gmpes, weights = get_gmpes_from_probs(origin.depth,
                                                  strec_tr[reg],
                                                  cfg)
        else:
            gmpes, weights = get_gmpes_from_depth(origin.depth, cfg[reg])
        gmpe_list = np.append(gmpe_list, gmpes)
        if reg_buff:
            reg_weight = 1.0 - reg_dist / reg_buff
        else:
            reg_weight = 1.0
        gmpe_weights = np.append(gmpe_weights, weights * reg_weight)
        total_weight += reg_weight
        region_weights[reg] = reg_weight

    if np.size(gmpe_list) < 1:
        raise RuntimeError('error: no valid tectonic_region:\n%s',
                           pprint.pformat(strec_tr))

    gmpe_weights /= total_weight

    return gmpe_list, gmpe_weights, region_weights

# ##########################################################################
# Produce a GMPE list and weights for subduction events based on the
# probabilities of subduction type.
# ##########################################################################


def get_gmpes_from_probs(depth, sreg, cfg):

    cr_prob = sreg['probabilities']['crustal']
    if_prob = sreg['probabilities']['interface']
    is_prob = sreg['probabilities']['intraslab']
    gmpe_list = np.array([])
    gmpe_weights = np.array([])
    if cr_prob == 0 and if_prob == 0 and is_prob == 0:
        return gmpe_list, gmpe_weights

    if cr_prob > 0:
        gmpe_list = np.append(gmpe_list, cfg['subduction']['crustal']['gmpe'])
        gmpe_weights = np.append(gmpe_weights, cr_prob)
    if if_prob > 0:
        gmpe_list = np.append(gmpe_list, cfg['subduction']['interface']['gmpe'])
        gmpe_weights = np.append(gmpe_weights, if_prob)
    if is_prob > 0:
        gmpe_list = np.append(gmpe_list, cfg['subduction']['intraslab']['gmpe'])
        gmpe_weights = np.append(gmpe_weights, is_prob)

    return gmpe_list, gmpe_weights


# ##########################################################################
# Produce a GMPE list and weights for non-subduction events based on the
# depth of the earthquake.
# ##########################################################################
def get_gmpes_from_depth(depth, region):
    gmpe_list = np.array([])
    gmpe_weights = np.array([])
    vbuf = region['vertical_buffer']
    for ig, gmpe in enumerate(region['gmpe']):
        if depth >= region['min_depth'][ig] and depth <= region['max_depth'][ig]:
            gmpe_list = np.append(gmpe_list, gmpe)
            gmpe_weights = np.append(gmpe_weights, 1.0)
            continue
        if depth > (region['min_depth'][ig] - vbuf) and depth < region['min_depth'][ig]:
            gmpe_list = np.append(gmpe_list, gmpe)
            wgt = 1.0 - (region['min_depth'][ig] - depth) / vbuf
            gmpe_weights = np.append(gmpe_weights, wgt)
            continue
        if depth < (region['max_depth'][ig] + vbuf) and depth > region['max_depth'][ig]:
            gmpe_list = np.append(gmpe_list, gmpe)
            wgt = 1.0 - (depth - region['max_depth'][ig]) / vbuf
            gmpe_weights = np.append(gmpe_weights, wgt)
            continue

    if np.size(gmpe_list) < 1:
        raise RuntimeError('error: no valid gmpe for depth %f; region:\n%s' %
                           (depth, pprint.pformat(region)))

    gmpe_weights /= np.sum(gmpe_weights)
    return gmpe_list, gmpe_weights
