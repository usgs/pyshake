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

def nearest_edge(elon, elat, poly):
    """
    Return the distance from a point to the nearest edge of a
    polygon.

    Args:
        elon (float): The longitude of the reference point.
        elat (float): The latitude of the reference point.
        poly (Polygon): An instance of a shapely Polygon.

    Returns:
        float: The distance (in km) from the reference point to the
        nearest edge (or vertex) of the polygon.
    """
    elon_arr = np.array([elon])
    elat_arr = np.array([elat])
    x, y = poly.exterior.xy
    nearest = 99999.
    for ix in range(1, len(x) - 1):
        dd = min_distance_to_segment(np.array(x[ix - 1:ix + 1]),
                                     np.array(y[ix - 1:ix + 1]),
                                     elon_arr, elat_arr)
        if np.abs(dd[0]) < nearest:
            nearest = dd[0]
    return nearest


def dist_to_layer(elon, elat, geom):
    """
    Return the distance from a point to the polygon(s) in a layer; zero if
    the point is inside the polygon. If the nearest edge of the polygon is
    greater than 5000 km from the point, the point cannot be inside the
    polygon and the distance reported will be the distance to the nearest
    edge. So don't make polygons too big.

    Args:
        elon (float): The longitude of the reference point.
        elat (float): The latitude of the reference point.
        geom (Polygon or MultiPolygon): An instance of a shapely Polygon
            or MultiPolygon.

    Returns:
        float: The distance (in km) from the reference point to the
        nearest polygon in the layer. The distance will be zero if the
        point lies inside the polygon.
    """
    if isinstance(geom, Polygon):
        plist = [geom]
    elif isinstance(geom, MultiPolygon):
        plist = list(geom.geoms)
    else:
        raise TypeError('Invalid geometry type in layer: %s' % type(geom))

    project = partial(
        pyproj.transform,
        pyproj.Proj(proj='latlong'),
        pyproj.Proj(proj='aeqd  +lat_0=%f +lon_0=%f +R=6371' % (elat, elon)))
    ep = Point(0.0, 0.0)
    min_dist = 99999.
    for poly in plist:
        nearest = nearest_edge(elon, elat, poly)
        if nearest < 5000:
            nearest = ep.distance(transform(project, poly))
        if nearest < min_dist:
            min_dist = nearest
        if min_dist == 0:
            break
    return min_dist


def get_layer_distances(elon, elat, layer_dir):
    """
    Return the distances from a point to the nearest polygon in each
    layer file found in 'layer_dir'. The distance will be zero if
    the point is inside a polygon. If the nearest edge of a polygon is
    greater than 5000 km from the point, the point cannot be inside the
    polygon and the distance reported will be the distance to the
    nearest edge. So don't make polygons too big.

    The layer files should be written in Well-Known Text (with .wkt
    extensions), and should contain either a single POLYGON or
    MULTIPOLYGON object. The layer name will be the file's basename.

    Args:
        elon (float): The longitude of the reference point.
        elat (float): The latitude of the reference point.
        layer_dir (str): The path to the directory containg the layer
            files.

    Returns:
        dict: A dictionary where the keys are the layer names, and the
        values are the distance (in km) from the reference point to the
        nearest polygon in the layer. The distance will be zero if the
        point lies inside the polygon.
    """
    layer_files = glob.glob(os.path.join(layer_dir, '*.wkt'))
    dist_dict = {}
    for file in layer_files:
        layer_name = os.path.splitext(os.path.basename(file))[0]
        with open(file, 'r') as fd:
            data = fd.read()
        geom = shapely.wkt.loads(data)
        dist_dict[layer_name] = dist_to_layer(elon, elat, geom)
    return dist_dict

def update_config_regions(lat, lon, config):
    min_dist_to_layer = 999999.9
    inside_layer_name = None
    if 'layers' in config and 'layer_dir' in config['layers']:
        layer_dir = config['layers']['layer_dir']
        if layer_dir and layer_dir != 'None':
            geo_layers = get_layer_distances(lon, lat, layer_dir)
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
                if min_dist_to_layer == 0:
                    inside_layer_name = layer
                    break
    if inside_layer_name is None:
        return config
    else:
        layer_config = config['layers'][inside_layer_name]
        for region,rdict in layer_config.items():
            if region == 'horizontal_buffer':
                continue
            config['tectonic_regions'][region] = rdict
    return config
        
