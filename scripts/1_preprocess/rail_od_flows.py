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

def assign_industry_names(x,industries_df):
    return industries_df.loc[(x.commodity_group,x.commodity_subgroup),'high_level_industry']

def min_max_cost(x,cost_df):
    min_cost = 2.6
    max_cost = 3.8
    for cost in list(cost_df.itertuples(index=False)):
        if unidecode.unidecode(cost.line.lower().strip()) in unidecode.unidecode(x.linea.lower().strip()):
            min_cost = cost.min_cost
            max_cost = cost.max_cost
            break

    return (0.01*min_cost*x.length,0.01*max_cost*x.length)


def rail_cost_function(cost_parameters_dataframe,tonnage,speed,waiting_time,distance):
    '''baseline constant_factor exponent
    '''
    cost_parameters_dataframe = cost_parameters_dataframe.set_index('factor')
    tonnage_cost = cost_parameters_dataframe.loc['tonnage','constant_factor']*np.power(tonnage/cost_parameters_dataframe.loc['tonnage','baseline'],cost_parameters_dataframe.loc['tonnage','exponent'])
    speed_cost = cost_parameters_dataframe.loc['speed','constant_factor']*np.power(speed/cost_parameters_dataframe.loc['speed','baseline'],cost_parameters_dataframe.loc['speed','exponent'])
    distance_cost = cost_parameters_dataframe.loc['distance','constant_factor']*np.power(distance/cost_parameters_dataframe.loc['distance','baseline'],cost_parameters_dataframe.loc['distance','exponent'])
    waiting_time_cost = cost_parameters_dataframe.loc['wait','constant_factor']*waiting_time + cost_parameters_dataframe.loc['wait','exponent']

    return (0.01*(tonnage_cost+speed_cost+distance_cost+waiting_time_cost))


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
    if st_change == 'mendoza' and fd['line_name'].lower().strip() == 'san matrin':
        st_change == 'mendoza pasajeros (goa)'

    for rp in replace_strings:
        st_change = st_change.replace(rp[0],rp[1])

    if fd['line_name'].lower().strip() in (unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip()) for x in rail_nodes):
        
        st_match = [x for x in rail_nodes \
            if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
            and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip()) \
            and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]

        if not st_match:
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]
        
            if not st_match:
                st_match = [x for x in rail_nodes \
                    if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.linea).replace('FFCC','').lower().strip())]


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
            st_match = [x for x in rail_nodes if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and st_prov == unidecode.unidecode(str(x.provincia).lower().strip())]
            if not st_match:
                st_match = [x for x in rail_nodes \
                    if unidecode.unidecode(x.nombre.lower().strip()) == unidecode.unidecode(st_change.lower().strip()) \
                    and fd['line_name'].lower().strip() in unidecode.unidecode(str(x.operador).lower().strip())]

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
    data_path = config['paths']['data']

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
            'net_speed','chosen_speed','net_path','obs_unit_cost','net_unit_cost','net_distance']

    ref_date = '2015-01-01 00:00:00'
    replace_strings = [('est.',''),('gral.','general'),('pto.',''),('p.s.m.','san martin'),('p.s.l.','san lorenzo'),('p.',''),('cnel.','coronel'),('ing.','ingeniero')]
    provinces_df = []
    for pdes in province_desc: 
        p_df = pd.read_excel(os.path.join(rail_od_folder,'{}.xlsx'.format(pdes['file_name'])),sheet_name=pdes['sheet_name'],encoding='utf-8-sig')
        p_df.rename(columns={pdes['station_column']:'station',pdes['province_column']:'province'},inplace=True)
        provinces_df.append(p_df)

    provinces_df = pd.concat(provinces_df,axis=0,sort='False', ignore_index=True)

    cost_df = pd.read_excel(os.path.join(incoming_data_path,'5','rail_od_matrices_06082018','rail_costs.xlsx'),sheet_name='route_costs')
    '''Get industries
    '''
    industries_df = pd.read_excel(os.path.join(data_path,'economic_IO_tables','commodity_classifications-hp.xlsx'),sheet_name='rail',index_col=[0,1])
    industry_cols = list(set(industries_df['high_level_industry'].values.tolist()))
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
    rail_edges['cost'] = rail_edges.apply(lambda x:min_max_cost(x,cost_df),axis=1)
    rail_edges[['min_gcost', 'max_gcost']] = rail_edges['cost'].apply(pd.Series)
    rail_edges.drop('cost', axis=1, inplace=True)

    rail_edges = rail_edges.reindex(list(rail_edges.columns)[2:]+list(rail_edges.columns)[:2], axis=1)
    rail_net = ig.Graph.TupleList(rail_edges.itertuples(index=False), edge_attrs=list(rail_edges.columns)[2:])

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
    rename_stations = pd.read_excel(os.path.join(incoming_data_path,'rail_ods','station_renames.xlsx'),sheet_name='rename').fillna(0)
    new_stations = [x for x in list(rename_stations.itertuples(index=False)) if 'railn' in str(x.od_station_correct)]
    unique_nodes = list(set([x.od_station_correct for x in new_stations]))
    for u in unique_nodes:
        names = ('/').join([x.od_station for x in new_stations if x.od_station_correct == u])
        rail_nodes.at[rail_nodes['node_id'] == u,'nombre'] = names

    print (rail_nodes)
    rail_nodes.to_file(os.path.join(data_path,'network', 'rail_nodes.shp'),encoding = 'utf-8')
    rail_nodes.drop('geometry', axis=1, inplace=True)
    rail_nodes.to_csv(os.path.join(data_path,'network','rail_nodes.csv'),encoding='utf-8',index=False)

    rail_nodes = rail_nodes[rail_nodes['nombre'] != 0]
    rail_nodes = rail_nodes[['node_id','nombre','linea','provincia','operador']]
    rail_nodes['nombre'] = rail_nodes['nombre'].apply(lambda x:replace_string_characters(x,replace_strings))
    rail_nodes = list(rail_nodes.itertuples(index=False))

    
    cost_df = pd.read_excel(os.path.join(incoming_data_path,'5','rail_od_matrices_06082018','rail_costs.xlsx'),sheet_name='baseline_values')

    od_output_excel = os.path.join(incoming_data_path,'rail_ods','rail_ods_paths.xlsx')
    excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(incoming_data_path,'rail_ods','rail_ods_mismatches.xlsx')
    mismatch_excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(incoming_data_path,'rail_ods','rail_ods_daily_totals.xlsx')
    day_total_excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(incoming_data_path,'rail_ods','rail_ods_anuual_and_daily_flows.xlsx')
    annual_excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(incoming_data_path,'rail_ods','province_ods.xlsx')
    province_excel_writer = pd.ExcelWriter(od_output_excel)

    province_ods = []
    od_dfs = []
    edge_speeds = {}
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

        if 'origin_province' not in df.columns.values.tolist() and fd['line_name'] in ('Belgrano','San Martin','Urquiza','FEPSA'):
            df['origin_province'] = df['origin_station'].apply(lambda x:get_province_matches(x,provinces_df))
            df['destination_province'] = df['destination_station'].apply(lambda x:get_province_matches(x,provinces_df))
        else:
            df['origin_province'] = ''
            df['destination_province'] = ''

        df = df.fillna(0)
        df = df[(df['tons']>0) & (df['origin_line'] != 0)]
        df['origin_date'] = df['origin_date'].apply(lambda x:set_reference_date(x,ref_date))
        df['destination_date'] = df['destination_date'].apply(lambda x: set_reference_date(x,ref_date))
        df['time_diff'] = (df.destination_date-df.origin_date).dt.days*24.0 + 1.0*(df.destination_date-df.origin_date).dt.seconds/3600.0
        df['given_speed'] = df['kms']/df['time_diff']

        '''Match industries
        '''
        df['industry_name'] = df.apply(lambda x:assign_industry_names(x,industries_df),axis=1)
        # df.to_csv('test.csv',index = False)

        '''Get OD matches
        '''
        od_vals = []
        od_mismatch = []
        for iter_,row in df.iterrows():
            origin_station = row['origin_station']
            origin_province = row['origin_province']
            destination_station = row['destination_station']
            destination_province = row['destination_province']
            o_st = station_name_to_node_matches((origin_station,origin_province),rename_stations,replace_strings,fd,rail_nodes)
            d_st = station_name_to_node_matches((destination_station,destination_province),rename_stations,replace_strings,fd,rail_nodes)

            if o_st and d_st:
                od_outputs = []
                for o in o_st:
                    for d in d_st:
                        path = rail_net.get_shortest_paths(o.node_id, d.node_id, weights='max_gcost', output="epath")[0]
                        if path:
                            path_dist = 0
                            edge_path = []
                            for n in path:
                                path_dist += rail_net.es[n]['length']
                                edge_path.append(rail_net.es[n]['edge_id'])
                            if row['time_diff'] != 0:
                                sp = 1.0*path_dist/row['time_diff']
                            else:
                                sp = 0

                            if 10 <= row['given_speed'] <= 50:
                                chosen_sp = row['given_speed']
                            elif 10 <= sp <= 50:
                                chosen_sp = sp
                            else:
                                chosen_sp = 20

                            net_unit_cost = rail_cost_function(cost_df,row['tons'],chosen_sp,36,path_dist)
                            obs_unit_cost = rail_cost_function(cost_df,row['tons'],chosen_sp,36,row['kms'])
                            for e in edge_path:
                                if e not in edge_speeds.keys():
                                    edge_speeds[e] = [chosen_sp]
                                else:
                                    edge_speeds[e].append(chosen_sp)

                            od_outputs.append(tuple(list(row)+list(o)+list(d)+[sp,chosen_sp,edge_path,obs_unit_cost,net_unit_cost,path_dist]))
                            if row['kms'] > 0 and 100.0*abs(path_dist - row['kms'])/abs(row['kms']) > 20:
                                od_mismatch.append(tuple(list(row)+list(o)+list(d)+[sp,chosen_sp,edge_path,obs_unit_cost,net_unit_cost,path_dist]))


                if len(od_outputs) > 1:
                    od_outputs = [[od for od in sorted(od_outputs, key=lambda pair: pair[-1])][0]]
                  

                od_vals += od_outputs


            print ('done with {} in {}'.format(iter_,fd['file_name']))


        od_df = pd.DataFrame(od_vals,columns = df.columns.values.tolist() + od_ids)
        od_df.to_excel(excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        excel_writer.save()

        od_df['o_date'] = od_df['origin_date'].dt.date
        od_dfs.append(od_df)

        province_ods.append(od_df.groupby(['net_origin_province','net_destination_province','industry_name'])['tons'].sum().reset_index())

        od_mismatch_df = pd.DataFrame(od_mismatch,columns = df.columns.values.tolist() + od_ids)
        od_mismatch_df.to_excel(mismatch_excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        mismatch_excel_writer.save()

        od_mismatch_df = od_mismatch_df.groupby(['origin_station','destination_station','origin_province','destination_province',
            'origin_id','net_origin_name','net_origin_line','net_origin_province','net_origin_operator',
            'destination_id','net_destination_name','net_destination_line','net_destination_province','net_destination_operator'])['kms','net_distance'].min().reset_index()
        od_mismatch_df.to_excel(mismatch_excel_writer, fd['file_name'] + ' ' + fd['line_name'] + ' pairs', index=False,encoding='utf-8-sig')
        mismatch_excel_writer.save()        

        od_com_day_totals = od_df[['origin_id','destination_id','commodity_group','commodity_subgroup','o_date','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup','o_date'])['tons'].sum()
        od_com_day_totals.to_excel(day_total_excel_writer,fd['file_name'] + ' ' + fd['line_name'],encoding='utf-8-sig')
        day_total_excel_writer.save()

        od_com_day_totals = od_com_day_totals.reset_index()
        od_com_tot = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).sum().rename(columns={'tons': 'total_annual_tons'})
        od_com_max = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).max().rename(columns={'tons': 'max_daily_tons'})
        od_com_min = od_com_day_totals[['origin_id','destination_id','commodity_group','commodity_subgroup','tons']].groupby(['origin_id','destination_id','commodity_group','commodity_subgroup']).min().rename(columns={'tons': 'min_daily_tons'})

        pd.concat([od_com_tot,od_com_max,od_com_min],axis=1).to_excel(annual_excel_writer,fd['file_name'] + ' ' + fd['line_name'],encoding='utf-8-sig')
        annual_excel_writer.save()


    province_ods = pd.concat(province_ods,axis=0,sort='False', ignore_index=True)
    province_ods = province_ods.groupby(['net_origin_province','net_destination_province','industry_name'])['tons'].sum().reset_index()
    province_ods.rename(columns={'net_origin_province':'origin_province','net_destination_province':'destination_province'})
    province_ods.to_excel(province_excel_writer,'rail',index=False,encoding='utf-8-sig')
    province_excel_writer.save()


    od_vals_group_industry = {}
    od_dfs = pd.concat(od_dfs,axis=0,sort='False', ignore_index=True)
    od_dfs.to_csv(os.path.join(incoming_data_path,'rail_ods','all_ods.csv'),index=False,encoding='utf-8-sig')

    # od_dfs = pd.read_csv(os.path.join(incoming_data_path,'rail_ods','all_ods.csv'),encoding='utf-8-sig')

    gr_cols = ['origin_id','destination_id','net_origin_province','net_destination_province','commodity_group','commodity_subgroup','industry_name','o_date']
    od_com_day_totals = od_dfs[gr_cols+['tons']].groupby(gr_cols)['tons'].sum().reset_index()

    gr_cols = ['origin_id','destination_id','net_origin_province','net_destination_province','commodity_group','commodity_subgroup','industry_name']
    od_com_max = od_com_day_totals[gr_cols + ['tons']].groupby(gr_cols).max().rename(columns={'tons': 'max_daily_tons'}).reset_index()
    od_com_min = od_com_day_totals[gr_cols + ['tons']].groupby(gr_cols).min().rename(columns={'tons': 'min_daily_tons'}).reset_index()
    od_minmax = pd.merge(od_com_min,od_com_max,how='left',on=gr_cols).fillna(0)
    
    # print (od_minmax)
    for iter_,row in od_minmax.iterrows():
        if '{}-{}'.format(row.origin_id,row.destination_id) not in od_vals_group_industry.keys():
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)] = {}
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['origin_province'] = row.net_origin_province 
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['destination_province'] = row.net_destination_province
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['min_total_tons'] = row.min_daily_tons
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['max_total_tons'] = row.max_daily_tons
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['min_{}'.format(row.industry_name)] = row.min_daily_tons
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['max_{}'.format(row.industry_name)] = row.max_daily_tons
        else:
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['min_total_tons'] += row.min_daily_tons
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['max_total_tons'] += row.max_daily_tons

            if 'min_{}'.format(row.industry_name) not in od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)].keys():
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['min_{}'.format(row.industry_name)] = row.min_daily_tons
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['max_{}'.format(row.industry_name)] = row.max_daily_tons
            else:
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['min_{}'.format(row.industry_name)] += row.min_daily_tons
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['max_{}'.format(row.industry_name)] += row.max_daily_tons


    od_list = []
    for key,values in od_vals_group_industry.items():
        od_list.append({**{'origin_id':key.split('-')[0],'destination_id':key.split('-')[1]},**values})
    od_df = pd.DataFrame(od_list).fillna(0)
    od_df.to_csv(os.path.join(data_path,'OD_data','rail_ods.csv'),index=False,encoding='utf-8-sig')
    
    del od_list
    
    od_vals_group_industry = {}
    for iter_,row in od_dfs.iterrows():
        if '{}-{}'.format(row.origin_id,row.destination_id) not in od_vals_group_industry.keys():
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)] = {}
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['origin_province'] = row.net_origin_province 
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['destination_province'] = row.net_destination_province
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['total_tons'] = row.tons
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)][row.industry_name] = row.tons
        else:
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['total_tons'] += row.tons
            
            if row.industry_name not in od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)].keys():
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)][row.industry_name] = row.tons
            else:
                od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)][row.industry_name] += row.tons

    od_list = []
    for key,values in od_vals_group_industry.items():
        od_list.append({**{'origin_id':key.split('-')[0],'destination_id':key.split('-')[1]},**values})
    od_df = pd.DataFrame(od_list).fillna(0)
    del od_list

    province_ods = od_df[['origin_province','destination_province']+industry_cols + ['total_tons']]
    province_ods = province_ods.groupby(['origin_province','destination_province'])[industry_cols + ['total_tons']].sum().reset_index()  
    province_ods.to_excel(province_excel_writer,'industries',index=False,encoding='utf-8-sig')
    province_excel_writer.save()

    
    esp = []
    for key,values in edge_speeds.items():
        # speed_vals, cost_vals = list(zip(*values)) 
        # esp.append((key,min(speed_vals),max(speed_vals),min(cost_vals),max(cost_vals)))
        esp.append((key,min(values),max(values)))

    # esp_df = pd.DataFrame(esp,columns=['edge_id','min_speed','max_speed','min_gcost','max_gcost'])
    esp_df = pd.DataFrame(esp,columns=['edge_id','min_speed','max_speed'])
    rail_edges = pd.merge(rail_edges,esp_df,how='left',on=['edge_id']).fillna(0)
    rail_edges.loc[rail_edges['min_speed'] == 0,'min_speed'] = 20
    rail_edges.loc[rail_edges['max_speed'] == 0,'max_speed'] = 20
    rail_edges['min_time'] = rail_edges['length']/rail_edges['max_speed']
    rail_edges['max_time'] = rail_edges['length']/rail_edges['min_speed']

    rail_edges.to_file(os.path.join(data_path,'network','rail_edges.shp'),encoding = 'utf-8')
    rail_edges.drop('geometry', axis=1, inplace=True)
    rail_edges.to_csv(os.path.join(data_path,'network','rail_edges.csv'),encoding='utf-8',index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
