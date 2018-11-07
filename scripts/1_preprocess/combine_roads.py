"""
Get vietnam shapefiles and convert them into networks
@author: Raghav Pant
Date: June 25, 2018
"""
import os
import sys
import pandas as pd
import geopandas as gpd

from oia.utils import *
import network_create as nc

def main():
	config = load_config()
	sectors = 'roads'
	subsects = ['national_roads','province_roads','rural_roads']
	road_types = ['national','province','rural']
	attributes = [['gid','distrito','ruta','limites_de','inicio_km','fin_km','tmda'],
		['tipo','nombre','clase','transitabi','provincia','codigo'],
		['gid','caracteris','c_cantidad','provincia']]
	input_files = ['tmda_roads.shp','Rutas_provinciales.shp','rural_roads.shp']

	networks = []
	for sb in range(len(subsects)):
		input_data = os.path.join(config['paths']['data'],'pre_processed_data',sectors,subsects[sb],input_files[sb])
		input_df = gpd.read_file(input_data,encoding='utf-8')
		input_df = input_df[attributes[sb] + ['geometry']]
		input_df.rename(columns={'ruta':'road_no','nombre':'road_no','tipo':'purpose',
								'c_cantidad':'purpose','clase':'surface',
								'caracteris':'surface','provincia':'province','distrito':'province'},inplace=True)
		input_df['road_type'] = road_types[sb]
		if road_types[sb] == 'national':
			input_df['surface'] = 'Paved'
		networks.append(input_df)

	networks_file = gpd.GeoDataFrame(pd.concat(networks,ignore_index=True,sort=False),geometry='geometry',crs={'init': 'epsg:4326'})
	networks_file.to_file(os.path.join(config['paths']['data'],'pre_processed_data','roads','combined_roads','combined_roads.shp'),encoding='utf-8')

if __name__ == '__main__':
    main()
