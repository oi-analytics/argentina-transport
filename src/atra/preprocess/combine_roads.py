"""
Get Argentina shapefiles and combine them into a single file
"""
import os
import sys
import pandas as pd
import geopandas as gpd

from atra.utils import *

def main():
	config = load_config()
	sectors = 'roads'
	subsects = ['national_roads','province_roads','rural_roads','osm_roads']
	subfolders = ['rutas','','','']
	road_types = ['national','province','rural','osm']
	attributes = [['cod_ruta','sentido'],
		['nombre','clase'],
		['caracteris'],
		['road_name','road_type']]
	input_files = ['rutas.shp','Rutas_provinciales.shp','rural_roads.shp','osm_roads.shp']

	networks = []
	for sb in range(len(subsects)):
		if subsects[sb] == 'national_roads':
			input_data = os.path.join(config['paths']['incoming_data'],'pre_processed_network_data',sectors,subsects[sb],subfolders[sb],input_files[sb])
		else:
			input_data = os.path.join(config['paths']['incoming_data'],'pre_processed_network_data',sectors,subsects[sb],input_files[sb])

		input_df = gpd.read_file(input_data,encoding='utf-8')
		input_df = input_df[attributes[sb] + ['geometry']]
		input_df.rename(columns={'cod_ruta':'road_name','nombre':'road_name',
								'clase':'surface',
								'caracteris':'surface'},inplace=True)
		if road_types[sb] != 'osm':
			input_df['road_type'] = road_types[sb]
		if road_types[sb] == 'national':
			input_df = input_df[input_df['sentido'] == 'A']

		networks.append(input_df)

	networks_file = gpd.GeoDataFrame(pd.concat(networks,ignore_index=True,sort=False),geometry='geometry',crs={'init': 'epsg:4326'})
	networks_file.to_file(os.path.join(config['paths']['incoming_data'],
				'pre_processed_network_data',
				'roads',
				'combined_roads',
				'combined_roads.shp'),encoding='utf-8')

if __name__ == '__main__':
    main()
