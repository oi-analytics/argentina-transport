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
from oia.utils import *

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

def assign_industry_names(x,industries_df):
    return industries_df.loc[(x.commodity_group,x.commodity_subgroup),'high_level_industry']

def set_reference_date(x,reference_date):
    if x == 0:
        x = pd.Timestamp(reference_date)

    return x

def port_name_to_node_matches(port_reference,named_port,commodity_group,country,port_nodes,port_renames,port_countries):
    if unidecode.unidecode(str(named_port).lower().strip()) in ('rada','rada exterior','transito'):
        named_port = 'Unknown'

    port_match = [x for x in list(port_nodes.itertuples(index=False)) \
        if (unidecode.unidecode(port_reference.lower().strip()) == unidecode.unidecode(x.name.lower().strip()))
        or (unidecode.unidecode(port_reference.lower().strip()) in unidecode.unidecode(x.name.lower().strip()))
        ]

    p_rename = [x.port for x in list(port_renames.itertuples(index=False)) \
        if (unidecode.unidecode(str(named_port).lower().strip()) == unidecode.unidecode(x.od_port.lower().strip()))
        and (unidecode.unidecode(commodity_group.lower().strip()) == unidecode.unidecode(x.commodity_group.lower().strip()))
        ]
    if not p_rename:
        p_rename = [x.port for x in list(port_renames.itertuples(index=False)) \
            if (unidecode.unidecode(str(named_port).lower().strip()) == unidecode.unidecode(x.od_port.lower().strip()))
            and (unidecode.unidecode(x.commodity_group.lower().strip()) in ('all','other'))
            ]
        if not p_rename:
            p_rename = [x.node for x in list(port_countries.itertuples(index=False)) \
                if (unidecode.unidecode(str(named_port).lower().strip()) == unidecode.unidecode(x.port_name.lower().strip())) 
                ]
            if not p_rename:
                p_rename = [x.node for x in list(port_countries.itertuples(index=False)) \
                if (unidecode.unidecode(str(country).lower().strip()) == unidecode.unidecode(str(x.country).lower().strip()))
                and (unidecode.unidecode(x.port_name.lower().strip()) in ('all','other')) 
                ]
                if p_rename:
                    named_port = p_rename[0]
            else:
                named_port = p_rename[0]

        else:
            named_port = p_rename[0]
    else:
        named_port = p_rename[0]


    st_match = [x for x in port_match \
        if (unidecode.unidecode(str(named_port).lower().strip()) == unidecode.unidecode(port_reference.lower().strip()))
        or (unidecode.unidecode(str(named_port).lower().strip()) in unidecode.unidecode(port_reference.lower().strip()))
        or (unidecode.unidecode(port_reference.lower().strip()) in unidecode.unidecode(str(named_port).lower().strip()))
        or (named_port == x.id)
        ]

    if not st_match:
        st_match = [x for x in list(port_nodes.itertuples(index=False)) \
            if (unidecode.unidecode(str(named_port).lower().strip()) == unidecode.unidecode(x.name.lower().strip()))
            or (unidecode.unidecode(str(named_port).lower().strip()) in unidecode.unidecode(x.name.lower().strip()))
            or (unidecode.unidecode(x.name.lower().strip()) in unidecode.unidecode(str(named_port).lower().strip()))
            or (named_port == x.id)
            ]
        if not st_match:
            st_match = port_match

    return st_match
                

def main(config):
    """
    Flanders Marine Institute (2018). 
    Maritime Boundaries Geodatabase: Maritime Boundaries and Exclusive Economic Zones (200NM), version 10. 
    Available online at http://www.marineregions.org/ https://doi.org/10.14284/312
    """
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    translate_columns = {
        'Puerto':'port',
        'mes':'month',
        'Fecha Entrada':'entrance_date',
        'Hora Entrada':'entrance_time',
        'Fecha Salida':'exit_date',
        'Hora Salida':'exit_time',
        'País de Procedencia':'origin_country',
        'Puerto de Procedencia':'origin_port',
        'País de Destino':'destination_country',
        'Puerto de Destino':'destination_port',
        'Tipo de Operación':'operation_type',
        'Producto Corregido':'commodity_subgroup',
        'Rubro':'commodity_group',
        'Total Tn':'tons',
        'Medida':'unit',
        'Contenedores Totales':'total_containers',
        'TEUS Totales':'total_teus'
    }
    ref_date = '2017-01-01 00:00:00'
    export_operations = ['Exportación','Vehículos Expo','Transbordo Expo','Cabotaje Salido']
    import_operations = ['Importación','Transbordo Impo','Vehículos Impo','Cabotaje Entrado']
    transit_operattions = ['Tránsito','Otros'] 
    port_df = gpd.read_file(os.path.join(data_path,'network','water_nodes.shp'),encoding='utf-8').fillna('none')
    port_df.crs = {'init' :'epsg:4326'}
    # port_df.rename(columns={'id':'node_id'},inplace=True)
    port_df.to_file(os.path.join(data_path,'network','port_nodes.shp'),encoding = 'utf-8')
    port_names = port_df[['name','id','province']]


    port_renames = pd.read_excel(os.path.join(incoming_data_path,'port_ods','od_port_matches.xlsx'),sheet_name='matches',encoding='utf-8-sig')
    port_countries = pd.read_excel(os.path.join(incoming_data_path,'port_ods','od_port_matches.xlsx'),sheet_name='country_ports',encoding='utf-8-sig')

    port_df = pd.read_excel(os.path.join(incoming_data_path,'5','Puertos','Cargas No Containerizadas - SSPVNYMM.xlsx'),sheet_name='2017',encoding='utf-8-sig').fillna(0)
    port_df.columns = port_df.columns.str.strip()
    port_df.rename(columns=translate_columns,inplace=True)
    port_df = port_df[port_df['tons'] > 0]
    od_ports = []
    od_matrix = []
    for p in list(port_df.itertuples(index=False)):
        port_id = [x.id for x in list(port_names.itertuples(index=False)) \
                if (unidecode.unidecode(p.port.lower().strip()) == unidecode.unidecode(x.name.lower().strip()))
                or (unidecode.unidecode(p.port.lower().strip()) in unidecode.unidecode(x.name.lower().strip()))
                ][0]
        port_province = [x.province for x in list(port_names.itertuples(index=False)) \
                if (unidecode.unidecode(p.port.lower().strip()) == unidecode.unidecode(x.name.lower().strip()))
                or (unidecode.unidecode(p.port.lower().strip()) in unidecode.unidecode(x.name.lower().strip()))
                ][0]
        if port_province.lower().strip() == 'ciudad bs as':
            port_province = 'Ciudad Autónoma de Buenos Aires'

        match = port_name_to_node_matches(p.port,p.origin_port,p.commodity_group,p.origin_country,port_names[['name','id']],port_renames,port_countries)
        o_id = [m.id for m in match][0]
        o_province = [x.province for x in list(port_names.itertuples(index=False)) \
                if x.id == o_id
                ][0]
        if o_province == 'none':
            o_province = 'Rest of World'
        elif o_province.lower().strip() == 'ciudad bs as':
            o_province = 'Ciudad Autónoma de Buenos Aires'

        match = port_name_to_node_matches(p.port,p.destination_port,p.commodity_group,p.destination_country,port_names[['name','id']],port_renames,port_countries)
        d_id = [m.id for m in match][0]
        d_province = [x.province for x in list(port_names.itertuples(index=False)) \
                if x.id == d_id
                ][0]
        if d_province == 'none':
            d_province = 'Rest of World'
        elif d_province.lower().strip() == 'ciudad bs as':
            d_province = 'Ciudad Autónoma de Buenos Aires'

        od_ports.append((o_id,p.origin_port,p.origin_country,port_id,p.port,port_province,d_id, \
            p.destination_port,p.destination_country,p.operation_type,p.commodity_group,p.commodity_subgroup,p.entrance_date,p.entrance_time,p.exit_date,p.exit_time,p.tons,p.unit))

        if p.operation_type in export_operations:
            operation = 'Export'
        elif p.operation_type in import_operations:
            operation = 'Import'
        else:
            operation = 'Transit'

        if p.unit.lower().strip() == 'unidades':
            tons = 15*p.tons
        else:
            tons = p.tons

        if len(set([o_id,port_id,d_id])) == 1:
            if operation in ['Export','Transit']:
                od_matrix.append((port_id,port_province,'watern_90','Rest of World',operation, \
                    p.commodity_group,p.commodity_subgroup,p.entrance_date,p.exit_date,tons))
            else:
                od_matrix.append(('watern_90','Rest of World',port_id,port_province,operation, \
                    p.commodity_group,p.commodity_subgroup,p.entrance_date,p.exit_date,tons))

        elif len(set([o_id,port_id,d_id])) == 2:
            if o_id != port_id:
                d_id = o_id
                d_province = o_province
            if operation in ['Export','Transit']:
                origin_id = port_id
                origin_province = port_province
                destination_id = d_id
                destination_province = d_province
            else:
                origin_id = d_id
                origin_province = d_province
                destination_id = port_id
                destination_province = port_province

            od_matrix.append((origin_id,origin_province,destination_id,destination_province,operation, \
                    p.commodity_group,p.commodity_subgroup,p.entrance_date,p.exit_date,tons))
        else:
            od_matrix.append((o_id,o_province,port_id,port_province,operation, \
                    p.commodity_group,p.commodity_subgroup,p.entrance_date,p.exit_date,tons))
            od_matrix.append((port_id,port_province,d_id,d_province,operation, \
                    p.commodity_group,p.commodity_subgroup,p.entrance_date,p.exit_date,tons))

    '''Get industries
    '''
    industries_df = pd.read_excel(os.path.join(data_path,'economic_IO_tables','commodity_classifications-hp.xlsx'),sheet_name='port',index_col=[0,1])
    industry_cols = list(set(industries_df['high_level_industry'].values.tolist()))


    # excel_writer = pd.ExcelWriter(os.path.join(incoming_data_path,'port_ods','od_flows.xlsx'))
    od_dfs = pd.DataFrame(od_ports,columns=['origin_id','origin_port','origin_country',
                'intermediate_id','intermediate_port','intermediate_province',
                'destination_id','destination_port','destination_country',
                'operation_type','commodity_group','commodity_subgroup',
                'entrance_date','entrance_time','exit_date','exit_time','tons','unit'])
    od_dfs['industry_name'] = od_dfs.apply(lambda x:assign_industry_names(x,industries_df),axis=1)
    od_dfs.to_csv(os.path.join(incoming_data_path,'port_ods','od_flows_raw.csv'),encoding='utf-8-sig',index=False)
    # od_dfs.to_excel(excel_writer,'od_flows_raw',encoding='utf-8-sig',index=False)
    # excel_writer.save()


    '''Match industries
    '''
    od_dfs = pd.DataFrame(od_matrix,columns=['origin_id','origin_province',
        'destination_id','destination_province',
        'operation_type','commodity_group','commodity_subgroup',
        'entrance_date','exit_date','tons'])
    od_dfs['entrance_date'] = od_dfs['entrance_date'].apply(lambda x:set_reference_date(x,ref_date))
    od_dfs['o_date'] = od_dfs['entrance_date'].dt.date
    od_dfs['industry_name'] = od_dfs.apply(lambda x:assign_industry_names(x,industries_df),axis=1)
    od_dfs.to_csv(os.path.join(incoming_data_path,'port_ods','od_matrix.csv'),encoding='utf-8-sig',index=False)
    # od_dfs.to_excel(excel_writer,'od_matrix',encoding='utf-8-sig',index=False)
    # excel_writer.save()

    od_vals_group_industry = {}
    
    gr_cols = ['origin_id','destination_id','origin_province','destination_province','commodity_group','commodity_subgroup','industry_name','o_date']
    od_com_day_totals = od_dfs[gr_cols+['tons']].groupby(gr_cols)['tons'].sum().reset_index()
    od_dfs[['o_date','tons']].groupby('o_date')['tons'].sum().reset_index().to_csv(os.path.join(incoming_data_path,'port_ods','od_daily_total.csv'),encoding='utf-8-sig',index=False)

    gr_cols = ['origin_id','destination_id','origin_province','destination_province','commodity_group','commodity_subgroup','industry_name']
    od_com_max = od_com_day_totals[gr_cols + ['tons']].groupby(gr_cols).max().rename(columns={'tons': 'max_daily_tons'}).reset_index()
    od_com_min = od_com_day_totals[gr_cols + ['tons']].groupby(gr_cols).min().rename(columns={'tons': 'min_daily_tons'}).reset_index()
    od_minmax = pd.merge(od_com_min,od_com_max,how='left',on=gr_cols).fillna(0)
    
    # print (od_minmax)
    for iter_,row in od_minmax.iterrows():
        if '{}-{}'.format(row.origin_id,row.destination_id) not in od_vals_group_industry.keys():
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)] = {}
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['origin_province'] = row.origin_province 
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['destination_province'] = row.destination_province
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
    od_df.to_csv(os.path.join(data_path,'OD_data','port_nodes_daily_ods.csv'),index=False,encoding='utf-8-sig')
    
    del od_list
    
    od_vals_group_industry = {}
    for iter_,row in od_dfs.iterrows():
        if '{}-{}'.format(row.origin_id,row.destination_id) not in od_vals_group_industry.keys():
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)] = {}
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['origin_province'] = row.origin_province 
            od_vals_group_industry['{}-{}'.format(row.origin_id,row.destination_id)]['destination_province'] = row.destination_province
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
    province_ods.to_csv(os.path.join(data_path,'OD_data','port_province_annual_ods.csv'),index=False,encoding='utf-8-sig')  
    # province_ods.to_excel(province_excel_writer,'industries',index=False,encoding='utf-8-sig')
    # province_excel_writer.save()

    '''Add operators
    '''
    port_edges_path = os.path.join(data_path,'network','water_edges.shp')
    port_edges = gpd.read_file(port_edges_path,encoding='utf-8').fillna(0)
    port_edges.columns = map(str.lower, port_edges.columns)
    port_edges.rename(columns={'id':'edge_id','from_id':'from_node','to_id':'to_node'},inplace=True)
    port_edges = port_edges[['from_node','to_node','edge_id','geometry']]
    # get the right linelength
    port_edges['length'] = port_edges.geometry.apply(line_length)
    port_edges['min_speed'] = 4.0
    port_edges['max_speed'] = 5.0
    port_edges['min_time'] = port_edges['length']/port_edges['max_speed']
    port_edges['max_time'] = port_edges['length']/port_edges['min_speed']

    cost_df = pd.read_excel(os.path.join(incoming_data_path,'5','Puertos','port_costs.xlsx'),sheet_name='costs')
    port_edges['min_gcost'] = cost_df['min_cost'].values[0]
    port_edges['max_gcost'] = cost_df['max_cost'].values[0]
    port_edges.crs = {'init' :'epsg:4326'}

    port_edges.to_file(os.path.join(data_path,'network','port_edges.shp'),encoding = 'utf-8')
    port_edges.drop('geometry', axis=1, inplace=True)
    port_edges.to_csv(os.path.join(data_path,'network','port_edges.csv'),encoding='utf-8',index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
