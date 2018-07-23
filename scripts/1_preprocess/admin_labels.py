"""Generate labels from `C Incoming Data` to `D Work Processes`
"""
import csv
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
    # to boundaries/region_labels.csv
    # keep nombre => name
    with fiona.open(os.path.join(incoming_data_path, '2', 'provincia', 'Provincias.shp')) as source:
        with open(os.path.join(data_path, 'boundaries', 'region_labels.csv'), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(('text', 'lon', 'lat', 'size'))
            for record in source:
                poly = shape(record['geometry'])
                point = poly.centroid
                name = record['properties']['nombre']
                w.writerow((name, point.x, point.y, 8))


    # load AdminBoundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp
    # in list
    # to boundaries/region_labels.csv
    # keep ISO_A3, NAME_EN => name
    with fiona.open(os.path.join(incoming_data_path, 'AdminBoundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp')) as source:
        with open(os.path.join(data_path, 'boundaries', 'labels.csv'), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(('text', 'lon', 'lat', 'size'))
            for record in source:
                iso_a3 = record['properties']['ISO_A3']
                if iso_a3 in country_codes:
                    poly = shape(record['geometry'])
                    point = poly.centroid
                    name = record['properties']['NAME_EN']
                    w.writerow((name, point.x, point.y, 10))


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
