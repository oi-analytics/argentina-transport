"""Combine the OD matrices of different modes to create a total OD matrix 
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


def main(config):
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    modes = ['road','rail','port']
    
    province_excel_writer = pd.ExcelWriter(os.path.join(data_path,'OD_data','province_ods.xlsx'))

    all_ods = []
    for m in range(len(modes)):
        od_df = pd.read_csv(os.path.join(data_path,'OD_data','{}_province_annual_ods.csv'.format(modes[m])),encoding='utf-8-sig')
        all_ods.append(od_df)

        od_df.to_excel(province_excel_writer,modes[m],index=False,encoding='utf-8-sig')
        province_excel_writer.save()



    all_ods = pd.concat(all_ods,axis=0,sort='False', ignore_index=True).fillna(0)
    industry_cols = [cols for cols in all_ods.columns.values.tolist() if cols not in ['origin_province','destination_province']]

    province_ods = all_ods.groupby(['origin_province','destination_province'])[industry_cols].sum().reset_index() 
    province_ods.to_excel(province_excel_writer,'total',index=False,encoding='utf-8-sig')
    province_excel_writer.save()




if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
