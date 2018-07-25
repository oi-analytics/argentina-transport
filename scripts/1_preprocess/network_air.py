"""Copy air network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os

import fiona

from oia.utils import load_config, transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    # from 5/aeropuertos/aeropuerto.shp
    # to network/air_nodes.shp
    # - "air_{}".format(CODIG_IATA) => id
    # - NOMBRE => name
    def transform_node(record):
        record['properties'] = {
            'id': "air_{}".format(record['properties']['CODIG_IATA']),
            'name': record['properties']['NOMBRE'],
            'iata': record['properties']['CODIG_IATA'],
        }
        return record

    node_schema = {
        'geometry': 'Point',
        'properties': [
            ('id', 'str'),
            ('name', 'str'),
            ('iata', 'str'),
        ]
    }

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'aeropuertos', 'aeropuerto.shp'),
        sink_file=os.path.join(data_path, 'network', 'air_nodes.shp'),
        sink_schema=node_schema,
        transform_record=transform_node
    )

    # from 5/PasajerosLargaDistanciaAvionyBus/SIAC2016pax.shp
    # to network/air_edges.shp
    # - "air_{}".format(Cod_Orig) => from_id
    # - "air_{}".format(Cod_Dest) => to_id
    # to usage/air_passenger.csv
    # - "air_{}".format(Cod_Orig) => from_id
    # - "air_{}".format(Cod_Dest) => to_id
    # - Pax_2016 => passengers_2016
    def transform_edge(record):
        record['properties'] = {
            'id': "air_{}-{}".format(
                record['properties']['Cod_Orig'], record['properties']['Cod_Dest']),
            'from_id': "air_{}".format(
                record['properties']['Cod_Orig']),
            'to_id': "air_{}".format(
                record['properties']['Cod_Dest']),
            'from_iata': record['properties']['Cod_Orig'],
            'to_iata': record['properties']['Cod_Dest'],
        }
        return record

    edge_schema = {
        'geometry': 'LineString',
        'properties': [
            ('id', 'str'),
            ('from_id', 'str'),
            ('from_iata', 'str'),
            ('to_id', 'str'),
            ('to_iata', 'str'),
        ]
    }
    edge_input_file = os.path.join(
        incoming_data_path, '5', 'PasajerosLargaDistanciaAvionyBus', 'SIAC2016pax.shp')
    transform_geo_file(
        source_file=edge_input_file,
        sink_file=os.path.join(data_path, 'network', 'air_edges.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge
    )


    with fiona.open(edge_input_file) as source:
        with open(os.path.join(data_path, 'usage', 'air_passenger.csv'), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(('id', 'from_id', 'to_id', 'from_iata', 'to_iata', 'passengers_2016'))
            for record in source:
                props = record['properties']
                row = (
                    "air_{}-{}".format(props['Cod_Orig'], props['Cod_Dest']),
                    "air_{}".format(props['Cod_Orig']),
                    "air_{}".format(props['Cod_Dest']),
                    props['Cod_Orig'],
                    props['Cod_Dest'],
                    int(props['Pax_2016'])
                )
                w.writerow(row)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
