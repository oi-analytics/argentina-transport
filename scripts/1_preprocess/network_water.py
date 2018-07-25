"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import os

from oia.utils import load_config, transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    # from 5/Puertos/puertos.shp
    # to network/water_nodes.shp
    # - "water_{}".format(ID) => id
    # - PUERTO => name
    # - transporte => port_type
    #   - inland > inland
    #   - puertos > sea
    node_schema = {
        'geometry': 'Point',
        'properties': [
            ('id', 'str'),
            ('name', 'str'),
        ]
    }

    def transform_node(record):
        record['properties'] = {
            'id': "water_{}".format(record['properties']['ID']),
            'name': record['properties']['PUERTO'],
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'Puertos', 'puertos.shp'),
        sink_file=os.path.join(data_path, 'network', 'water_nodes.shp'),
        sink_schema=node_schema,
        transform_record=transform_node
    )

    # from 5/Hidrovia/Hidrovia.shp
    # to network/water_edges.shp
    # - "water_{}".format(UNION) => id
    # - "inland" => waterway_type
    # TODO resolve network connectivity inland
    # TODO construct connections between sea ports
    edge_schema = {
        'geometry': 'LineString',
        'properties': [
            ('id', 'str'),
        ]
    }

    def transform_edge(record):
        record['properties'] = {
            'id': "water_{}".format(record['properties']['UNION']),
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'Hidrovia', 'Hidrovia.shp'),
        sink_file=os.path.join(data_path, 'network', 'water_edges.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge
    )

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
