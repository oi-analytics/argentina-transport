"""Summarise network-hazard intersections

Purpose
-------

Collect network-hazard intersection attributes
    - Combine with boundary Polygons to collect network-hazard-boundary intersection attributes
    - Write final results to an Excel sheet

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of network-hazard intersections results with attributes:
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

4. Excel sheet of hazard attributes with attributes:
    - hazard_type - String name of hazard type
    - model - String name of hazard model
    - year - String name of hazard year
    - climate_scenario - String name of hazard scenario
    - probability - Float/String value of hazard probability
    - band_num - Integer value of hazard band
    - min_val - Integer value of minimum value of hazard threshold
    - max_val - Integer value of maximum value of hazard threshold

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
    - sector - String name of transport mode
    - hazard_type - String name of hazard type
    - model - String name of hazard model
    - year - String name of hazard year
    - climate_scenario - String name of hazard scenario
    - probability - Float/String value of hazard probability
    - band_num - Integer value of hazard band
    - min_val - Integer value of minimum value of hazard threshold
    - max_val - Integer value of maximum value of hazard threshold

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


def create_hazard_event_attributes_for_network(intersection_dir,climate_scenario,year,sector,hazard_files,
    hazard_df,thresholds,commune_shape,network_id_column,hazard_event_id,network_type=''):
    """Extract results of network edges/nodes and hazard intersections to collect
    network-hazard intersection attributes

        - Combine with boundary Polygons to collect network-hazard-boundary intersection attributes
        - Write final results to an Excel sheet

    Parameters
    ----------
    intersection_dir : str
        Path to Directory where the network-hazard shapefile results are stored
    sector : str
        name of transport mode
    hazard_files : list[str]
        names of all hazard files
    hazard_df : pandas.DataFrame
        hazard attributes
    bands : list[int]
        integer values of hazard bands
    thresholds : list[int]
        integer values of hazard thresholds
    commune_shape
        Shapefile of commune boundaries and attributes
    network_type : str, optional
        value -'edges' or 'nodes': Default = 'nodes'
    name_province : str, optional
        name of province if needed: Default = ''

    Returns
    -------
    data_df : pandas.DataFrame
        network-hazard-boundary intersection attributes:
            - edge_id/node_id - String name of intersecting edge ID or node ID
            - length - Float length of intersection of edge LineString and hazard Polygon: Only for edges
            - province_id - String/Integer ID of Province
            - province_name - String name of Province in English
            - district_id - String/Integer ID of District
            - district_name - String name of District in English
            - commune_id - String/Integer ID of Commune
            - commune_name - String name of Commune in English
            - sector - String name of transport mode
            - hazard_type - String name of hazard type
            - model - String name of hazard model
            - year - String name of hazard year
            - climate_scenario - String name of hazard scenario
            - probability - Float/String value of hazard probability
            - band_num - Integer value of hazard band
            - min_val - Integer value of minimum value of hazard threshold
            - max_val - Integer value of maximum value of hazard threshold
            - length - Float length of intersection of edge LineString and hazard Polygon: Only for edges

    """
    data_dict = []
    for root, dirs, files in os.walk(intersection_dir):
        for file in files:
            if file.endswith(".shp"):
                hazard_dict = {}
                hazard_dict['event_id'] = hazard_event_id
                hazard_dict['sector'] = sector
                hazard_shp = os.path.join(root, file)
                hz_file = file.split('_')
                hz_file = [hz_file[h-1]+'_'+hz_file[h] for h in range(len(hz_file)) if '1in' in hz_file[h]][0]
                hazard_dict['hazard_type'] = hazard_df.loc[hazard_df.file_name ==
                                                            hz_file].hazard_type.values[0]
                hazard_dict['model'] = hazard_df.loc[hazard_df.file_name ==
                                                        hz_file].model.values[0]
                hazard_dict['year'] = year
                hazard_dict['climate_scenario'] = climate_scenario
                hazard_dict['probability'] = hazard_df.loc[hazard_df.file_name ==
                                                            hz_file].probability.values[0]


                hazard_thrs = [(thresholds[t], thresholds[t+1]) for t in range(len(thresholds)-1)
                                           if '{0}m-{1}m'.format(thresholds[t], thresholds[t+1]) in file][0]
                hazard_dict['min_depth'] = hazard_thrs[0]
                hazard_dict['max_depth'] = hazard_thrs[1]


                data_dict = spatial_scenario_selection(
                            hazard_shp, commune_shape, hazard_dict, data_dict,
                            network_id_column,
                            network_type = network_type)

                print ('Done with file {} in event {}'.format(file,hazard_event_id))

    data_df = pd.DataFrame(data_dict)
    data_df_cols = data_df.columns.values.tolist()
    if 'length' in data_df_cols:
        selected_cols = [cols for cols in data_df_cols if cols != 'length']
        data_df = data_df.groupby(selected_cols)['length'].sum().reset_index()

    return data_df

def main():
    """Collect results

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
        - Hazard datasets description Excel file
        - String name of sheet in hazard datasets description Excel file
    """
    tqdm.pandas()
    incoming_data_path,data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road', 'rail','bridge', 'air', 'water']
    modes_id_cols = ['edge_id','edge_id','bridge_id','node_id','node_id']
    thresholds = [1, 2, 3, 4, 999]
    national_results = 'Yes'
    climate_scenarios = ['Baseline','Future_Med','Future_High']
    years = [2016,2050,2050]

    '''Assign provinces to zones
    '''
    print('* Reading department dataframe')
    zones_path = os.path.join(incoming_data_path, '2',
                                'departamento', 'Departamentos.shp')
    zones = gpd.read_file(zones_path,encoding='utf-8')
    zones = zones.to_crs({'init': 'epsg:4326'})
    zones.rename(columns={'OBJECTID':'department_id','Name':'department_name','Geometry':'geom_type'},inplace=True)
    sindex_zones = zones.sindex

    print('* Reading event dataframe')
    events_path = os.path.join(data_path, 'flood_data',
                                'Darthmouth_events', 'darthmouth_event_set_arg.shp')
    events = gpd.read_file(events_path,encoding='utf-8')
    events = events.to_crs({'init': 'epsg:4326'})

    # Specify the output files and paths to be created
    output_dir = os.path.join(output_path, 'hazard_scenarios')
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)

    # Process national scale results
    if national_results == 'Yes':
        print ('* Processing national scale results')
        for m in range(len(modes)):
            mode_df = pd.read_excel(os.path.join(output_dir,'national_scale_hazard_intersections.xlsx'),sheet_name=modes[m],encoding='utf-8-sig')
            mode_data_df = []
            event_set = []
            for event_idx,event_val in events.iterrows():
                intersected_zones = zones.iloc[list(sindex_zones.intersection(event_val['geometry'].bounds))].reset_index()
                intersected_zones = intersected_zones[['department_id']]
                intersected_zones['event_id'] = [event_val['id']]*len(intersected_zones.index)
                intersected_zones = pd.merge(intersected_zones,mode_df,how='left',on=['department_id']).fillna(0)
                intersected_zones = intersected_zones[intersected_zones[modes_id_cols[m]] != 0]

                event_df = intersected_zones[[modes_id_cols[m],'event_id','climate_scenario','probability']].set_index(['event_id','climate_scenario','probability'])
                events_select = list(set(event_df.index.values.tolist()))
                for e in events_select:
                    event_desc = '{}_1in{}_{}'.format(e[0],int(1.0/e[2]),e[1])
                    event_mode_ids = list(set(event_df.loc[[e],modes_id_cols[m]].values.tolist()))
                    # print (event_mode_ids)
                    event_set += list(zip([event_desc]*len(event_mode_ids),event_mode_ids))
                    # print (event_set)

                mode_data_df.append(intersected_zones)
                print ('* Done with event {} for {}'.format(event_val['id'],modes[m]))
            mode_data_df = pd.concat(mode_data_df,axis=0,sort='False', ignore_index=True)
            mode_data_df = mode_data_df[mode_data_df[modes_id_cols[m]] != 0]
            mode_data_df.to_csv(os.path.join(output_dir,'{}_event_intersections.csv'.format(modes[m])),index=False,encoding='utf-8-sig')
            '''Create events
            '''
            # event_df = mode_data_df[[modes_id_cols[m],'event_id','climate_scenario','probability']].set_index(['event_id','climate_scenario','probability'])
            # events = list(set(event_df.index.values.tolist()))
            # event_set = []
            # for e in events:
            #     event_desc = '{}_1in{}_{}'.format(e[0],int(1.0/e[2]),e[1])
            #     event_set.append((event_desc,list(set(event_df.loc[[e],modes_id_cols[m]].values.tolist()))))

            event_set = pd.DataFrame(event_set,columns=['event_id',modes_id_cols[m]])
            event_set.to_csv(os.path.join(output_dir,'{}_event_set.csv'.format(modes[m])),index=False,encoding='utf-8-sig')
            del mode_data_df, event_set




if __name__ == "__main__":
    main()
