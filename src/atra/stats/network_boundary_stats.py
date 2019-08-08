"""Summarise length of edges/number of nodes within each boundary (commune, district, province)

Purpose
-------

Collect network attributes
    - Combine with boundary Polygons to collect network-boundary intersection attributes
    - Write final results to an Excel sheet

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of networks with attributes:
    - edge_id or node_id - String/Integer/Float Edge ID or Node ID of network
    - length - Float length of edge intersecting with hazards
    - geometry - Shapely geometry of edges as LineString or nodes as Points

3. Shapefile of administrative boundaries of Argentina with attributes:
    - province_i - String/Integer ID of Province
    - pro_name_e - String name of Province in English
    - district_i - String/Integer ID of District
    - dis_name_e - String name of District in English
    - commune_id - String/Integer ID of Commune
    - name_eng - String name of Commune in English
    - geometry - Shapely geometry of boundary Polygon

Results
-------

1. Excel sheet of network-hazard-boundary intersection with attributes:
    - edge_id/node_id - String name of intersecting edge ID or node ID
    - length - Float length of intersection of edge LineString and hazard Polygon: Only for edges
    - province_id - String/Integer ID of Province
    - province_name - String name of Province in English
    - district_id - String/Integer ID of District
    - district_name - String name of District in English
    - commune_id - String/Integer ID of Commune
    - commune_name - String name of Commune in English
"""
import itertools
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from atra.utils import *
from atra.transport_flow_and_failure_functions import *
from tqdm import tqdm

def main():
    """Summarise

    1. Specify the paths from where you to read and write:
        - Input data
        - Intermediate calcuations data
        - Output results

    2. Supply input data and parameters
        - Names of the three Provinces - List of string types
        - Names of modes - List of strings
        - Names of output modes - List of strings
        - Names of hazard bands - List of integers
        - Names of hazard thresholds - List of integers
        - Condition 'Yes' or 'No' is the users wants to process results

    3. Give the paths to the input data files:
        - Commune boundary and stats data shapefile
        - String name of sheet in hazard datasets description Excel file

    4. Specify the output files and paths to be created
    """
    tqdm.pandas()
    incoming_data_path,data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road', 'rail','bridge', 'air', 'port']
    modes_id_cols = ['edge_id','edge_id','bridge_id','node_id','node_id']

    # Give the paths to the input data files
    # load provinces and get geometry of the right province
    print('* Reading provinces dataframe')
    province_path = os.path.join(incoming_data_path,
                                    'admin_boundaries_and_census',
                                    'provincia','Provincias.shp')
    provinces = gpd.read_file(province_path,encoding='utf-8')
    provinces = provinces.to_crs({'init': 'epsg:4326'})
    provinces.rename(columns={'OBJECTID':'province_id','nombre':'province_name','Geometry':'geom_type'},inplace=True)
    sindex_provinces = provinces.sindex

    '''Assign provinces to zones
    '''
    print('* Reading department dataframe')
    zones_path = os.path.join(incoming_data_path, 'admin_boundaries_and_census',,
                                'departamento', 'Departamentos.shp')
    zones = gpd.read_file(zones_path,encoding='utf-8')
    zones = zones.to_crs({'init': 'epsg:4326'})
    zones.rename(columns={'OBJECTID':'department_id','Name':'department_name','Geometry':'geom_type'},inplace=True)

    zones['geometry_centroid'] = zones.geometry.centroid
    zones_centriods = zones[['department_id','department_name','geometry_centroid']]
    zones_centriods.rename(columns={'geometry_centroid':'geometry'},inplace=True)
    zone_matches = gpd.sjoin(zones_centriods,provinces[['province_id','province_name','geometry']], how="inner", op='within').reset_index()
    no_zones = [x for x in zones['department_id'].tolist() if x not in zone_matches['department_id'].tolist()]

    zones.drop('geometry_centroid',axis=1,inplace=True)
    if no_zones:
        remain_zones = zones[zones['department_id'].isin(no_zones)]
        remain_zones['province_name'] = remain_zones.progress_apply(lambda x: extract_value_from_gdf(
            x, sindex_provinces, provinces,'province_name'), axis=1)
        remain_zones['province_id'] = remain_zones.progress_apply(lambda x: extract_value_from_gdf(
            x, sindex_provinces, provinces,'province_id'), axis=1)

        zone_matches = pd.concat([zone_matches,remain_zones],axis=0,sort='False', ignore_index=True)

    zones = pd.merge(zones,zone_matches[['department_id','province_id','province_name']],how='left',on=['department_id'])


    # Specify the output files and paths to be created
    output_dir = os.path.join(output_path, 'network_stats')
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)


    # Process national scale results
    data_excel = os.path.join(
        output_dir,'national_scale_boundary_stats.xlsx')
    nat_excel_writer = pd.ExcelWriter(data_excel)
    for m in range(len(modes)):
        if modes[m] in ['road','rail','bridge']:
            ntype = 'edges'
            network_shp = os.path.join(
                data_path,
                'network',
                '{}_edges.shp'.format(modes[m]))
        else:
            ntype = 'nodes'
            network_shp = os.path.join(
                data_path,
                'network',
                '{}_nodes.shp'.format(modes[m]))

        data_dict = []
        data_dict = spatial_scenario_selection(
                        network_shp, zones, {}, data_dict,
                        modes_id_cols[m],
                        network_type = ntype)
        data_df = pd.DataFrame(data_dict)

        data_df.to_excel(nat_excel_writer, modes[m], index=False)
        nat_excel_writer.save()
        del data_df




if __name__ == "__main__":
    main()
