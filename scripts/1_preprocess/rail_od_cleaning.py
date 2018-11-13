"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import pandas as pd
import numpy as np

from oia.utils import load_config,  transform_geo_file

def extract_subset_from_dataframe(input_dataframe,skiprows,start_row,end_row,new_columns):
    output_data = []
    input_dataframe = input_dataframe.iloc[skiprows:]
    for iter_,row in input_dataframe.iterrows():
        output_data.append(tuple(row[start_row:end_row]))

    output_df = pd.DataFrame(output_data,columns=new_columns)
    return output_df


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
        'line_name':'FESPA',
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
    od_output_excel = os.path.join(data_path,'rail_ods','rail_ods.xlsx')
    excel_writer = pd.ExcelWriter(od_output_excel)
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

        df = df.fillna(0)
        df = df[(df['tons']>0) & (df['origin_line'] != 0)]
        df.to_excel(excel_writer, fd['file_name'] + ' ' + fd['line_name'], index=False,encoding='utf-8-sig')
        excel_writer.save()
        del df

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
