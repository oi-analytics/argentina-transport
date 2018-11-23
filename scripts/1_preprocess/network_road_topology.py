"""Load combined_roads and join to form graph topology
"""
import os

import geopandas
import pandas

from fiona.crs import from_epsg
from oia.utils import load_config
from snkit import Network
from snkit.network import (add_endpoints, link_nodes_to_edges_within, nearest_edge,
                           split_edges_at_nodes, add_ids, add_topology, set_precision)
from tqdm import tqdm


def main(config):
    data_path = config['paths']['incoming_data']
    roads_path = os.path.join(data_path, 'pre_processed_data', 'roads', 'combined_roads')
    input_path = os.path.join(roads_path, 'combined_roads.shp')

    edges = geopandas.read_file(input_path)
    edges = edges[edges.geometry.notnull()]

    # Project to UTM zone 20S, so distances are in metres
    epsg_utm_20s = 32720
    edges = edges.to_crs(epsg=epsg_utm_20s)

    # split multilinestrings
    simple_edge_attrs = []
    simple_edge_geoms = []
    for edge in tqdm(edges.itertuples(index=False), desc="simplify", total=len(edges)):
        if edge.geometry.geom_type == 'MultiLineString':
            edge_parts = list(edge.geometry)
        else:
            edge_parts = [edge.geometry]

        for part in edge_parts:
            simple_edge_geoms.append(part)

        attrs = geopandas.GeoDataFrame([edge] * len(edge_parts))
        simple_edge_attrs.append(attrs)

    simple_edge_geoms = geopandas.GeoDataFrame(simple_edge_geoms, columns=['geometry'])
    edges = pandas.concat(simple_edge_attrs, axis=0).reset_index(drop=True).drop('geometry', axis=1)
    edges = pandas.concat([edges, simple_edge_geoms], axis=1)

    # create initial network
    initial_network = Network(edges=edges)

    # drop some precision
    tqdm.pandas(desc="drop_precision")
    initial_network.edges.geometry = initial_network.edges.geometry.progress_apply(
        lambda geom: set_precision(geom, 1))

    # add nodes at endpoints
    with_nodes = add_endpoints(initial_network)

    # assign road type to nodes
    tqdm.pandas(desc="assign_road_type")
    def nearest_edge_road_type(node):
        edge = nearest_edge(node.geometry, edges)
        return edge.road_type

    with_nodes.nodes['road_type'] = with_nodes.nodes.progress_apply(nearest_edge_road_type, axis=1)

    # join nodes to any edge within buffer up to 100m, if of different road_type
    def different_types(node, edge):
        return node.road_type != edge.road_type

    joined = link_nodes_to_edges_within(with_nodes, distance=100, condition=different_types)

    # COULD
    # - add nodes at line intersections
    # - link nodes to edges of same type within 100m or 10m

    # COULD merge nodes within buffer (simplify graph)
    # merged = merge_nodes_within(joined, distance=10)

    # add topology (a_node, b_node) to edges
    topological = add_topology(add_ids(joined, edge_prefix='roade', node_prefix='roadn'))

    # COULD add degree to nodes
    # with_degree = calculate_node_degree(topological)

    network = topological

    # project back to WGS84 lat/lon
    edges_path = os.path.join(roads_path, 'combined_roads_edges.shp')
    network.edges.to_file(edges_path)

    nodes_path = os.path.join(roads_path, 'combined_roads_nodes.shp')
    network.nodes.to_file(nodes_path)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
