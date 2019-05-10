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
from shapely import wkt,ops
from atra.utils import *
import copy
from atra.transport_flow_and_failure_functions import *
import datetime
from tqdm import tqdm
import pandas as pd
import geopandas as gpd


def find_km_markers(road_dataframe,marker_dataframe,marker_id):
    line = road_dataframe['geometry'].values[0]
    length_km = 0.001*(road_dataframe['geometry'].length.values[0])
    points_list = list(zip(marker_dataframe[marker_id].values.tolist(),marker_dataframe['geometry'].values.tolist()))
    pt_tup_list = []
    for pts in points_list:
        point = line.interpolate(line.project(pts[-1]))
        pt_tup_list.append(tuple(list(pts[:-1]) + [0.001*line.project(point),(length_km - 0.001*line.project(point))]))

    edge_markers = pd.merge(marker_dataframe,pd.DataFrame(pt_tup_list,columns = [marker_id,'prog_st','prog_end']),how='left',on=[marker_id])

    return edge_markers

def find_closest_edges(x,road_dataframe,edge_id_column):
    id_dist = []
    for j,line in road_dataframe.iterrows():
        id_dist.append((line[edge_id_column],x['geometry'].distance(line['geometry'])))

    id_dist = [(z,y) for (z,y) in sorted(id_dist, key=lambda pair: pair[-1])]

    return id_dist[0][0]

def find_point_edges(road_dataframe,marker_dataframe,marker_columns,edge_columns,geom_buffer):
    marker_dataframe['poly_geometry'] = marker_dataframe.geometry.apply(lambda x: x.buffer(geom_buffer))
    poly_df = marker_dataframe[marker_columns + ['poly_geometry']]
    poly_df.rename(columns={'poly_geometry':'geometry'},inplace=True)
    road_matches = gpd.sjoin(road_dataframe,poly_df, how="inner", op='intersects').reset_index()
    return road_matches[edge_columns+marker_columns]

def get_marker(x,points_dataframe,common_column,extract_column):
    selected_dataframe = points_dataframe[points_dataframe[common_column] == x[common_column]]
    if len(selected_dataframe.index) > 0:
        dist = []
        for idx, vals in selected_dataframe.iterrows():
            dist.append(x.geometry.distance(vals.geometry))

        selected_dataframe['distance'] = dist
        selected_dataframe = selected_dataframe.sort_values(by=['distance'])
        if len(selected_dataframe.index) == 1:
            return selected_dataframe[extract_column].values[0] + 0.001*selected_dataframe['distance'].values[0]
        else:
            if selected_dataframe[extract_column].values[0] < selected_dataframe[extract_column].values[1]:
                return selected_dataframe[extract_column].values[0] + 0.001*selected_dataframe['distance'].values[0]
            else:
                return selected_dataframe[extract_column].values[1] + 0.001*selected_dataframe['distance'].values[1]
    else:
        return 0

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    epsg_utm_20s = 32720
    '''Get road edge network
    '''
    road_edges_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','national_roads','rutas','rutas.shp')
    edges_in = road_edges_path
    edges = gpd.read_file(edges_in,encoding='utf-8').fillna(0)
    edges = edges.to_crs(epsg=epsg_utm_20s)
    edges.columns = map(str.lower, edges.columns)

    '''Add the kilometer markers
    '''
    km_markers = gpd.read_file(os.path.join(incoming_data_path,'pre_processed_network_data','roads','national_roads','v_mojon','v_mojonPoint.shp'),encoding='utf-8').fillna(0)
    km_markers = km_markers.to_crs(epsg=epsg_utm_20s)
    km_markers['id_ruta'] = km_markers.progress_apply(lambda x:find_closest_edges(x,edges,'id_ruta'),axis=1)
    km_markers = pd.merge(km_markers,edges[['id_ruta','cod_ruta']],how='left',on=['id_ruta'])

    '''Find the bridge locations
    '''
    marker_df = gpd.read_file(os.path.join(incoming_data_path,'pre_processed_network_data','roads','national_roads','puente_sel','puente_selPoint.shp'),encoding='utf-8').fillna(0)
    marker_df.drop_duplicates(subset='id_estruct', keep='first', inplace=True)

    marker_df = marker_df.to_crs(epsg=epsg_utm_20s)
    bm = find_point_edges(edges[['id_ruta','cod_ruta','geometry']],marker_df,['id_estruct','color'],['id_ruta','cod_ruta'],1)
    bm = pd.merge(bm,marker_df[['id_estruct','geometry']],how='left',on=['id_estruct'])
    bridge_markers = copy.deepcopy(bm)
    del marker_df

    bridge_df = pd.read_excel(os.path.join(incoming_data_path,'pre_processed_network_data','roads',
                'national_roads','puente_sel','Consulta Puentes - 2017.xlsx'),sheet_name='Consulta',encoding='utf-8-sig').fillna(0)
    bridge_df.columns = map(str.lower, bridge_df.columns)

    all_ids = list(set(bridge_markers['id_estruct'].values.tolist()))
    ids = copy.deepcopy(all_ids)
    multiple_ids = []
    bridge_matches = []
    for i in ids:
        if len(bridge_markers[bridge_markers['id_estruct'] == i].index) > 1:
            print (i,bridge_markers.loc[bridge_markers['id_estruct'] == i,'cod_ruta'].values,len(bridge_markers[bridge_markers['id_estruct'] == i].index))
            multiple_ids.append(i)
            routes = bridge_markers.loc[bridge_markers['id_estruct'] == i,'cod_ruta'].values.tolist()
            for r in routes:
                if (len(bridge_df[bridge_df['ruta'] == r].index) < len(bridge_markers[bridge_markers['cod_ruta'] == r].index)):
                    if len(bridge_markers[bridge_markers['id_estruct'] == i].index) > 1:
                        bridge_markers = bridge_markers[(bridge_markers['cod_ruta'] != r) | (bridge_markers['id_estruct'] != i)]
                        print (r,i,len(bridge_markers.index))
                else:
                    print ('equal',r,i)


    routes = list(set(bridge_markers['cod_ruta'].values.tolist()))
    bridge_matches = []
    id_matches = []
    r_n = []
    for r in routes:
        bridge_info = bridge_df[bridge_df['ruta'] == r]
        bridge_ids = bridge_markers[bridge_markers['cod_ruta'] == r]
        bridge_ids.drop_duplicates(subset='id_estruct', keep='first', inplace=True)
        if len(bridge_info.index) == len(bridge_ids.index):
            bridge_matches.append(bridge_ids)
            id_matches += bridge_ids['id_estruct'].values.tolist()
        else:
            r_n.append(r)


    r_m = []
    id_m = []
    for r in r_n:
        bridge_info = bridge_df[bridge_df['ruta'] == r]
        bridge_ids = bridge_markers[bridge_markers['cod_ruta'] == r]
        if (len(bridge_info.index) < len(bridge_ids.index)):
            print ('old lengths',r,len(bridge_ids.index),len(bridge_info.index))
            ids = list(set(bridge_ids['id_estruct'].values.tolist()))
            for i in ids:
                if i in id_matches:
                    bridge_ids  = bridge_ids[bridge_ids['id_estruct'] != i]

            print ('new lengths',r,len(bridge_ids.index),len(bridge_info.index))
            if (len(bridge_info.index) == len(bridge_ids.index)):
                bridge_matches.append(bridge_ids)
            elif (len(bridge_info.index) < len(bridge_ids.index)):
                ids = list(set(bridge_ids['id_estruct'].values.tolist()))
                mid = []
                for i in ids:
                    if i in multiple_ids:
                        mid.append(i)

                if len(mid) == (len(bridge_ids.index) - len(bridge_info.index)):
                    for i in mid:
                        bridge_ids = bridge_ids[bridge_ids['id_estruct'] != i]

                    print ('newer lengths',r,len(bridge_ids.index),len(bridge_info.index))
                    bridge_matches.append(bridge_ids)
                    id_matches += bridge_ids['id_estruct'].values.tolist()
                else:
                    print ('extra lengths',r,mid,len(bridge_ids.index),len(bridge_info.index))

        else:
            print ('Need to add extra',r,len(bridge_info.index),len(bridge_ids.index))
            r_m.append(r)
            id_m += bridge_ids['id_estruct'].values.tolist()

    for i in all_ids:
        if i not in id_matches + id_m:
            routes = bm.loc[bm['id_estruct'] == i,'cod_ruta'].values
            for r in routes:
                if r in r_m:
                    bridge_info = bridge_df[bridge_df['ruta'] == r]
                    bridge_ids = bm[bm['cod_ruta'] == r]
                    bridge_ids.drop_duplicates(subset='id_estruct', keep='first', inplace=True)
                    if (len(bridge_info.index) == len(bridge_ids.index)):
                        print ('works',r,len(bridge_info.index),len(bridge_ids.index))
                        bridge_matches.append(bridge_ids)
                        id_matches += bridge_ids['id_estruct'].values.tolist()


    '''Cannot improve further!
        Just combine everything
    '''
    for i in all_ids:
        if i not in id_matches:
            bridge_ids = bm[bm['id_estruct'] == i]
            bridge_matches.append(bridge_ids)
            id_matches += bridge_ids['id_estruct'].values.tolist()

    bridge_markers = gpd.GeoDataFrame(pd.concat(bridge_matches,axis=0,sort='False', ignore_index=True).fillna(0),geometry='geometry',crs={'init' :'epsg:32720'})

    '''Match bridge locations to markers
    '''
    bridge_markers['distances'] = bridge_markers.progress_apply(lambda x:get_marker(x,km_markers,'id_ruta','progresiva'),axis=1)
    bridge_markers.to_csv(os.path.join(incoming_data_path,'pre_processed_network_data','roads','national_roads','puente_sel','bridge_markers.csv'),encoding='utf-8-sig',index=False)

    # bridge_markers = pd.read_csv('bridge_markers.csv',encoding='utf-8-sig').fillna(0)
    # bridge_markers['geometry'] = bridge_markers['geometry'].apply(wkt.loads)
    # bridge_markers = gpd.GeoDataFrame(bridge_markers,geometry='geometry',crs={'init' :'epsg:32720'})

    routes = list(set(bridge_markers['cod_ruta'].values.tolist()))
    bridge_data = []
    for r in routes:
        bridge_info = bridge_df[bridge_df['ruta'] == r].reset_index()
        bridge_info = bridge_info.sort_values(by=['prog. inicial'])
        bridge_ids = bridge_markers[bridge_markers['cod_ruta'] == r].reset_index()
        if (len(bridge_info.index) == len(bridge_ids.index)) and (list(set(bridge_ids['distances'].values.tolist())) != [0]):
            bridge_ids = bridge_ids.sort_values(by=['distances'])
            bridge_info['ids'] = bridge_ids['id_estruct'].values.tolist()
            bridge_info['distances'] = bridge_ids['distances'].values.tolist()
            bridge_info['color'] = bridge_ids['color'].values.tolist()
            bridge_info['geometry'] = bridge_ids['geometry'].values.tolist()
            bridge_data.append(bridge_info)
        elif (len(bridge_info.index) == 1) and (len(bridge_ids.index) == 1):
            bridge_info['ids'] = bridge_ids['id_estruct'].values.tolist()
            bridge_info['distances'] = bridge_ids['distances'].values.tolist()
            bridge_info['color'] = bridge_ids['color'].values.tolist()
            bridge_info['geometry'] = bridge_ids['geometry'].values.tolist()
            bridge_data.append(bridge_info)
        elif (len(bridge_info.index) == len(bridge_ids.index)) and (list(set(bridge_ids['distances'].values.tolist())) == [0]):
            prog_st_end = find_km_markers(edges[edges['cod_ruta'] == r],bridge_ids,'id_estruct')
            prog_st = prog_st_end.sort_values(by=['prog_st'])
            prog_end = prog_st_end.sort_values(by=['prog_end'])
            if abs((prog_st['prog_st'].values - bridge_info['prog. inicial'].values).sum()) < abs((prog_st['prog_end'].values - bridge_info['prog. inicial'].values).sum()):
                bridge_info['ids'] = prog_st['id_estruct'].values.tolist()
                bridge_info['distances'] = prog_st['prog_st'].values.tolist()
                bridge_info['color'] = prog_st['color'].values.tolist()
                bridge_info['geometry'] = prog_st['geometry'].values.tolist()
                bridge_data.append(bridge_info)
            else:
                bridge_info['ids'] = prog_end['id_estruct'].values.tolist()
                bridge_info['distances'] = prog_end['prog_end'].values.tolist()
                bridge_info['color'] = prog_end['color'].values.tolist()
                bridge_info['geometry'] = prog_end['geometry'].values.tolist()
                bridge_data.append(bridge_info)

        elif (len(bridge_info.index) != len(bridge_ids.index)) and (list(set(bridge_ids['distances'].values.tolist())) != [0]):
            if len(bridge_info.index) > len(bridge_ids.index):
                print (bridge_info.index.values)
                bridge_ids = bridge_ids.sort_values(by=['distances'])
                id_dist = []
                for idx,val in bridge_info.iterrows():
                    id_dist.append((idx,np.absolute(np.array(val['prog. inicial']*len(bridge_ids.index)) - bridge_ids['distances'].values).min()))

                id_dist = [(z,y) for (z,y) in sorted(id_dist, key=lambda pair: pair[-1])]
                # bridge_info = bridge_info[bridge_info.index != id_dist[-1][0]]
                bridge_info = bridge_info.drop(bridge_info.index[[id_dist[-1][0]]])
                print (id_dist,r,len(bridge_info.index),len(bridge_ids.index))
                bridge_info['ids'] = bridge_ids['id_estruct'].values.tolist()
                bridge_info['distances'] = bridge_ids['distances'].values.tolist()
                bridge_info['color'] = bridge_ids['color'].values.tolist()
                bridge_info['geometry'] = bridge_ids['geometry'].values.tolist()
                bridge_data.append(bridge_info)

            else:
                id_dist = []
                for idx,val in bridge_ids.iterrows():
                    id_dist.append((val['id_estruct'],np.absolute(np.array(val['prog. inicial']*len(bridge_ids.index)) - bridge_ids['distances'].values).min()))

                id_dist = [(z,y) for (z,y) in sorted(id_dist, key=lambda pair: pair[-1])]
                bridge_ids = bridge_ids[bridge_ids['id_estruct'] != id_dist[-1][0]]
                bridge_ids = bridge_ids.sort_values(by=['distances'])
                bridge_info['ids'] = bridge_ids['id_estruct'].values.tolist()
                bridge_info['distances'] = bridge_ids['distances'].values.tolist()
                bridge_info['color'] = bridge_ids['color'].values.tolist()
                bridge_info['geometry'] = bridge_ids['geometry'].values.tolist()
                bridge_data.append(bridge_info)

        else:
            print (r,len(bridge_info.index),len(bridge_ids.index))

    columns = ['altura de barandas',
        'altura libre',
        'ancho de vereda derecha',
        'ancho de vereda izquierda',
        'ancho pavimento asc.',
        'ancho pavimento desc.',
        'año de construcción',
        'clase de estructura',
        'color',
        'distances',
        'distrito',
        'geometry',
        'gálibo horizontal asc.',
        'gálibo horizontal desc.',
        'gálibo vertical asc.',
        'gálibo vertical desc.',
        'ids',
        'iluminación',
        'index',
        'longitud',
        'longitud luces',
        'límite de carga',
        'material de barandas',
        'material pavimento asc.',
        'material pavimento desc.',
        'material sub estructura',
        'material super estructura',
        'nro luces',
        'peaje',
        'prog. final',
        'prog. inicial',
        'protección de tablero',
        'ruta',
        'tipo de estructura',
        'tipo de tablero',
        'ubicación']

    columns_rename = ['railing_height',
        'free_height',
        'right_lane_width',
        'left_lane_width',
        'pavement_width_asc',
        'pavement_width_desc',
        'construction_year',
        'structure_class',
        'color',
        'distances',
        'province',
        'geometry',
        'horizontal_clearance_asc',
        'horizontal_clearance_desc',
        'vertical_clearance_asc',
        'vertical_clearance_desc',
        'bridge_id',
        'illumination',
        'index',
        'length',
        'length_lights',
        'load_limit',
        'railing_material',
        'pavement_material_asc',
        'pavement_material_desc',
        'substructure_mateerial',
        'superstructure_mateerial',
        'nro_lights',
        'toll',
        'final_km_marker',
        'initial_km_marker',
        'board_protection',
        'ruta',
        'structure_type',
        'board_type',
        'location'
        ]

    columns_dict= {}
    for c in range(len(columns)):
        columns_dict[columns[c]] = columns_rename[c]

    bridges = gpd.GeoDataFrame(pd.concat(bridge_data,axis=0,sort='False', ignore_index=True).fillna(0),geometry='geometry',crs={'init' :'epsg:32720'})
    bridges.rename(columns=columns_dict,inplace=True)

    edges = gpd.read_file(os.path.join(data_path,'network','road_edges.shp'),encoding='utf-8').fillna(0)
    edges = edges.to_crs(epsg=epsg_utm_20s)
    edges.columns = map(str.lower, edges.columns)

    edges = edges[edges['road_type']=='national']
    edges = edges[['edge_id','road_name','geometry']]
    edges['road_name'] = edges.road_name.progress_apply(lambda x:str(x.split(',')))
    bridges['edge_id'] = bridges.progress_apply(lambda x:find_closest_edges(x,edges[edges['road_name'].str.contains("'{}'".format(x.ruta))],'edge_id'),axis=1)

    bridges = bridges.to_crs(epsg=4326)
    bridges.to_file(os.path.join(data_path,'network','bridges.shp'),encoding='utf-8')
    bridges.drop('geometry',axis=1,inplace=True)
    bridges.to_csv(os.path.join(data_path,'network','bridges.csv'),encoding='utf-8-sig',index=False)

    '''Convert bridge geometries to lines based on point location and length
    '''
    bridges = gpd.read_file(os.path.join(data_path,'network','bridges.shp'),encoding='utf-8')
    bridges = bridges[['bridge_id','geometry']]
    bridges = bridges.to_crs(epsg=epsg_utm_20s)
    bridges = pd.merge(bridges,pd.read_csv(os.path.join(data_path,'network','bridges.csv'),encoding='utf-8-sig'),how='left',on=['bridge_id'])

    edges = gpd.read_file(os.path.join(data_path,'network','road_edges.shp'),encoding='utf-8').fillna(0)
    edges = edges.to_crs(epsg=epsg_utm_20s)
    edges.columns = map(str.lower, edges.columns)
    edges = edges[edges['road_type']=='national']
    edges = edges[['edge_id','geometry']]

    # test_bridge = 1160902
    # bridges = bridges[bridges['bridge_id'] == test_bridge]
    bridge_lines = []
    for idx,val in bridges.iterrows():
        line = edges.loc[edges['edge_id'] == val['edge_id'],'geometry'].values[0]
        length_m = edges.loc[edges['edge_id'] == val['edge_id'],'geometry'].length.values[0]
        pt_loc = line.project(line.interpolate(line.project(val.geometry)))
        pt_h = pt_loc + 0.5*1000.0*val['length']
        if pt_h > length_m:
            pt_h = length_m
        pt_b = pt_loc - 0.5*1000.0*val['length']
        if pt_b < 0:
            pt_b = 0

        if pt_h == pt_b:
            merged_line = LineString([line.interpolate(pt_h),line.interpolate(pt_b)])
        else:
            merged_line = []
            for p in line.coords:
                d = line.project(Point(p))
                if pt_b <= line.project(Point(p)) <= pt_h:
                    merged_line.append(Point(p))
            if len(merged_line) > 1:
                merged_line = LineString(merged_line)
            else:
                merged_line = LineString([line.interpolate(pt_h),line.interpolate(pt_b)])

        bridge_lines.append((val['bridge_id'],merged_line,0.001*merged_line.length))

    bridge_lines = gpd.GeoDataFrame(pd.DataFrame(bridge_lines,columns=['bridge_id','geometry','length']).fillna(0),geometry='geometry',crs={'init' :'epsg:32720'})
    bridge_lines = bridge_lines.to_crs(epsg=4326)
    bridge_lines.to_file(os.path.join(data_path,'network','bridge_edges.shp'),encoding='utf-8')



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
