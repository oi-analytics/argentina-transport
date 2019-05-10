"""Plot country and administrative areas
"""
import os
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from atra.utils import *
import matplotlib as mpl
import geopandas

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 11.

#mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 14.
mpl.rcParams['xtick.labelsize'] = 11.
mpl.rcParams['ytick.labelsize'] = 11.
mpl.rcParams['savefig.pad_inches'] = 0.05

def main(config):
	"""Read shapes, plot map
	"""
	# for f_i in range(len(figure_names)):
	output_file = os.path.join(config['paths']['figures'], 'bueans-aires-flooding.png')

	extent_file = provinces_filename = os.path.join(config['paths']['data'],'boundaries','admin_1_boundaries.shp')
	record_names = []
	num = 0
	for record in shpreader.Reader(extent_file).records():
		record_names.append((num,record.attributes['name'].lower().strip()))
		num += 1

	extent_region = [r for (n,r) in record_names if n == 22][0]
	extent_geom = [record.geometry.bounds for record in shpreader.Reader(extent_file).records() if record.attributes['name'].lower().strip() == extent_region]
	print (extent_geom)
	ax = get_axes(extent = extent_geom[0])
	plot_basemap(ax, config['paths']['data'])
	scale_bar(ax, location=(0.8, 0.05))
	plot_basemap_labels(ax, config['paths']['data'], include_regions=True,include_zorder=1)

	proj_lat_lon = ccrs.PlateCarree()

	depths = ['015','025','040','090','160']
	colors = ['#d0d1e6','#a6bddb','#74a9cf','#2b8cbe','#045a8d']
	for d in range(len(depths)):
		hazard_file = os.path.join(config['paths']['incoming_data'], 'cba_pdoh_shps','co100_3h_{}.shp'.format(depths[d]))
		# Regions
		records = geopandas.read_file(hazard_file)
		proj = "+proj=tmerc +lat_0=-34.629269 +lon_0=-58.4633 +k=0.9999980000000001 +x_0=100000 +y_0=100000 +ellps=intl +units=m +no_defs"
		records.crs = proj
		print (records)
		records = records.to_crs({'init': 'epsg:4326'})
		print (records)
		records.to_file(os.path.join(config['paths']['incoming_data'], 'cba_pdoh_shps_2','co100_3h_{}.shp'.format(depths[d])))

		ax.add_geometries(list(records.geometry), crs=proj_lat_lon, edgecolor='#ffffff', facecolor=colors[d])

	# Legend
	legend_handles = []
	for c in range(len(colors)):
		legend_handles.append(mpatches.Patch(color=colors[c], label=str(depths[c])))

	ax.legend(
		handles=legend_handles,
		title = 'Flood depths (cm)',
		loc='lower right'
	)

	plt.title('1 in 100 year flood for 3 hour duration', fontsize = 14)
	save_fig(output_file)
	plt.close()


if __name__ == '__main__':
	CONFIG = load_config()
	main(CONFIG)
