"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import pandas as pd
import geopandas as gpd
import numpy as np
import unidecode
from atra.utils import *

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
                'cargo_code_1','cargo_code_2',
                'origin_date','destination_date',
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

    match_list = []
    nomatch_list = []
    od_output_excel = os.path.join(data_path,'rail_ods','rail_ods.xlsx')
    excel_writer = pd.ExcelWriter(od_output_excel)

    match_excel = os.path.join(data_path,'rail_ods','station_matches.xlsx')
    match_writer = pd.ExcelWriter(match_excel)
    commodity_list = []
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
        df.to_excel(excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        excel_writer.save()

        commodity_list.append(df[['commodity_group','commodity_subgroup','tons']])
        all_stations = list(set(list(zip(df['origin_station'].values.tolist(),df['origin_province'].values.tolist())) \
                        + list(zip(df['destination_station'].values.tolist(),df['destination_province'].values.tolist()))))
        del df
        for st in all_stations:
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
            if st_match:
                # print (st[0],st_match)
                # provinces = list(set([x.provincia for x in st_match]))
                # if len(st_match) > 1:
                #     print (st[0],st_match)

                for sm in st_match:
                    if st[1] != 0 and str(st[1]).strip() != '':
                        if str(st[1]).lower().strip() != unidecode.unidecode(str(sm.provincia).lower().strip()):
                            print (st,sm)

                    match_list.append(tuple([st[0],st[1]] + list(sm)))

            else:
                # print (st[0], 'NO MATCH')
                nomatch_list.append((st[0],st[1]))


    match_df = pd.DataFrame(match_list,columns=['od_station','od_province','node_id','nombre','linea','provincia','operador'])
    match_df.to_excel(match_writer,'match', index=False,encoding='utf-8-sig')
    match_writer.save()

    nomatch_df = pd.DataFrame(nomatch_list,columns=['od_station','province'])
    nomatch_df.to_excel(match_writer,'nomatch', index=False,encoding='utf-8-sig')
    match_writer.save()

    excel_writer = pd.ExcelWriter('test.xlsx')
    commodity_list = pd.concat(commodity_list,axis=0,sort='False', ignore_index=True)
    commodity_list = commodity_list[['commodity_group','commodity_subgroup','tons']].groupby(['commodity_group','commodity_subgroup'])['tons'].sum()
    commodity_list.to_excel(excel_writer,'rail',encoding='utf-8-sig')
    excel_writer.save()

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
