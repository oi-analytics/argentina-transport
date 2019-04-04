
"""Intersect networks with hazards

Purpose
-------

Intersect hazards and network line and point geometries with hazatd polygons

Write final results to Shapefiles

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of network edges or nodes with attributes:
    - edge_id or node_id - String/Integer/Float Edge ID or Node ID of network
    - geometry - Shapely geometry of edges as LineStrings or nodes as Points

3. Shapefile of hazards with attributes:
    - geometry - Shapely geometry of hazard Polygon

Results
-------

1. Edge shapefiles with attributes:
    - edge_id - String name of intersecting edge ID
    - length - Float length of intersection of edge LineString and hazard Polygon
    - geometry - Shapely LineString geometry of intersection of edge LineString and hazard Polygon

2. Node Shapefile with attributes:
    - node_id - String name of intersecting node ID
    - geometry - Shapely Point geometry of intersecting node ID

"""
import itertools
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from oia.utils import *


def networkedge_hazard_intersection(edge_shapefile, hazard_shapefile, output_shapefile,edge_id_column):
    """Intersect network edges and hazards and write results to shapefiles

    Parameters
    ----------
    edge_shapefile
        Shapefile of network LineStrings
    hazard_shapefile
        Shapefile of hazard Polygons
    output_shapefile
        String name of edge-hazard shapefile for storing results


    Outputs
    -------
    output_shapefile
        - edge_id - String name of intersecting edge ID
        - length - Float length of intersection of edge LineString and hazard Polygon
        - geometry - Shapely LineString geometry of intersection of edge LineString and hazard Polygon
    """
    print ('* Starting {} and {} intersections'.format(edge_shapefile,hazard_shapefile))
    line_gpd = gpd.read_file(edge_shapefile)
    poly_gpd = gpd.read_file(hazard_shapefile)

    if len(line_gpd.index) > 0 and len(poly_gpd.index) > 0:
        line_gpd.columns = map(str.lower, line_gpd.columns)
        poly_gpd.columns = map(str.lower, poly_gpd.columns)

        line_bounding_box = line_gpd.total_bounds
        line_bounding_box_coord = list(itertools.product([line_bounding_box[0], line_bounding_box[2]], [
                                       line_bounding_box[1], line_bounding_box[3]]))
        line_bounding_box_geom = Polygon(line_bounding_box_coord)
        line_bounding_box_gpd = gpd.GeoDataFrame(pd.DataFrame(
            [[1], [line_bounding_box_geom]]).T, crs='epsg:4326')
        line_bounding_box_gpd.columns = ['ID', 'geometry']

        poly_bounding_box = poly_gpd.total_bounds
        poly_bounding_box_coord = list(itertools.product([poly_bounding_box[0], poly_bounding_box[2]], [
                                       poly_bounding_box[1], poly_bounding_box[3]]))
        poly_bounding_box_geom = Polygon(poly_bounding_box_coord)
        poly_bounding_box_gpd = gpd.GeoDataFrame(pd.DataFrame(
            [[1], [poly_bounding_box_geom]]).T, crs='epsg:4326')
        poly_bounding_box_gpd.columns = ['ID', 'geometry']

        poly_sindex = poly_bounding_box_gpd.sindex

        selected_polys = poly_bounding_box_gpd.iloc[list(
            poly_sindex.intersection(line_bounding_box_gpd['geometry'].iloc[0].bounds))]
        if len(selected_polys.index) > 0:
            data = []
            poly_sindex = poly_gpd.sindex
            for l_index, lines in line_gpd.iterrows():
                intersected_polys = poly_gpd.iloc[list(
                    poly_sindex.intersection(lines.geometry.bounds))]
                for p_index, poly in intersected_polys.iterrows():
                    if (lines['geometry'].intersects(poly['geometry']) is True) and (poly.geometry.is_valid is True):
                        if line_length(lines['geometry']) > 1e-3:
                            data.append({edge_id_column: lines[edge_id_column], 'length': 1000.0*line_length(lines['geometry'].intersection(
                                poly['geometry'])), 'geometry': lines['geometry'].intersection(poly['geometry'])})
                        else:
                            data.append({edge_id_column: lines[edge_id_column], 'length': 0, 'geometry': lines['geometry']})
            if data:
                intersections_data = gpd.GeoDataFrame(
                    data, columns=[edge_id_column, 'length', 'geometry'], crs='epsg:4326')
                intersections_data.to_file(output_shapefile)

                del intersections_data

    del line_gpd, poly_gpd


def networknode_hazard_intersection(node_shapefile, hazard_shapefile, output_shapefile,node_id_column):
    """Intersect network nodes and hazards and write results to shapefiles

    Parameters
    ----------
    node_shapefile
        Shapefile of network Points
    hazard_shapefile
        Shapefile of hazard Polygons
    output_shapefile
        String name of node-hazard shapefile for storing results


    Outputs
    -------
    output_shapefile
        - node_id - String name of intersecting node ID
        - geometry - Shapely Point geometry of intersecting node ID
    """
    print ('* Starting {} and {} intersections'.format(node_shapefile,hazard_shapefile))
    point_gpd = gpd.read_file(node_shapefile)
    point_gpd.rename(columns={'id':node_id_column},inplace=True)
    poly_gpd = gpd.read_file(hazard_shapefile)

    if len(point_gpd.index) > 0 and len(poly_gpd.index) > 0:
        point_gpd.columns = map(str.lower, point_gpd.columns)
        poly_gpd.columns = map(str.lower, poly_gpd.columns)
        data = []
        # create spatial index
        poly_sindex = poly_gpd.sindex
        for pt_index, points in point_gpd.iterrows():
            intersected_polys = poly_gpd.iloc[list(
                poly_sindex.intersection(points.geometry.bounds))]
            if len(intersected_polys.index) > 0:
                data.append({node_id_column: points[node_id_column], 'geometry': points['geometry']})
        if data:
            intersections_data = gpd.GeoDataFrame(
                data, columns=[node_id_column, 'geometry'], crs='epsg:4326')
            intersections_data.to_file(output_shapefile)

            del intersections_data

    del point_gpd, poly_gpd

def intersect_networks_and_all_hazards(hazard_dir,network_file_path,network_file_name,output_file_path,network_id_column,network_type = ''):
    """Walk through all hazard files and select network-hazard intersection criteria

    Parameters
    ----------
    hazard_dir : str
        name of directory where all hazard shapefiles are stored
    network_file_path : str
        name of directory where network shapefile is stored
    network_file_name : str
        name network shapefile
    output_file_path : str
        name of directory where network-hazard instersection result shapefiles will be stored
    network_type : str
        values of 'edges' or 'nodes'


    Outputs
    -------
    Edge or Node shapefiles

    """
    for root, dirs, files in os.walk(hazard_dir):
        for file in files:
            if file.endswith(".shp"):
                hazard_file = os.path.join(root, file)
                out_shp_name = network_file_name[:-4] + '_' + file
                output_file = os.path.join(output_file_path,out_shp_name)
                if network_type == 'edges':
                    networkedge_hazard_intersection(network_file_path, hazard_file, output_file,network_id_column)
                elif network_type == 'nodes':
                    networknode_hazard_intersection(network_file_path, hazard_file, output_file,network_id_column)


def main():
    """Intersect networks with hazards

    1. Specify the paths from where you to read and write:
        - Input data
        - Intermediate calcuations data
        - Output results

    2. Supply input data and parameters
        - Names of the three Provinces - List of string types
        - Paths of the mode files - List of tuples of strings
        - Names of modes - List of strings
        - Names of output modes - List of strings
        - Condition 'Yes' or 'No' is the users wants to process results

    3. Give the paths to the input data files:
        - Hazard directory
    """
    data_path, calc_path, output_path = load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road', 'rail','bridge', 'air', 'water']
    modes_id_cols = ['edge_id','edge_id','bridge_id','node_id','node_id']
    climate_scenarios = ['Baseline','Future_Med','Future_High']
    national_results = 'Yes'

    for sc in climate_scenarios:
	    # Give the paths to the input data files
	    hazard_dir = os.path.join(data_path,'flood_data','FATHOM',sc)

	    # Specify the output files and paths to be created
	    output_dir = os.path.join(output_path, 'networks_hazards_intersection_shapefiles')
	    if not os.path.exists(output_dir):
	        os.mkdir(output_dir)

	    if national_results == 'Yes':
	        for m in range(len(modes)):
	            if modes[m] in ['road', 'rail','bridge']:
	                edges_in = os.path.join(data_path,'network','{}_edges.shp'.format(modes[m]))
	                edges_name = '{}_edges'.format(modes[m])

	                output_dir = os.path.join(output_path, 'networks_hazards_intersection_shapefiles','{}_hazard_intersections'.format(modes[m]))
	                if os.path.exists(output_dir) == False:
	                    os.mkdir(output_dir)

	                output_dir = os.path.join(output_path, 'networks_hazards_intersection_shapefiles','{}_hazard_intersections'.format(modes[m]),sc)
	                if os.path.exists(output_dir) == False:
	                    os.mkdir(output_dir)

	                print ('* Starting national {} and all hazards intersections'.format(modes[m]))
	                intersect_networks_and_all_hazards(hazard_dir,edges_in,edges_name,output_dir,modes_id_cols[m],network_type = 'edges')

	            elif modes[m] in ['air', 'water']:
	                nodes_in = os.path.join(data_path,'network','{}_nodes.shp'.format(modes[m]))
	                nodes_name = '{}_nodes'.format(modes[m])

	                output_dir = os.path.join(output_path, 'networks_hazards_intersection_shapefiles','{}_hazard_intersections'.format(modes[m]))
	                if os.path.exists(output_dir) == False:
	                    os.mkdir(output_dir)

	                output_dir = os.path.join(output_path, 'networks_hazards_intersection_shapefiles','{}_hazard_intersections'.format(modes[m]),sc)
	                if os.path.exists(output_dir) == False:
	                    os.mkdir(output_dir)

	                print ('* Starting national {} and all hazards intersections'.format(modes[m]))
	                intersect_networks_and_all_hazards(hazard_dir,nodes_in,nodes_name,output_dir,modes_id_cols[m],network_type = 'nodes')


if __name__ == "__main__":
    main()
