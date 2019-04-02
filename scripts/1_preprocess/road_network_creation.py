"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import numpy as np
import igraph as ig
import copy
import unidecode
from scipy.spatial import Voronoi
from shapely.geometry import Point, LineString
from oia.utils import *
import datetime
from tqdm import tqdm
import pandas as pd
import geopandas as gpd

def assign_road_name(x):
    """Assign road conditions as paved or unpaved to Province roads

    Parameters
        x - Pandas DataFrame of values
            - code - Numeric code for type of asset
            - level - Numeric code for level of asset

    Returns
        String value as paved or unpaved
    """
    asset_type = str(x.road_type).lower().strip()
    

    # This is an national and provincial roads with paved surfaces
    if asset_type == 'national':
        if str(x.road_name) != '0':
            return x.road_name
        else:
            return 'no number'
    elif str(x.nombre) != '0':
        # Anything else not included above
        return str(x.nombre)
    else:
        return 'no number'

def assign_road_surface(x):
    """Assign road conditions as paved or unpaved to Province roads

    Parameters
        x - Pandas DataFrame of values
            - code - Numeric code for type of asset
            - level - Numeric code for level of asset

    Returns
        String value as paved or unpaved
    """
    asset_type = str(x.road_type).lower().strip()
    

    # This is an national and provincial roads with paved surfaces
    '''A - Asphalt, H - Hormigon, R - Ripio, T - Tierra, B - Tratamiento
    '''
    matrerial_surfaces = [('A','Asfalto'),('H','Hormigon'), ('R','Ripio'), ('T','Tierra'), ('B','Tratamiento')]
    if asset_type == 'national':
        if str(x.material_code) != '0':
            ml = x.material_code.split(',')
            s = []
            for ms in matrerial_surfaces:
                if ms[0] in ml:
                    s.append(ms[1])

            return ','.join(s)
        else:
            return 'Asfalto'
    elif str(x.surface).lower().strip() != '0':
        # Anything else not included above
        return x.surface.title()
    else:
        return 'Tierra'

def assign_road_conditions(x):
    """Assign road conditions as paved or unpaved to Province roads

    Parameters
        x - Pandas DataFrame of values
            - code - Numeric code for type of asset
            - level - Numeric code for level of asset

    Returns
        String value as paved or unpaved
    """
    asset_type = str(x.road_type).lower().strip()
    

    # This is an national and provincial roads with paved surfaces
    '''A - Asphalt, H - Hormigon, R - Ripio, T - Tierra, B - Tratamiento
    '''
    if asset_type == 'national':
        if ('A' in str(x.material_code)) or ('B' in str(x.material_code)) or ('H' in str(x.material_code)):
            return 'paved'
        elif ('R' in str(x.material_code)) or ('T' in str(x.material_code)):
            return 'unpaved'
        else:
            return 'paved'
    elif str(x.surface).lower().strip() in ('pavimentado, pavimento en construcc'):
        # Anything else not included above
        return 'paved'
    else:
        return 'unpaved'


def assign_road_terrain_and_width(x,width_terrain_list):
    """Assign terrain as flat or mountain to national roads

    Parameters
        x - Pandas DataFrame of values
            - dia_hinh__ - String value of type of terrain

    Returns
        String value of terrain as flat or mountain
    """
    road_no = x.road_no
    if str(road_no).isdigit():
        road_no = int(road_no)
    terrain = 'flat'
    assumed_width = 0
    if x.road_type == 'national':
        for vals in width_terrain_list:
            rn = vals.road_no
            if str(vals.road_no).isdigit():
                rn = int(rn)
            if road_no == rn and x.prog_min >= vals.inital_km and x.prog_max <= vals.final_km:
                assumed_width = vals.left_width + vals.right_width
                terrain = vals.terrain
                break

    if assumed_width == 0 and x.road_type in ('national','province'):
        assumed_width = 7.30
    elif assumed_width == 0 and x.road_type == 'rural':
        assumed_width = 3.65

    if unidecode.unidecode(str(terrain).lower().strip()) in ('llano','ondulado'):
        terrain = 'flat'
    elif unidecode.unidecode(str(terrain).lower().strip()) == 'montana':
        terrain = 'mountain'
    else:
        terrain = 'flat'

    return assumed_width, terrain

def assign_min_max_speeds_to_roads(x,speeds_list):
    """Assign terrain as flat or mountain to national roads

    Parameters
        x - Pandas DataFrame of values
            - dia_hinh__ - String value of type of terrain

    Returns
        String value of terrain as flat or mountain
    """
    road_no = x.road_no
    if str(road_no).isdigit():
        road_no = int(road_no)

    min_speed = 0
    max_speed = 0
    if x.road_type == 'national':
        for vals in speeds_list:
            rn = vals.ruta
            if str(rn).isdigit():
                rn = int(rn)

            if road_no == rn and x.prog_min >= vals.inicio and x.prog_max <= vals.fin:
                min_speed = vals.vmpes
                max_speed = vals.percentilpes
                break

    if (min_speed == 0 or isinstance(min_speed,str)) and x.road_type == 'national':
        if (0 < x.road_service <= 1) or (0 < x.road_quality <= 3):
            min_speed = 50
            max_speed = 80
        elif (1 < x.road_service <= 2) or (3 < x.road_quality <= 6):
            min_speed = 60
            max_speed = 90
        else:
            min_speed = 70
            max_speed = 100

    elif (min_speed == 0 or isinstance(min_speed,str)) and x.road_type == 'province':
        min_speed = 40
        max_speed = 60
    elif (min_speed == 0 or isinstance(min_speed,str)):
        min_speed = 20
        max_speed = 40

    return min_speed, max_speed

def assign_minmax_time_costs_roads(x, road_costs,exchange_rate):
    design_speeds = road_costs['speed'].values.tolist()
    if x.min_speed == 0 and x.max_speed == 0:
        min_cost = 0
        max_cost = 0
    elif x.min_speed in design_speeds and x.max_speed in design_speeds:
        min_speed = x.min_speed
        max_speed = x.max_speed
    else:
        min_speed = [design_speeds[d] for d in range(len(design_speeds)-1) if design_speeds[d] <= x.min_speed < design_speeds[d+1]][0]
        max_speed = [design_speeds[d] for d in range(len(design_speeds)-1) if design_speeds[d] <= x.max_speed < design_speeds[d+1]][0]
   
    if x.surface.lower().strip() in ('tierra','de tierra'):
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'tierra_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'tierra_cost_total'].values[0]
    elif x.surface.lower().strip() in ('ripio','consolidado'):
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'ripio_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'ripio_cost_total'].values[0]
    else:
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'paved_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'paved_cost_total'].values[0]

    
    return exchange_rate*min_cost*x.length, exchange_rate*max_cost*x.length

def assign_minmax_tariff_costs_roads_apply(x,tariff_costs_dataframe,exchange_rate):
    min_cost = tariff_costs_dataframe['min_tariff_cost'].values[0]*x.length*exchange_rate
    max_cost = tariff_costs_dataframe['max_tariff_cost'].values[0]*x.length*exchange_rate

    return min_cost,max_cost


def road_shapefile_to_dataframe(edges,road_properties_dataframe,
    road_speeds_dataframe,time_costs_dataframe,tariff_costs_dataframe,exchange_rate):
    """Create national network dataframe from inputs

    Parameters
        - edges_in - String path to edges file/network Shapefile
        - road_properties_file - String path to Excel file with road attributes
        - usage_factor - Tuple of 2-float values between 0 and 1

    Returns
        edges: Geopandas DataFrame with network edge topology and attributes
    """
    tqdm.pandas()
    add_columns = ['road_name','terrain','road_type','surface',
        'road_cond','width','length',
        'prog_min','prog_max','dist_min','dist_max',
        'road_quality','road_service',
        'min_speed','max_speed',
        'min_time','max_time',
        'min_time_cost','max_time_cost',
        'min_tariff_cost','max_tariff_cost'
        ]


    # assgin asset terrain
    road_properties_dataframe = list(road_properties_dataframe.itertuples(index=False))
    edges['width_terrain'] = edges.progress_apply(lambda x: assign_road_terrain_and_width(x,road_properties_dataframe), axis=1)
    edges[['width', 'terrain']] = edges['width_terrain'].apply(pd.Series)
    edges.drop('width_terrain', axis=1, inplace=True)

    # assign road surface
    edges['road_name'] = edges.progress_apply(assign_road_name, axis=1)

    # assign road surface
    edges['surface'] = edges.progress_apply(assign_road_surface, axis=1)

    # assign road conditon
    edges['road_cond'] = edges.progress_apply(assign_road_conditions, axis=1)

    # assign minimum and maximum speed to network
    road_speeds_dataframe = list(road_speeds_dataframe.itertuples(index=False))
    edges['speed'] = edges.progress_apply(lambda x: assign_min_max_speeds_to_roads(
        x, road_speeds_dataframe), axis=1)
    edges[['min_speed', 'max_speed']] = edges['speed'].apply(pd.Series)
    edges.drop('speed', axis=1, inplace=True)

    # assign minimum and maximum travel time to network
    edges['min_time'] = edges['length']/edges['max_speed']
    edges['max_time'] = edges['length']/edges['min_speed']

    # assign minimum and maximum cost of time in USD to the network
    # the costs of time  = (unit vehicle operating cost depending upon speed in USD/km)*(length of road)
    edges['time_cost'] = edges.progress_apply(
        lambda x: assign_minmax_time_costs_roads(x, time_costs_dataframe,exchange_rate), axis=1)
    edges[['min_time_cost', 'max_time_cost']] = edges['time_cost'].apply(pd.Series)
    edges.drop('time_cost', axis=1, inplace=True)

    # assign minimum and maximum cost of tonnage in USD/ton to the network
    # the costs of time  = (unit cost of tariff in USD/ton-km)*(length in km)
    edges['tariff_cost'] = edges.progress_apply(
        lambda x: assign_minmax_tariff_costs_roads_apply(x, tariff_costs_dataframe,exchange_rate), axis=1)
    edges[['min_tariff_cost', 'max_tariff_cost']] = edges['tariff_cost'].apply(pd.Series)
    edges.drop('tariff_cost', axis=1, inplace=True)

    # make sure that From and To node are the first two columns of the dataframe
    # to make sure the conversion from dataframe to igraph network goes smooth
    edges = edges[['edge_id','from_node','to_node'] + add_columns + ['geometry']]
    edges = edges.reindex(list(edges.columns)[1:]+list(edges.columns)[:1], axis=1)

    return edges

def find_km_markers(road_dataframe,marker_dataframe):
    epsg_utm_20s = 32720
    road_dataframe = road_dataframe.to_crs(epsg=epsg_utm_20s)
    marker_dataframe = marker_dataframe.to_crs(epsg=epsg_utm_20s)
    marker_dataframe['poly_geometry'] = marker_dataframe.geometry.progress_apply(lambda x: x.buffer(0.04))
    poly_df = marker_dataframe[['id','progresiva','distancia','poly_geometry']]
    poly_df.rename(columns={'poly_geometry':'geometry'},inplace=True)
    road_matches = gpd.sjoin(road_dataframe,poly_df, how="inner", op='intersects').reset_index()
    marker_dataframe.drop('poly_geometry',axis=1,inplace=True)
    del poly_df
    road_matches = road_matches[['edge_id','id','progresiva','distancia']].set_index(['edge_id'])
    marker_dataframe = marker_dataframe.set_index(['id'])
    edge_ids = list(set(road_matches.index.values.tolist()))
    edge_markers = []
    for e_id in edge_ids:
        marker_ids = road_matches.loc[[e_id],'id'].values.tolist()
        marker_prog = road_matches.loc[[e_id],'progresiva'].values.tolist()
        marker_dist = road_matches.loc[[e_id],'distancia'].values.tolist()
        marker_geom = marker_dataframe.loc[marker_ids,'geometry'].values.tolist()

        points_list = list(zip(marker_ids,marker_prog,marker_dist,marker_geom))
        pt_tup_list = []
        for pts in points_list:
            line = road_dataframe.loc[road_dataframe['edge_id']==e_id,'geometry'].values[0]
            point = line.interpolate(line.project(pts[-1]))
            pt_tup_list.append(tuple(list(pts[:-1]) + [line.project(point)]))

        length_km = 0.001*(road_dataframe.loc[road_dataframe['edge_id']==e_id,'length'].values[0])
        pt_tup_list = [(p,w,x,y) for (p,w,x,y) in sorted(pt_tup_list, key=lambda pair: pair[-1])]
        if pt_tup_list[0][-1] > 0:
            prog_min = pt_tup_list[0][1] - 0.001*pt_tup_list[0][-1]
            dist_min = pt_tup_list[0][2] - 0.001*pt_tup_list[0][-1]
        else:
            prog_min = pt_tup_list[0][1]
            dist_min = pt_tup_list[0][2]

        if pt_tup_list[-1][-1] < 1:
            prog_max = pt_tup_list[-1][1] + (length_km - 0.001*pt_tup_list[-1][-1])
            dist_max = pt_tup_list[-1][2] + (length_km - 0.001*pt_tup_list[-1][-1])
        else:
            prog_max = pt_tup_list[-1][1]
            dist_max = pt_tup_list[-1][2]

        if prog_min < 1e-3:
            prog_min = 0
        if dist_min < 1e-3:
            dist_min = 0
        edge_markers.append((e_id,prog_min,prog_max,dist_min,dist_max))

    edge_markers = pd.DataFrame(edge_markers,columns = ['edge_id','prog_min','prog_max','dist_min','dist_max'])

    del marker_dataframe, road_matches, edge_ids

    return edge_markers

def get_numeric_attributes(road_gpd,attribute_gpd,attribute_id_column,attribute_value_column,road_column_name):
    epsg_utm_20s = 32720
    road_gpd = road_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd = attribute_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd['geometry'] = attribute_gpd.geometry.progress_apply(lambda x: x.buffer(0.04))
    road_matches = gpd.sjoin(road_gpd,attribute_gpd, how="inner", op='intersects').reset_index()
    road_matches = road_matches[['edge_id',attribute_id_column,attribute_value_column]].set_index(['edge_id'])
    attribute_gpd = attribute_gpd.set_index([attribute_id_column])
    edge_ids = list(set(road_matches.index.values.tolist()))
    edge_vals = []
    for e_id in edge_ids:
        line = road_gpd.loc[road_gpd['edge_id']==e_id,'geometry'].values[0]
        attr_ids = road_matches.loc[[e_id],attribute_id_column].values.tolist()
        attr_vals = road_matches.loc[[e_id],attribute_value_column].values.tolist()
        attr_geom = attribute_gpd.loc[attr_ids,'geometry'].values.tolist()

        poly_list = list(zip(attr_vals,attr_geom))
        attr_tot = 0
        length_tot = 0
        for poly in poly_list:
            length_m = line.intersection(poly[1]).length
            attr_tot += poly[0]*length_m
            length_tot += length_m

        attr_tot = 1.0*attr_tot/length_tot
        edge_vals.append((e_id,attr_tot))

        print ('Done with attribute {} for edge {}'.format(road_column_name,e_id))

    edge_vals = pd.DataFrame(edge_vals,columns=['edge_id',road_column_name])

    del attribute_gpd
    return edge_vals

def get_string_attributes(road_gpd,attribute_gpd,attribute_value_column,road_column_name):
    epsg_utm_20s = 32720
    road_gpd = road_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd = attribute_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd['geometry'] = attribute_gpd.geometry.progress_apply(lambda x: x.buffer(0.04))
    road_matches = gpd.sjoin(road_gpd,attribute_gpd, how="inner", op='intersects').reset_index()
    road_matches = road_matches[['edge_id',attribute_value_column]].set_index(['edge_id'])
    edge_ids = list(set(road_matches.index.values.tolist()))
    edge_vals = []
    for e_id in edge_ids:
        attr_vals = ','.join(list(set(road_matches.loc[[e_id],attribute_value_column].values.tolist())))
        edge_vals.append((e_id,attr_vals))

        print ('Done with attribute {} for edge {}'.format(road_column_name,e_id))

    edge_vals = pd.DataFrame(edge_vals,columns=['edge_id',road_column_name])

    del attribute_gpd
    return edge_vals

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    exchange_rate = 0.026

    attributes_desc = [
        {
            'folder_name':'indice_de_estado',
            'file_name':'vistagis_selLine.shp',
            'id_column':'nro_regist',
            'attribute':'valor',
            'attribute_rename':'road_quality'
        },
        {
            'folder_name':'indice_de_serviciabilidad',
            'file_name':'vistagis_selLine.shp',
            'id_column':'nro_regist',
            'attribute':'valor',
            'attribute_rename':'road_service'
        },
        {
            'folder_name':'materialcarril_sel',
            'file_name':'materialcarril_selLine.shp',
            'id_column':'id_materia',
            'attribute':'grupo',
            'attribute_rename':'material_code'
        },
    ]


    '''Get road edge network
    '''
    road_edges_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_edges.shp')
    road_nodes_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_nodes.shp')
    '''Get the road properties, which are mainly the widths of national roads
    '''
    skiprows = 4
    road_properties_df = pd.read_excel(os.path.join(incoming_data_path,'5','DNV_data_recieved_06082018','Tramos por Rutas.xls'),sheet_name='Hoja1',skiprows=skiprows,encoding='utf-8-sig').fillna(0)
    # road_properties_df = road_properties_df.iloc[skiprows:]
    road_properties_df.columns = ['road_no','location','inital_km','final_km',
                                'purpose','description','length_km','left_surface',
                                'left_width','right_surface','right_width','lanes','terrain']


    road_speeds_df = pd.read_excel(os.path.join(incoming_data_path,'5','DNV_data_recieved_06082018','TMDA y Clasificación 2016.xlsx'),sheet_name='Clasificación 2016',skiprows=14,encoding='utf-8-sig').fillna(0)
    road_speeds_df.columns = map(str.lower, road_speeds_df.columns)

    time_costs_df = pd.read_excel(os.path.join(incoming_data_path,'5','Costs','Costos de Operación de Vehículos.xlsx'),sheet_name='Camión Pesado',skiprows=15,encoding='utf-8-sig').fillna(0)
    time_costs_df.columns = ['speed','tierra_cost_A','tierra_cost_B','tierra_cost_total',
                                'ripio_cost_A','ripio_cost_B','ripio_cost_total',
                                'paved_cost_A','paved_cost_B','paved_cost_total','speed_copy']

    time_costs_df = time_costs_df[time_costs_df['speed'] > 0]

    tariff_costs_df = pd.read_excel(os.path.join(incoming_data_path,'5','Costs','tariff_costs.xlsx'),sheet_name='road',encoding='utf-8')

    nodes = gpd.read_file(road_nodes_path,encoding='utf-8').fillna(0)
    nodes.columns = map(str.lower, nodes.columns)
    nodes.rename(columns={'id':'node_id'},inplace=True)

    edges_in = road_edges_path
    edges = gpd.read_file(edges_in,encoding='utf-8').fillna(0)
    edges.columns = map(str.lower, edges.columns)

    new_edges = {}
    new_edges['from_id'] = 'roadn_65'
    new_edges['to_id'] = 'roadn_66'
    new_edges['road_name'] = 3
    new_edges['road_no'] = 275
    new_edges['road_type'] = 'national'
    new_edges['sentido'] = 'A'
    new_edges = pd.DataFrame([new_edges],columns=new_edges.keys())
    new_edges['from_geom'] = nodes[nodes['node_id'] == 'roadn_65'].geometry.values[0]
    new_edges['to_geom'] = nodes[nodes['node_id'] == 'roadn_66'].geometry.values[0]
    new_edges['geometry'] = new_edges.apply(lambda x: LineString([x.from_geom,x.to_geom]),axis = 1)
    new_edges.drop('from_geom',axis=1,inplace=True)
    new_edges.drop('to_geom',axis=1,inplace=True)
    edges = gpd.GeoDataFrame(pd.concat([edges,new_edges],axis=0,sort='False', ignore_index=True).fillna(0),geometry='geometry',crs={'init' :'epsg:4326'})
    # print (edges['geometry'])
    # edges[['id','geometry']].to_csv('test.csv')

    edges['id'] = ['{}_{}'.format('roade', i) for i in range(len(edges.index))]

    edges.rename(columns={'id':'edge_id','from_id':'from_node','to_id':'to_node'},inplace=True)

    # get the right linelength
    edges['length'] = edges.geometry.progress_apply(line_length)

    '''Add properties to the national roads
    '''
    '''Add the kilometer markers
    '''
    marker_df = gpd.read_file(os.path.join(incoming_data_path,'pre_processed_network_data','roads','national_roads','v_mojon','v_mojonPoint.shp'),encoding='utf-8').fillna(0)
    km_markers = find_km_markers(edges[edges['road_type']=='national'][['edge_id','length','geometry']],marker_df)
    edges = pd.merge(edges,km_markers,how='left',on=['edge_id']).fillna(0)
    '''Add the quality and service
    '''
    for a in attributes_desc:
        road_attr = gpd.read_file(os.path.join(incoming_data_path,
                        'pre_processed_network_data','roads','national_roads',
                        a['folder_name'],a['file_name']),encoding='utf-8').fillna(0)
        if a['folder_name'] == 'materialcarril_sel':
            edge_attr = get_string_attributes(edges[edges['road_type']=='national'][['edge_id','length','geometry']],road_attr,a['attribute'],a['attribute_rename'])
        else:
            road_attr = road_attr[(road_attr['sentido'] == 'A') & (road_attr[a['attribute']] != -1)]
            edge_attr = get_numeric_attributes(edges[edges['road_type']=='national'][['edge_id','length','geometry']],road_attr,a['id_column'],a['attribute'],a['attribute_rename'])
        
        edges = pd.merge(edges,edge_attr,how='left',on=['edge_id']).fillna(0)

    edges = road_shapefile_to_dataframe(edges,road_properties_df,road_speeds_df,time_costs_df,tariff_costs_df,exchange_rate)

    edges.to_file(os.path.join(data_path,'network','road_edges.shp'),encoding = 'utf-8')
    edges.drop('geometry', axis=1, inplace=True)
    edges.to_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8',index=False)

    nodes.to_file(os.path.join(data_path,'network', 'road_nodes.shp'),encoding = 'utf-8')
    nodes.drop('geometry', axis=1, inplace=True)
    nodes.to_csv(os.path.join(data_path,'network','road_nodes.csv'),encoding='utf-8',index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
