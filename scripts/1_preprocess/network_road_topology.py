"""Load combined_roads and join to form graph topology
"""
import os

import geopandas
import pandas

from fiona.crs import from_epsg
from oia.utils import load_config
from shapely.geometry import Point
from snkit import Network
from snkit.network import (add_endpoints, link_nodes_to_edges_within, nearest_edge,
                           split_edges_at_nodes, add_ids, add_topology, set_precision)
from tqdm import tqdm


def main(config):
    data_path = config['paths']['incoming_data']
    roads_path = os.path.join(data_path, 'pre_processed_data', 'roads', 'combined_roads')
    input_path = os.path.join(roads_path, 'combined_roads_2.shp')

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

    # drop some precision
    tqdm.pandas(desc="drop_precision")
    edges.geometry = edges.geometry.progress_apply(lambda geom: set_precision(geom, 1))

    # split first to national and provincial/rural
    national_edges = edges[edges.road_type == 'national'].copy()
    provincial_rural_edges = edges[edges.road_type != 'national'].copy()

    # create national-provincial network
    network = Network(edges=national_edges)

    # add nodes at endpoints
    network = add_endpoints(network)
    # split at endpoints - generous tolerance
    network = split_edges_at_nodes(network, tolerance=20)

    # add nodes at intersections
    intersection_node_geoms = []
    extra_geoms = []  # ignore LineString intersections
    for edge in tqdm(network.edges.itertuples(index=False), desc="self-int", total=len(network.edges)):
        geom = edge.geometry
        candidate_idxs = list(network.edges.sindex.intersection(geom.bounds))
        candidates = network.edges.iloc[candidate_idxs]
        intersections = candidates.intersection(geom)
        for intersection in intersections:
            geom_type = intersection.geom_type
            if intersection.is_empty:
                continue
            elif geom_type == 'Point':
                intersection_node_geoms.append(intersection)
            elif geom_type == 'MultiPoint':
                for point in intersection.geoms:
                    intersection_node_geoms.append(point)
            elif geom_type == 'LineString':
                start = Point(intersection.coords[0])
                end = Point(intersection.coords[-1])
                extra_geoms.append(start)
                extra_geoms.append(end)
            elif geom_type == 'MultiLineString':
                for line in intersection.geoms:
                    start = Point(line.coords[0])
                    end = Point(line.coords[-1])
                    extra_geoms.append(start)
                    extra_geoms.append(end)
            elif geom_type == 'GeometryCollection':
                for geom in intersection.geoms:
                    if geom.geom_type == 'Point':
                        intersection_node_geoms.append(geom)
                    elif geom.geom_type == 'LineString':
                        start = Point(geom.coords[0])
                        end = Point(geom.coords[-1])
                        extra_geoms.append(start)
                        extra_geoms.append(end)
                    else:
                        print("-",geom.geom_type)
            else:
                print(intersection.geom_type)

    network.nodes = geopandas.GeoDataFrame(intersection_node_geoms, columns=['geometry'])

    # split at intersections - lower tolerance
    network = split_edges_at_nodes(network, tolerance=1)

    # add nodes at any endpoint
    network = add_endpoints(network)
    # add topology
    network = add_topology(add_ids(network, edge_prefix='roade', node_prefix='roadn'))

    # deduplicate almost-equal edges
    def almost_name(edge, edges=None, tolerance=1):
        geom = edge.geometry
        buf = geom.buffer(tolerance)
        candidate_idxs = list(edges.sindex.intersection(buf.bounds))
        candidates = edges.iloc[candidate_idxs]
        names = [edge.road_name]
        for c in candidates.itertuples(index=False):
            if buf.contains(c.geometry):
                names.append(c.road_name)
        return ",".join(sorted(set(names)))

    tqdm.pandas(desc="dedup_prep-name")
    network.edges.road_name = network.edges.progress_apply(almost_name, axis=1, edges=network.edges, tolerance=20)

    def join_from_to(edge):
        return ",".join(sorted([edge.from_id, edge.to_id]))

    tqdm.pandas(desc="dedup_prep-ids")
    network.edges['from_to'] = network.edges.progress_apply(join_from_to, axis=1)

    # drop based on shared road_name and from-to ids
    network.edges.drop_duplicates(subset=['road_name', 'from_to'], keep='first', inplace=True)
    network.edges.drop(columns=['id', 'to_id', 'from_id', 'from_to'], inplace=True)

    # create whole network (ignore nodes from above)
    all_edges = pandas.concat([network.edges, provincial_rural_edges], axis=0)
    initial_network = Network(edges=all_edges)

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

    joined = link_nodes_to_edges_within(
        with_nodes, distance=10, condition=different_types, tolerance=1e-6)

    # COULD
    # - add nodes at line intersections
    # - link nodes to edges of same type within 100m or 10m
    # - merge nodes within buffer (simplify graph)

    # add topology (a_node, b_node) to edges
    with_ids = add_ids(joined, edge_prefix='roade', node_prefix='roadn')
    topological = add_topology(with_ids)

    # COULD add degree to nodes and join 2-degree stretches
    # with_degree = calculate_node_degree(topological)

    network = topological

    # project back to WGS84 lat/lon
    network.set_crs(epsg=epsg_utm_20s)
    epsg_lat_lon = 4326
    network.to_crs(epsg=epsg_lat_lon)

    # write out
    edges_path = os.path.join(roads_path, 'combined_roads_edges.shp')
    network.edges.to_file(edges_path)

    nodes_path = os.path.join(roads_path, 'combined_roads_nodes.shp')
    network.nodes.to_file(nodes_path)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
