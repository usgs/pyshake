# stdlib imports
import os.path

# third party imports
from shakelib.utils.containers import ShakeMapOutputContainer
from mapio.gdal import GDALGrid
from configobj import ConfigObj

# local imports
from .base import CoreModule
from shakemap.utils.config import get_config_paths
from shakelib.utils.imt_string import oq_to_file

FORMATS = {
    'shapefile': ('ESRI Shapefile', 'shp'),
    'geojson': ('GeoJSON', 'json')
}

DEFAULT_FILTER_SIZE = 10


class RasterModule(CoreModule):
    """
    raster -- Generate GIS raster files of all configured IMT values from
                    shake_result.hdf.
    """

    command_name = 'raster'

    def execute(self):
        install_path, data_path = get_config_paths()
        datadir = os.path.join(data_path, self._eventid, 'current', 'products')
        datadir = os.path.join(data_path, self._eventid, 'current', 'products')
        if not os.path.isdir(datadir):
            raise NotADirectoryError('%s is not a valid directory.' % datadir)
        datafile = os.path.join(datadir, 'shake_result.hdf')
        if not os.path.isfile(datafile):
            raise FileNotFoundError('%s does not exist.' % datafile)

        # Open the ShakeMapOutputContainer and extract the data
        container = ShakeMapOutputContainer.load(datafile)
        if container.getDataType() != 'grid':
            raise NotImplementedError('raster module can only operate on '
                                      'gridded data, not sets of points')

        # get the path to the products.conf file, load the config
        config_file = os.path.join(install_path, 'config', 'products.conf')
        config = ConfigObj(config_file)

        # create GIS-readable .flt files of imt and uncertainty
        self.logger.info('Creating GIS grids...')
        layers = config['products']['raster']['layers']
        for layer in layers:
            fileimt = oq_to_file(layer)
            imtdict = container.getIMTGrids(layer, 'GREATER_OF_TWO_HORIZONTAL')
            mean_grid = imtdict['mean']
            std_grid = imtdict['std']
            mean_gdal = GDALGrid.copyFromGrid(mean_grid)
            std_gdal = GDALGrid.copyFromGrid(std_grid)
            mean_fname = os.path.join(datadir, '%s_mean.flt' % fileimt)
            std_fname = os.path.join(datadir, '%s_std.flt' % fileimt)
            self.logger.info('Saving %s...' % mean_fname)
            mean_gdal.save(mean_fname)
            self.logger.info('Saving %s...' % std_fname)
            std_gdal.save(std_fname)
