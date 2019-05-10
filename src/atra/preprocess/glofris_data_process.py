# -*- coding: utf-8 -*-
"""
Created on Tue September 18 10:35:55 2018

@authors: Raghav Pant, Tom Russell, elcok
"""

import os
import subprocess
import json
import sys
import fiona
import fiona.crs
import rasterio
import numpy as np
import pandas as pd
import geopandas as gpd
from netCDF4 import Dataset
from osgeo import gdal
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping
from rasterio.features import shapes

from atra.utils import *

def glofris_data_details(root_dir):
	f_all = []
	for root, dirs, files in os.walk(root_dir):
		for file in files:
			if file.endswith(".tif") or file.endswith(".tiff"):
				fname = file.split('.tif')
				fname = fname[0]
				print (fname)
				if '2030' in fname:
					year = 2030
				else:
					year = 2016

				if 'rcp4p5' in fname:
					sc = 'rcp 4.5'
				elif 'rcp8p5' in fname:
					sc = 'rcp 8.5'
				else:
					sc = 'none'

				f_all.append((fname,'flooding',year,sc,1.0/float(fname[-5:])))

	df = pd.DataFrame(f_all,columns = ['file_name',	'hazard_type',	'year',	'climate_scenario',	'probability'])
	df.to_csv(os.path.join(root_dir,'glofris_files.csv'),index = False)

def raster_rewrite(in_raster,out_raster,nodata):
	with rasterio.open(in_raster) as dataset:
		data_array = dataset.read()
		data_array[np.where(np.isnan(data_array))] = nodata

		with rasterio.open(out_raster, 'w', driver='GTIff',
					height=data_array.shape[1],    # numpy of rows
					width=data_array.shape[2],     # number of columns
					count=dataset.count,                        # number of bands
					dtype=data_array.dtype,  # this must match the dtype of our array
					crs=dataset.crs,
					transform=dataset.transform) as out_data:
			out_data.write(data_array)  # optional second parameter is the band number to write to
			out_data.nodata = -1  # set the raster's nodata value


	os.remove(in_raster)
	os.rename(out_raster,in_raster)

def convert_geotiff_to_vector_with_threshold(from_threshold,to_threshold, infile, infile_epsg,tmpfile_1, tmpfile_2, outfile):
	"""Threshold raster, convert to polygons, assign crs
	"""
	args = [
		"gdal_calc.py",
		'-A', infile,
		'--outfile={}'.format(tmpfile_1),
		'--calc=logical_and(A>={0}, A<{1})'.format(from_threshold,to_threshold),
		'--type=Byte', '--NoDataValue=0',
		'--co=SPARSE_OK=YES',
		'--co=NBITS=1',
		'--quiet',
		'--co=COMPRESS=LZW'
	]
	subprocess.run(args)

	subprocess.run([
		"gdal_edit.py",
		'-a_srs', 'EPSG:{}'.format(infile_epsg),
		tmpfile_1
	])

	subprocess.run([
		"gdal_polygonize.py",
		tmpfile_1,
		'-q',
		'-f', 'ESRI Shapefile',
		tmpfile_2
	])

	subprocess.run([
		"ogr2ogr",
		'-a_srs', 'EPSG:{}'.format(infile_epsg),
		'-t_srs', 'EPSG:4326',
		outfile,
		tmpfile_2
	])

	subprocess.run(["rm", tmpfile_1])
	subprocess.run(["rm", tmpfile_2])
	subprocess.run(["rm", tmpfile_2.replace('shp', 'shx')])
	subprocess.run(["rm", tmpfile_2.replace('shp', 'dbf')])
	subprocess.run(["rm", tmpfile_2.replace('shp', 'prj')])


def main(config):
	data_path = config['paths']['data']
	incoming_path = config['paths']['incoming_data']

	# threshold based datasets
	thresholds = [1,2,3,4,999]
	boundary_file = os.path.join(data_path,'boundaries','admin_0_boundaries.shp')
	get_boundary = gpd.read_file(boundary_file)
	get_boundary = get_boundary[get_boundary['ISO_A3'] == 'ARG']

	get_boundary_to_json = get_boundary.to_json()
	get_boundary_to_json_dict = json.loads(get_boundary_to_json)
	clip_boundary = [feature["geometry"] for feature in get_boundary_to_json_dict["features"]]

	del get_boundary, get_boundary_to_json, get_boundary_to_json_dict

	model_types = ['WATCH','RCP45','RCP85']
	for m in range(len(model_types)):
		model = model_types[m]
		root_dir = os.path.join(incoming_path,'Global_GLOFRIS_data',model)
		arg_dir = os.path.join(data_path,'flood_data','GLOFRIS',model)

		for root, dirs, files in os.walk(root_dir):
			for file in files:
				if file.endswith(".nc"):
					with rasterio.open(os.path.join(root, file)) as src:
						meta_data = src.meta
						print ('* Read meta data')

					dataset = Dataset(os.path.join(root, file))
					rp = int(file[-8:-3])
					proj = dataset.variables['projection']
					nv = dataset.variables['{}-year_of_inundation_depth'.format(rp)]
					data = np.ma.masked_greater(nv, 1e10)

					global_raster = os.path.join(root, file[:-3]+'.tif')
					with rasterio.open(global_raster, 'w', driver='GTIff',
							height=data.shape[1],    # numpy of rows
							width=data.shape[2],     # number of columns
							count=1,                        # number of bands
							dtype=meta_data['dtype'],  # this must match the dtype of our array
							crs=proj.EPSG_code,
							compress='lzw',
							transform=meta_data['transform']) as out_data:
						out_data.write(data[:,::-1,:])  # optional second parameter is the band number to write to
						out_data.nodata = -1  # set the raster's nodata value

					del data

					print ('* Created global raster')
					with rasterio.open(global_raster) as src:
						out_image, out_transform = mask(src, clip_boundary, crop=True)

					# print (out_image)
					arg_raster = os.path.join(arg_dir, 'ARG_' + file[:-3]+'.tif')
					with rasterio.open(arg_raster, 'w', driver='GTiff',
								height=out_image.shape[1],
								width=out_image.shape[2],
								count=1,
								dtype=out_image.dtype,
								crs=proj.EPSG_code,
								compress='lzw',
								transform=out_transform) as dst:
						dst.write(out_image[0], 1)

					print ('* Created Argentina raster')
					os.remove(global_raster)
					# threshold based datasets
					thresholds = [1,2,3,4,10]
					for t in range(len(thresholds)-1):
						thr_1 = thresholds[t]
						thr_2 = thresholds[t+1]
						in_file = arg_raster
						tmp_1 = os.path.join(arg_dir, 'ARG_' + file[:-3]+'_mask.tif')
						tmp_2 = os.path.join(arg_dir, 'ARG_' + file[:-3]+'_mask.shp')
						out_file = os.path.join(arg_dir, 'ARG_' + file[:-3]+'_{0}m-{1}m_threshold.shp'.format(thr_1,thr_2))
						convert_geotiff_to_vector_with_threshold(thr_1,thr_2,in_file,4326,tmp_1, tmp_2, out_file)

						print ('* Created shapefile',t)

					print ('* Done with file',file)

	arg_dir = os.path.join(data_path,'flood_data','GLOFRIS')
	glofris_data_details(arg_dir)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
