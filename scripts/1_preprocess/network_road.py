"""Copy road network from `C Incoming Data` to `D Work Processes`
"""
import os

from atra.utils import load_config, transform_geo_file

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    # from 5/RutasNacionaes/Rutas_nacionales.shp
    # - "road_{}".format(gid) => id
    # - nombre => name
    # - "national" => jurisdiction
    # - "unknown" => surface
    # to network/road_edges.shp
    edge_schema = {
        'geometry': 'LineString',
        'properties': [
            ('id', 'str'),
            ('name', 'str'),
            ('jurisdiction', 'str'),
            ('surface', 'str'),
        ]
    }

    def transform_edge_national(record):
        record['properties'] = {
            'id': "road_{}".format(record['properties']['gid']),
            'name': record['properties']['nombre'],
            'jurisdiction': 'national',
            'surface': 'unknown',
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'RutasNacionaes', 'Rutas_nacionales.shp'),
        sink_file=os.path.join(data_path, 'network', 'road_edges_national.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge_national
    )

    # from 5/RutasProvinciales/Rutas_provinciales.shp
    # - "road_{}".format(union) => id
    # - nombre => name
    # - "provincial" => jurisdiction
    # - clase => surface
    #   - DE TIERRA > earth
    #   - CONSOLIDADO > consolidated gravel
    #   - PAVIMENTADO > paved
    #   - PAVIMENTADO EN CONSTRUCC > paved (under construction)
    def transform_edge_provincial(record):
        # translate surface type
        surfaces = {
            'DE TIERRA': 'earth',
            'CONSOLIDADO': 'consolidated gravel',
            'PAVIMENTADO': 'paved',
            'PAVIMENTADO EN CONSTRUCC': 'paved (under construction)',
        }
        if record['properties']['clase'] in surfaces:
            surface = surfaces[record['properties']['clase']]
        else:
            # fall back to passing through unchanged
            surface = record['properties']['clase']

        record['properties'] = {
            'id': "road_{}".format(record['properties']['union']),
            'name': record['properties']['nombre'],
            'jurisdiction': 'provincial',
            'surface': surface,
        }
        return record

    transform_geo_file(
        source_file=os.path.join(incoming_data_path, '5', 'RutasProvinciales', 'Rutas_provinciales.shp'),
        sink_file=os.path.join(data_path, 'network', 'road_edges_provincial.shp'),
        sink_schema=edge_schema,
        transform_record=transform_edge_provincial
    )


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
