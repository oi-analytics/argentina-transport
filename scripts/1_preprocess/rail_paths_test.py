"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import pandas as pd
import geopandas as gpd
import numpy as np
import igraph as ig
import copy
import unidecode
from oia.utils import *
import datetime

def extract_subset_from_dataframe(input_dataframe,skiprows,start_row,end_row,new_columns):
    output_data = []
    input_dataframe = input_dataframe.iloc[skiprows:]
    for iter_,row in input_dataframe.iterrows():
        output_data.append(tuple(row[start_row:end_row]))

    output_df = pd.DataFrame(output_data,columns=new_columns)
    return output_df

def get_province_matches(x,provinces_df):
    match = provinces_df[provinces_df['station'] == x]
    if len(match.index) > 0:
        match = match['province'].values.tolist()
        return match[0]
    else:
        return ''

def replace_string_characters(x,replace_strings):
    x_change = x.lower().strip()
    for rp in replace_strings:
        x_change = x_change.replace(rp[0],rp[1])

    return x_change

def  set_reference_date(x,reference_date):
    if x == 0:
        x = pd.Timestamp(reference_date)

    return x

def station_name_to_node_matches(st,rename_stations,replace_strings,fd,rail_nodes):
    if st[0] in rename_stations['od_station'].values.tolist():
        st_change = rename_stations.loc[rename_stations['od_station']==st[0],'od_station_correct'].values[0]
        if st_change == 0 or 'railn' in st_change:
            st_change = st[0]

        st_prov = rename_stations.loc[rename_stations['od_station']==st[0],'provincia'].values[0]
        if st_prov == 0:
            st_prov = st[1]
    else: 
        st_change = st[0]
        st_prov = st[1]

    st_change = str(st_change).lower().strip()
    st_prov = str(st_prov).lower().strip()
    for rp in replace_strings:
        st_change = st_change.replace(rp[0],rp[1])

    if fd['line_name'].lower().strip() in (unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip()) for x in rail_nodes):
        
        st_match = [x for x in rail_nodes \
            if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
            and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip()) \
            and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]
        
        if not st_match:
            st_match = [x for x in rail_nodes \
                if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip())]

        if not st_match:
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

            if not st_match:
                st_match = [x for x in rail_nodes if (unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                            or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())) \
                            and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

            if not st_match:
                st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip())]
            if not st_match:
                st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                            or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())]

    elif fd['line_name'].lower().strip() in (unidecode.unidecode(str(x.operador).lower().strip()) for x in rail_nodes):
        st_match = [x for x in rail_nodes \
            if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
            and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.operador).lower().strip()) \
            and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]
        
        if not st_match:
            st_match = [x for x in rail_nodes \
                if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.operador).lower().strip())]

        if not st_match:
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]
            if not st_match:
                st_match = [x for x in rail_nodes if (unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                            or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())) \
                            and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

            if not st_match:
                st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip())]
            if not st_match:
                st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                            or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())]

    else:
        st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

        if not st_match:
            st_match = [x for x in rail_nodes if (unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                        or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())) \
                        and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

        if not st_match:
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip())]
        if not st_match:
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) in unidecode.unidecode(st_change.lower().strip()) \
                        or unidecode.unidecode(st_change.lower().strip()) in unidecode.unidecode(x.nombre.lower().strip())]
    return st_match

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['incoming_data']

    rail_od_folder = os.path.join(incoming_data_path,'5','rail_od_matrices_06082018','Matrices OD FFCC')
    file_desc = [{'file_name':'OD BcyL',
        'sheet_name':'BCYLBEL',
        'line_name':'Belgrano',
        'skiprows':5,
        'start_row':0,
        'end_row':11,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_date','origin_station','origin_line',
                'destination_date','destination_station','destination_line',
                'line_routes']
        },
        {'file_name':'OD BcyL',
        'sheet_name':'BCYLSM',
        'line_name':'San Martin',
        'skiprows':5,
        'start_row':0,
        'end_row':11,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_date','origin_station','origin_line',
                'destination_date','destination_station','destination_line',
                'line_routes']
        },
        {'file_name':'OD BcyL',
        'sheet_name':'BCYLURQ',
        'line_name':'Urquiza',
        'skiprows':5,
        'start_row':0,
        'end_row':11,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_date','origin_station','origin_line',
                'destination_date','destination_station','destination_line',
                'line_routes']
        },
        {'file_name':'OD FEPSA',
        'sheet_name':'Datos',
        'line_name':'FEPSA',
        'skiprows':4,
        'start_row':0,
        'end_row':11,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_date','origin_station','origin_line',
                'destination_date','destination_station','destination_line',
                'line_routes']
        },
        {'file_name':'OD Ferrosur',
        'sheet_name':'INFORME ORIG-DEST',
        'line_name':'Roca',
        'skiprows':2,
        'start_row':0,
        'end_row':15,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_station','origin_province',
                'destination_station','destination_province',
                'origin_date','destination_date',
                'cargo_code_1','cargo_code_2',
                'origin_line','destination_line',
                'line_routes']
        },
        {'file_name':'OD NCA',
        'sheet_name':None,
        'line_name':'NCA',
        'skiprows':6,
        'start_row':1,
        'end_row':12,
        'columns':['commodity_group','commodity_subgroup','tons', 'kms',
                'origin_date','origin_station','origin_line',
                'destination_date','destination_station','destination_line',
                'line_routes']
        },
    ]

    """Extract provinces
    """
    province_desc = [{'file_name':'OD BCyL Belgrano',
        'sheet_name':'LISTADO ESTACIONES',
        'station_column':'ESTACIOM ORIGEN',
        'province_column':'PROVINCIA ORIGEN'
        },
        {'file_name':'OD BCyL SM y URQ',
        'sheet_name':'PROVINCIAS',
        'station_column':'ESTACION',
        'province_column':'PROVINCIA'
        },
        {'file_name':'OD FEPSA',
        'sheet_name':'ESTACON PRVINCIA',
        'station_column':'ESTACION',
        'province_column':'PROVINCIA'
        },
    ]
    od_ids = ['origin_id','net_origin_name','net_origin_line','net_origin_province','net_origin_operator',
            'destination_id','net_destination_name','net_destination_line','net_destination_province','net_destination_operator',
            'net_distance','net_speed','net_path']

    ref_date = '2015-01-01 00:00:00'
    replace_strings = [('est.',''),('gral.','general'),('pto.',''),('p.s.m.','san martin'),('p.s.l.','san lorenzo'),('p.',''),('cnel.','coronel'),('ing.','ingeniero')]
    provinces_df = []
    for pdes in province_desc: 
        p_df = pd.read_excel(os.path.join(rail_od_folder,'{}.xlsx'.format(pdes['file_name'])),sheet_name=pdes['sheet_name'],encoding='utf-8-sig')
        p_df.rename(columns={pdes['station_column']:'station',pdes['province_column']:'province'},inplace=True)
        provinces_df.append(p_df)

    provinces_df = pd.concat(provinces_df,axis=0,sort='False', ignore_index=True)

    # load provinces and get geometry of the right province
    province_path = os.path.join(incoming_data_path,'2','provincia','Provincias.shp')
    provinces = gpd.read_file(province_path,encoding='utf-8')
    provinces = provinces.to_crs({'init': 'epsg:4326'})
    sindex_provinces = provinces.sindex

    rail_nodes_path = os.path.join(incoming_data_path,'pre_processed_network_data','railways','national_rail','ffcc_nodes.shp')
    rail_nodes = gpd.read_file(rail_nodes_path,encoding='utf-8').fillna(0)
    rail_nodes = rail_nodes.to_crs({'init': 'epsg:4326'})
    rail_nodes.columns = map(str.lower, rail_nodes.columns)
    rail_nodes['provincia'] = rail_nodes.apply(lambda x: extract_gdf_values_containing_nodes(
        x, sindex_provinces, provinces,'nombre'), axis=1)

    del provinces

    '''Add operators
    '''
    rail_edges_path = os.path.join(incoming_data_path,'pre_processed_network_data','railways','national_rail','lineas_ffcc_edges.shp')
    rail_edges = gpd.read_file(rail_edges_path,encoding='utf-8').fillna(0)
    rail_edges.columns = map(str.lower, rail_edges.columns)
    # get the right linelength
    rail_edges['length'] = rail_edges.geometry.apply(line_length)
    rail_edges = rail_edges.reindex(list(rail_edges.columns)[2:]+list(rail_edges.columns)[:2], axis=1)
    # rail_net = ig.Graph.TupleList(rail_edges.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])

    rail_operators = list(set(list(zip(rail_edges['from_node'].values.tolist(),rail_edges['operador'].values.tolist())) + \
                    list(zip(rail_edges['to_node'].values.tolist(),rail_edges['operador'].values.tolist()))))

    rail_nodes['operador'] = 0
    unique_nodes = list(set([x[0] for x in rail_operators]))
    for u in unique_nodes:
        names = ('/').join([x[1] for x in rail_operators if x[0] == u])
        rail_nodes.at[rail_nodes['node_id'] == u,'operador'] = names

    '''Add lines
    '''
    rail_lines = list(set(list(zip(rail_edges['from_node'].values.tolist(),rail_edges['linea'].values.tolist())) + \
                    list(zip(rail_edges['to_node'].values.tolist(),rail_edges['linea'].values.tolist()))))
    unique_nodes = list(set([x[0] for x in rail_lines]))
    for u in unique_nodes:
        names = ('/').join([x[1] for x in rail_lines if x[0] == u])
        rail_nodes.at[rail_nodes['node_id'] == u,'linea'] = names

    '''Add new station names
    '''
    rename_stations = pd.read_excel(os.path.join(data_path,'rail_ods','station_renames.xlsx'),sheet_name='rename').fillna(0)
    new_stations = [x for x in list(rename_stations.itertuples(index=False)) if 'railn' in str(x.od_station_correct)]
    unique_nodes = list(set([x.od_station_correct for x in new_stations]))
    for u in unique_nodes:
        names = ('/').join([x.od_station for x in new_stations if x.od_station_correct == u])
        rail_nodes.at[rail_nodes['node_id'] == u,'nombre'] = names

    
    rail_nodes.to_csv(os.path.join(data_path,'rail_ods','rail_nodes.csv'),encoding='utf-8-sig')
    rail_nodes = rail_nodes[rail_nodes['nombre'] != 0]
    rail_nodes = rail_nodes[['node_id','nombre','linea','provincia','operador']]
    rail_nodes['nombre'] = rail_nodes['nombre'].apply(lambda x:replace_string_characters(x,replace_strings))
    rail_nodes = list(rail_nodes.itertuples(index=False))

    for fd in file_desc:
        file_name = os.path.join(rail_od_folder,'{}.xlsx'.format(fd['file_name']))
        rail_od_dict = pd.read_excel(file_name,sheet_name=fd['sheet_name'],encoding='utf-8-sig')
        if fd['sheet_name'] is None:
            df_list = []
            for name,sheet in rail_od_dict.items():
                df = extract_subset_from_dataframe(sheet,fd['skiprows'],fd['start_row'],fd['end_row'],fd['columns'])
                df['line_name'] = fd['line_name']
                df_list.append(df)
                del df
            
            df = pd.concat(df_list,axis=0,sort='False', ignore_index=True).fillna(0)

        else:
            df = extract_subset_from_dataframe(rail_od_dict,fd['skiprows'],fd['start_row'],fd['end_row'],fd['columns'])
            df['line_name'] = fd['line_name']

        if 'origin_province' not in df.columns.values.tolist():
            df['origin_province'] = df['origin_station'].apply(lambda x:get_province_matches(x,provinces_df))
            df['destination_province'] = df['destination_station'].apply(lambda x:get_province_matches(x,provinces_df))

        df = df.fillna(0)
        df = df[(df['tons']>0) & (df['origin_line'] != 0)]
        df['origin_date'] = df['origin_date'].apply(lambda x:set_reference_date(x,ref_date))
        df['destination_date'] = df['destination_date'].apply(lambda x: set_reference_date(x,ref_date))
        df['time_diff'] = (df.destination_date-df.origin_date).dt.days*24.0 + 1.0*(df.destination_date-df.origin_date).dt.seconds/3600.0
        df['given_speed'] = df['kms']/df['time_diff']

        od_vals = []
        od_mismatch = []
        for iter_,row in df.iterrows():
            origin_station = row['origin_station']
            origin_province = row['origin_province']
            destination_station = row['destination_station']
            destination_province = row['destination_province']
            o_st = station_name_to_node_matches((origin_station,origin_province),rename_stations,replace_strings,fd,rail_nodes)
            d_st = station_name_to_node_matches((destination_station,destination_province),rename_stations,replace_strings,fd,rail_nodes)

            rail_edges_copy = copy.deepcopy(rail_edges)
            rail_edges_copy = rail_edges_copy[(rail_edges_copy['operador'].str.contains(fd['line_name'])) \
                                            | (rail_edges_copy['linea'].str.contains(fd['line_name']))]
            if len(rail_edges_copy.index) > 0:
                od_nodes = list(set(rail_edges_copy['from_node'].values.tolist() + rail_edges_copy['to_node'].values.tolist()))
                rail_net = ig.Graph.TupleList(rail_edges_copy.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])
                full_net = False
            else:
                rail_net = ig.Graph.TupleList(rail_edges.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])
                full_net = True

            if o_st and d_st:
                od_outputs = []
                for o in o_st:
                    for d in d_st:
                        if full_net == False:
                            if (o.node_id in od_nodes) and (d.node_id in od_nodes):
                                path = rail_net.get_shortest_paths(o.node_id, d.node_id, weights='length', output="epath")[0]
                                if not path:
                                    rail_net = ig.Graph.TupleList(rail_edges.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])
                                    path = rail_net.get_shortest_paths(o.node_id, d.node_id, weights='length', output="epath")[0]
                            else:
                                rail_net = ig.Graph.TupleList(rail_edges.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])
                                path = rail_net.get_shortest_paths(o.node_id, d.node_id, weights='length', output="epath")[0]

                        else:
                            path = rail_net.get_shortest_paths(o.node_id, d.node_id, weights='length', output="epath")[0]

                        if path:
                            path_dist = 0
                            edge_path = []
                            for n in path:
                                path_dist += rail_net.es[n]['length']
                                edge_path.append(rail_net.es[n]['g_id'])
                            if row['time_diff'] != 0:
                                sp = 1.0*path_dist/row['time_diff']
                            else:
                                sp = 0

                            od_outputs.append(tuple(list(row)+list(o)+list(d)+[path_dist,sp,edge_path]))
                            if row['kms'] > 0 and 100.0*abs(path_dist - row['kms'])/row['kms'] > 20:
                                od_mismatch.append(tuple(list(row)+list(o)+list(d)+[path_dist,sp,edge_path]))

                if len(od_outputs) > 1:
                    od_outputs = [[od for od in sorted(od_outputs, key=lambda pair: pair[-3])][0]]
                  

                od_vals += od_outputs


            print ('done with {} in {}'.format(iter_,fd['file_name']))

        od_df = pd.DataFrame(od_vals,columns = df.columns.values.tolist() + od_ids)
        od_df.to_excel(excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        excel_writer.save()

        od_mismatch_df = pd.DataFrame(od_mismatch,columns = df.columns.values.tolist() + od_ids)
        od_mismatch_df.to_excel(mismatch_excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        mismatch_excel_writer.save()

        # od_df = pd.read_excel(os.path.join(data_path,'rail_ods','rail_ods_paths_2.xlsx'),sheet_name = fd['file_name'] + ' ' + fd['line_name'],encoding='utf-8-sig')
        # od_df['o_date'] = od_df['origin_date'].dt.date
        # od_com_day_totals = od_df[['origin_id','destination_id','commodity_group','commodity_subgroup','o_date','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup','o_date'])['tons'].sum()
        # od_com_day_totals.to_excel(day_total_excel_writer,fd['file_name'] + ' ' + fd['line_name'],encoding='utf-8-sig')
        # day_total_excel_writer.save()

        # od_com_day_totals = od_com_day_totals.reset_index()
        # od_com_tot = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).sum().rename(columns={'tons': 'total_annual_tons'})
        # od_com_max = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).max().rename(columns={'tons': 'max_daily_tons'})
        # od_com_min = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).min().rename(columns={'tons': 'min_daily_tons'})

        # pd.concat([od_com_tot,od_com_max,od_com_min],axis=1).to_excel(annual_excel_writer,fd['file_name'] + ' ' + fd['line_name'],encoding='utf-8-sig')
        # annual_excel_writer.save()








if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
