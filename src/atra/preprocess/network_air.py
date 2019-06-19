"""Copy air network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os

import fiona

from atra.utils import load_config, transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    # from 5/aeropuertos/aeropuerto.shp
    # to network/air_nodes.shp
    # - "air_{}".format(CODIG_IATA) => id
    # - NOMBRE => name
    def transform_node(record):
        record['properties'] = {
            'node_id': "air_{}".format(record['properties']['local']),
            'name': record['properties']['denominacion'],
            'iata': record['properties']['local'],
        }
        return record

    node_schema = {
        'geometry': 'Point',
        'properties': [
            ('node_id', 'str'),
            ('name', 'str'),
            ('iata', 'str'),
        ]
    }

    transform_geo_file(
        source_file=os.path.join(incoming_data_path,'pre_processed_network_data',
                                    'air', 
                                    'observ-_3.4.4.1.5_aerodromos_anac_2018.view.gml'),
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
    # TODO fix origin and destination ids - they all use three-letter codes but DO NOT MATCH
    # the IATA codes used for nodes
    def transform_edge(record):
        orig_props = record['properties']
        record['properties'] = {
            'edge_id': "air_{}-{}".format(
                record['properties']['Cod_Orig'], record['properties']['Cod_Dest']),
            'from_node': "air_{}".format(
                record['properties']['Cod_Orig']),
            'to_node': "air_{}".format(
                record['properties']['Cod_Dest']),
            'from_iata': record['properties']['Cod_Orig'],
            'to_iata': record['properties']['Cod_Dest'],
        }
        if record['properties']['edge_id'] == 'air_BAR-MDP' and orig_props['Long'] == 898:
            print("Correcting", orig_props)
            record['properties']['edge_id'] = 'air_MDP-DRY'
            record['properties']['from_node'] = 'air_MDP'
            record['properties']['from_iata'] = 'MDP'
            record['properties']['to_node'] = 'air_DRY'
            record['properties']['to_iata'] = 'DRY'

        return record

    edge_schema = {
        'geometry': 'LineString',
        'properties': [
            ('edge_id', 'str'),
            ('from_node', 'str'),
            ('from_iata', 'str'),
            ('to_node', 'str'),
            ('to_iata', 'str'),
        ]
    }
    edge_input_file = os.path.join(
        incoming_data_path, 'pre_processed_network_data','air', 'SIAC2016pax.shp')
    transform_geo_file(
        source_file=edge_input_file,
        sink_file=os.path.join(data_path, 'network', 'air_edges.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge
    )


    with fiona.open(edge_input_file) as source:
        with open(os.path.join(data_path, 'usage', 'air_passenger.csv'), 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(('edge_id', 'from_node', 'to_node', 'from_iata', 'to_iata', 'passengers'))
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
                if props['Cod_Orig'] == 'BAR' and props['Cod_Dest'] == 'MDP' and props['Long'] == 898:
                    print("Correcting", props)
                    row = (
                        'air_MDP-DRY',
                        'air_MDP',
                        'MDP',
                        'air_DRY',
                        'DRY',
                        int(props['Pax_2016'])
                    )
                w.writerow(row)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
