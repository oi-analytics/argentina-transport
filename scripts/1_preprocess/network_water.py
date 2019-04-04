"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import os

import geopandas as gpd
import pandas as pd

from oia.utils import load_config
from shapely.geometry import Point
from snkit import Network
from snkit.network import (link_nodes_to_nearest_edge, add_ids, add_topology, add_endpoints,
                           split_multilinestrings)

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    # from 5/Puertos/port_od_nodes.csv
    # to network/water_nodes.shp
    # - id => port_id
    # - PUERTO => name
    in_node_file = os.path.join(incoming_data_path, '5', 'Puertos', 'port_od_nodes.csv')
    out_node_file = os.path.join(data_path, 'network', 'water_nodes.shp')
    # from 5/Hidrovia/Hidrovia.shp
    # to network/water_edges.shp
    in_edge_file=os.path.join(incoming_data_path, '5', 'Hidrovia', 'water_edge_basis.shp')
    out_edge_file=os.path.join(data_path, 'network', 'water_edges.shp')


    nodes = pd.read_csv(in_node_file)[
        # ['Puerto', 'Provincia', 'Región', 'Localidad', 'Según la titularidad del Inmueble', 'Modelo de Gestion', 'Según su Destino', 'Latitud Sur', 'Longitud Oeste']
        ['Puerto', 'Provincia', 'Región', 'Localidad', 'Latitud Sur', 'Longitud Oeste']
    ].rename(columns={
        'Puerto': 'name',
        'Provincia': 'province',
        'Región': 'region',
        'Localidad': 'locality',
        'Latitud Sur': 'lat',
        'Longitud Oeste': 'lon'
    })
    nodes = nodes.groupby(['province','region','locality','lat','lon'])['name'].apply(lambda x:'/'.join(x)).reset_index()

    nodes['geometry'] = list(zip(nodes.lon, nodes.lat))
    nodes['geometry'] = nodes['geometry'].apply(Point)
    nodes = gpd.GeoDataFrame(nodes, geometry='geometry').drop(['lat', 'lon'], axis=1)

    edges = gpd.read_file(in_edge_file).drop(['OBJECTID', 'ID'], axis=1)

    network = Network(edges=edges, nodes=nodes)
    network = add_endpoints(split_multilinestrings(network))
    network = link_nodes_to_nearest_edge(network)
    network = add_topology(add_ids(network, edge_prefix='watere', node_prefix='watern'))

    network.edges.to_file(out_edge_file,encoding='utf-8')
    network.nodes.to_file(out_node_file,encoding='utf-8')



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
