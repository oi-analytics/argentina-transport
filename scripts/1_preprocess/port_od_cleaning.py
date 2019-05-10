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
from atra.utils import load_config,  transform_geo_file

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
        'Contenedores Totales':'total_containers',
        'TEUS Totales':'total_teus'
    }


    port_df = gpd.read_file(os.path.join(data_path,'network','water_nodes.shp'),encoding='utf-8').fillna('none')
    # port_names = []
    # for p in list(port_df.itertuples(index=False)):
    #     port_names += list(zip(p.name.split('/'),[p.id]*len(p.name.split('/'))))

    # port_names = pd.DataFrame(port_names,columns = ['name','id'])
    port_names = port_df[['name','id']]


    port_renames = pd.read_excel(os.path.join(incoming_data_path,'port_ods','od_port_matches.xlsx'),sheet_name='matches',encoding='utf-8-sig')
    port_countries = pd.read_excel(os.path.join(incoming_data_path,'port_ods','od_port_matches.xlsx'),sheet_name='country_ports',encoding='utf-8-sig')

    port_df = pd.read_excel(os.path.join(incoming_data_path,'5','Puertos','Cargas No Containerizadas - SSPVNYMM.xlsx'),sheet_name='2017',encoding='utf-8-sig').fillna(0)
    port_df.rename(columns=translate_columns,inplace=True)
    match_ports = []
    no_ports = []
    for p in list(port_df.itertuples(index=False)):
        match = port_name_to_node_matches(p.port,p.origin_port,p.commodity_group,p.origin_country,port_names,port_renames,port_countries)
        if match:
            if len(match) > 1:
                print ('More than 1 match for origin:',p.origin_port,match)
            for m in match:
                match_ports.append((p.port,p.origin_port,p.origin_country,p.origin_port,p.destination_port,p.commodity_group,m.name,m.id))
        else:
            no_ports.append((p.port,p.origin_port,p.origin_country,p.commodity_group))

        match = port_name_to_node_matches(p.port,p.destination_port,p.commodity_group,p.destination_country,port_names,port_renames,port_countries)
        if match:
            if len(match) > 1:
                print ('More than 1 match for destination:',p.destination_port,match)
            for m in match:
                match_ports.append((p.port,p.destination_port,p.destination_country,p.origin_port,p.destination_port,p.commodity_group,m.name,m.id))
        else:
            no_ports.append((p.port,p.destination_port,p.destination_country,p.commodity_group))


    excel_writer = pd.ExcelWriter(os.path.join(incoming_data_path,'port_ods','matches_and_nomatches_v2.xlsx'))
    pd.DataFrame(list(set(match_ports)),columns=['port','od_port','od_country','origin_port','destination_port','commodity_group','gis_port','id']).to_excel(excel_writer,'matches',encoding='utf-8-sig')
    excel_writer.save()
    pd.DataFrame(list(set(no_ports)),columns=['port','od_port','od_country','commodity_group']).to_excel(excel_writer,'no_matches',encoding='utf-8-sig')
    excel_writer.save()
    countries = list(set(port_df['origin_country'].values.tolist() + port_df['destination_country'].values.tolist()))
    pd.DataFrame(countries,columns=['country']).to_excel(excel_writer,'countries',encoding='utf-8-sig')
    excel_writer.save()

    excel_writer = pd.ExcelWriter(os.path.join(incoming_data_path,'port_ods','port_od_commodities.xlsx'))
    commodity_list = port_df[['commodity_group','commodity_subgroup','tons']].groupby(['commodity_group','commodity_subgroup'])['tons'].sum()
    commodity_list.to_excel(excel_writer,'port',encoding='utf-8-sig')
    excel_writer.save()



    # port_df = pd.read_excel(os.path.join(incoming_data_path,'5','Puertos','Contenedores - SSPVNYMM.xlsx'),sheet_name='2017',encoding='utf-8-sig').fillna(0)
    # # print (port_df)
    # port_df.rename(columns=translate_columns,inplace=True)
    # od_pairs = list(set(list(zip(port_df['origin_port'].values.tolist(),port_df['destination_port'].values.tolist()))))
    # # print (od_pairs)




if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
