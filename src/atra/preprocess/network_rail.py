"""Copy rail network from `C Incoming Data` to `D Work Processes`
"""
import os

from shapely.geometry import shape, mapping

from atra.utils import load_config, transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    # from 5/estaciones/ffcc.shp
    # to network/rail_nodes.shp
    # - "rail_{}".format(id) => id
    # - nombre => name
    # - linea => line
    # TODO reduce or filter out stations?
    def transform_node(record):
        geom = shape(record['geometry'])
        # assume all multipoints have just one point, else raise error
        if len(geom.geoms) > 1:
            print(len(geom.geoms))
            print(record['properties']['id'])
            raise ValueError
        record['geometry'] = mapping(geom.geoms[0])
        record['properties'] = {
            'id': "rail_{}".format(record['properties']['id']),
            'name': record['properties']['nombre'],
            'line': record['properties']['linea'],
        }
        return record

    node_schema = {
        'geometry': 'Point',
        'properties': [
            ('id', 'str'),
            ('name', 'str'),
            ('line', 'str'),
        ]
    }

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'estaciones', 'ffcc.shp'),
        sink_file=os.path.join(data_path, 'network', 'rail_nodes.shp'),
        sink_schema=node_schema,
        transform_record=transform_node
    )

    # from 5/Red_ffcc/lineas_ffcc.shp
    # to network/rail_edges.shp
    # - "rail_{}".format(ID) => id
    # - OPERADOR => operator
    # - LINAE => line
    # TODO split edges at stations, add to_id, from_id
    def transform_edge(record):
        record['properties'] = {
            'id': "rail_{}".format(record['properties']['ID']),
            'operator': record['properties']['OPERADOR'],
            'line': record['properties']['LINEA'],
        }
        return record

    edge_schema = {
        'geometry': 'LineString',
        'properties': [
            ('id', 'str'),
            ('operator', 'str'),
            ('line', 'str'),
        ]
    }

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'Red_ffcc', 'lineas_ffcc.shp'),
        sink_file=os.path.join(data_path, 'network', 'rail_edges.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge
    )

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
