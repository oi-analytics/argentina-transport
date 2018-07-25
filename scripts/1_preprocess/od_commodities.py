"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os

import fiona

from oia.utils import load_config,  transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    # from 5/Lineas de deseo OD- 2014/3.6.1.10.zonas/ZonasSHP.shp
    # to boundaries/economic_od_zones.shp
    # - DATA => id
    # - PROV => admin_1_shortcode
    # - PROVINCIA => admin_1_shortname
    zone_schema = {
        'geometry': 'Polygon',
        'properties': [
            ('id', 'str'),
            ('admin_1_shortcode', 'str'),
            ('admin_1_shortname', 'str'),
        ]
    }

    def transform_zone(record):
        record['properties'] = {
            'id': "econ_{}".format(record['properties']['DATA']),
            'admin_1_shortcode': record['properties']['PROV'],
            'admin_1_shortname': record['properties']['PROVINCIA'],
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'Lineas de deseo OD- 2014', '3.6.1.10.zonas', 'ZonasSHP.shp'),
        sink_file=os.path.join(data_path, 'boundaries', 'economic_od_zones.shp'),
        sink_schema=zone_schema,
        transform_record=transform_zone
    )

    # from 5/Lineas de deseo OD- 2014/3.6.1.2.centroides/Centroides.shp
    # to boundaries/economic_od_centroids.shp
    # - DATA => id
    # - ZONA => admin_1_shortcode
    centroid_schema = {
        'geometry': 'Point',
        'properties': [
            ('id', 'str'),
            ('admin_1_shortcode', 'str'),
        ]
    }

    def transform_centroid(record):
        record['properties'] = {
            'id': "econ_{}".format(record['properties']['DATA']),
            'admin_1_shortcode': record['properties']['ZONA'],
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'Lineas de deseo OD- 2014', '3.6.1.2.centroides', 'Centroides.shp'),
        sink_file=os.path.join(data_path, 'boundaries', 'economic_od_centroids.shp'),
        sink_schema=centroid_schema,
        transform_record=transform_centroid
    )

    # from 5/Lineas de deseo OD- 2014/3.6.1.1.carnestotal/CarnesTotal.shp
    # - meat
    # from 5/Lineas de deseo OD- 2014/3.6.1.3.combustiblestotal/CombustiblesTotal.shp
    # - fuel
    # from 5/Lineas de deseo OD- 2014/3.6.1.4.granostotal/GranosTotal.shp
    # - grain
    # from 5/Lineas de deseo OD- 2014/3.6.1.5.industrializadostotal/IndustrializadosTotal.shp
    # - industrial
    # from 5/Lineas de deseo OD- 2014/3.6.1.6.mineriatotal/MineriaTotal.shp
    # - mining
    # from 5/Lineas de deseo OD- 2014/3.6.1.7.regionalestotal/RegionalesTotal.shp
    # - regional
    # from 5/Lineas de deseo OD- 2014/3.6.1.8.semiterminadostotal/SemiterminadosTotal.shp
    # - semi-finished
    # FILA > a_id
    # COLUMNA > b_id
    # AB > a_to_b
    # BA > b_to_a
    od_path = os.path.join(incoming_data_path, '5', 'Lineas de deseo OD- 2014')
    od_paths = {
        'meat': os.path.join(
            od_path, '3.6.1.1.carnestotal', 'CarnesTotal.shp'),
        'fuel': os.path.join(
            od_path, '3.6.1.3.combustiblestotal', 'CombustiblesTotal.shp'),
        'grain': os.path.join(
            od_path, '3.6.1.4.granostotal', 'GranosTotal.shp'),
        'industrial': os.path.join(
            od_path, '3.6.1.5.industrializadostotal', 'IndustrializadosTotal.shp'),
        'mining': os.path.join(
            od_path, '3.6.1.6.mineriatotal', 'MineriaTotal.shp'),
        'regional': os.path.join(
            od_path, '3.6.1.7.regionalestotal', 'RegionalesTotal.shp'),
        'semi-finished': os.path.join(
            od_path, '3.6.1.8.semiterminadostotal', 'SemiterminadosTotal.shp'),
    }
    with open(os.path.join(data_path, 'usage', 'economic_od.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(('from_zone', 'to_zone', 'sector', 'value'))
        for sector, path in od_paths.items():
            with fiona.open(path) as source:
                for record in source:
                    props = record['properties']
                    a_id = props['FILA']
                    b_id = props['COLUMNA']
                    a_to_b = props['AB']
                    b_to_a = props['BA']
                    # from row to column
                    w.writerow((a_id, b_id, sector, a_to_b))
                    # from column to row
                    w.writerow((b_id, a_id, sector, b_to_a))


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
