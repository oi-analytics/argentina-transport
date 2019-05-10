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
from atra.utils import *
import datetime

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    water_od_folder = os.path.join(incoming_data_path,'5','Puertos')
    file_desc = [{'file_name':'Cargas No Containerizadas - SSPVNYMM',
        'sheet_name':'2017',
        'skiprows':0,
        'excel_columns':['Puerto', 'Año', 'Mes', 'Nombre Del Buque', 'Tipo de Buque',
                        'OMI', 'Bandera', 'TRN', 'Eslora', 'Manga', 'Sitio de Atraque',
                        'Fecha Entrada', 'Hora Entrada', 'Fecha Salida', ' Hora Salida',
                        'País de Procedencia', 'Puerto de Procedencia', 'País de Destino',
                        'Puerto de Destino', 'Tipo de Operación', 'Producto Corregido',
                        'Rubro', 'Trimestre', 'Total Tn', 'Medida', 'Observaciones',
                        'Provincia', 'Región'],
        'columns':['commodity_group','commodity_subgroup','tons',
                'origin_date','origin_port',
                'destination_date','destination_port',
                'trade_type']
        },
        {'file_name':'Contenedores - SSPVNYMM',
        'sheet_name':'2017',
        'skiprows':0,
        'columns':['commodity_group','commodity_subgroup','tons',
                'origin_date','origin_port',
                'destination_date','destination_port',
                'trade_type']
        }
    ]

    file_desc = [{'file_name':'Cargas No Containerizadas - SSPVNYMM',
        'sheet_name':'2017',
        'skiprows':0,
        'excel_columns':['Puerto', 'Mes',
                        'Fecha Entrada', 'Hora Entrada', 'Fecha Salida', ' Hora Salida',
                        'País de Procedencia', 'Puerto de Procedencia', 'País de Destino',
                        'Puerto de Destino', 'Tipo de Operación', 'Producto Corregido',
                        'Rubro', 'Total Tn', 'Medida',
                        'Provincia', 'Región'],
        'columns':['port_name','month','entry_date','entry_time','exit_date','exit_time',
                'origin_country','origin_port',
                'destination_country','destination_port',
                'operation_type','commodity_subgroup',
                'commodity_group','tons',
                'tons_unit','province','port_region'
                ],
        'excel_operations':['Cabotaje Entrado', 'No Operó', 'Cabotaje Salido',
                    'Vehículos Expo', 'Tránsito', 'Otros', 'Vehículos Impo',
                    'Transbordo Impo', 'Exportación', 'Transbordo Expo', 'Importación'],

        'operations':['']

        },
    ]


    ports_data = gpd.read_file(os.path.join(data_path,'network','water_nodes.shp'),encoding='utf-8')
    print (ports_data['name'].values.tolist())
    ref_date = '2017-01-01 00:00:00'
    for fd in file_desc:
        p_df = pd.read_excel(os.path.join(water_od_folder,'{}.xlsx'.format(fd['file_name'])),sheet_name=fd['sheet_name'],encoding='utf-8-sig').fillna(0)
        p_df = p_df[fd['excel_columns']]
        p_df.rename(columns=dict(zip(fd['excel_columns'],fd['columns'])),inplace=True)
        print (list(set(p_df['operation_type'].values.tolist())))
        p_df = p_df[p_df['tons'] > 0]








if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
