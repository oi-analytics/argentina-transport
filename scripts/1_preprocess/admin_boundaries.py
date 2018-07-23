"""Copy admin boundaries from `C Incoming Data` to `D Work Processes`
"""
import os

import fiona

from oia.utils import load_config, within_extent
from shapely.geometry import shape

def main(config):
    """Read files, write in reduced data format
    """
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    extent = (-74.039948, -55.262288, -57.387752, -20.295821)
    country_codes = ('ARG', 'CHL', 'BOL', 'PRY', 'BRA', 'URY')

    # load 2/provincia/Provincias.shp
    # to boundaries/admin_1_boundaries.shp
    # keep nombre => name
    with fiona.open(os.path.join(incoming_data_path, '2', 'provincia', 'Provincias.shp')) as source:
        schema = {
            'geometry': 'Polygon',
            'properties': [
                ('name', 'str'),
            ]
        }
        with fiona.open(
                os.path.join(data_path, 'boundaries', 'admin_1_boundaries.shp'),
                'w',
                driver=source.driver,
                crs=source.crs,
                schema=schema) as sink:
            for record in source:
                record['properties'] = {
                    'name': record['properties']['nombre']
                }
                sink.write(record)


    # load AdminBoundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp
    # in list
    # to boundaries/admin_0_boundaries.shp
    # keep ISO_A3, NAME_EN => name
    with fiona.open(os.path.join(incoming_data_path, 'AdminBoundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp')) as source:
        schema = {
            'geometry': 'Polygon',
            'properties': [
                ('name', 'str'),
                ('ISO_A3', 'str'),
            ]
        }
        with fiona.open(
                os.path.join(data_path, 'boundaries', 'admin_0_boundaries.shp'),
                'w',
                driver=source.driver,
                crs=source.crs,
                schema=schema) as sink:
            for record in source:
                iso_a3 = record['properties']['ISO_A3']
                if iso_a3 in country_codes:
                    record['properties'] = {
                        'name': record['properties']['NAME_EN'],
                        'ISO_A3': record['properties']['ISO_A3']
                    }
                    sink.write(record)


    # load AdminBoundaries/ne_10m_lakes/ne_10m_lakes.shp
    # within extent
    # to boundaries/physical_lakes.shp
    # keep name
    with fiona.open(os.path.join(incoming_data_path, 'AdminBoundaries/ne_10m_lakes/ne_10m_lakes.shp')) as source:
        schema = {
            'geometry': 'Polygon',
            'properties': [
                ('name', 'str'),
            ]
        }
        with fiona.open(
                os.path.join(data_path, 'boundaries', 'physical_lakes.shp'),
                'w',
                driver=source.driver,
                crs=source.crs,
                schema=schema) as sink:
            for record in source:
                poly = shape(record['geometry'])
                point = poly.centroid
                if within_extent(point.x, point.y, extent):
                    record['properties'] = {
                        'name': record['properties']['name']
                    }
                    sink.write(record)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
