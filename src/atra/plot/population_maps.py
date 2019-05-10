"""Plot country and administrative areas
"""
import os
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from atra.utils import *
import matplotlib as mpl

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
	figure_names = ['2010-census','2015-census']
	# for f_i in range(len(figure_names)):
	for f_i in range(0,1):
		output_file = os.path.join(config['paths']['figures'], '{}.png'.format(figure_names[f_i]))

		ax = get_axes()
		plot_basemap(ax, config['paths']['data'])
		scale_bar(ax, location=(0.8, 0.05))
		plot_basemap_labels(ax, config['paths']['data'], include_regions=True,include_zorder=3)

		proj_lat_lon = ccrs.PlateCarree()

		if f_i == 0:
			hazard_file = os.path.join(config['paths']['incoming_data'], '3','radios censales','radioscensales.shp')
			# Regions
			for record in shpreader.Reader(hazard_file).records():
				region_val = record.attributes['poblacion']
				color = '#e0e0e0'
				geom = record.geometry
				if region_val:
					if region_val > 0 and region_val <= 1000:
						color = '#ffffcc' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '0 to 1000')
					elif region_val > 500 and region_val <= 2000:
						color = '#c7e9b4' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '1000 to 2000')
					elif region_val > 2000 and region_val <= 3000:
						color = '#7fcdbb' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '2000 to 3000')
					elif region_val > 3000 and region_val <= 4000:
						color = '#41b6c4' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '3000 to 4000')
					if region_val > 4000 and region_val <= 5000:
						color = '#2c7fb8' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '4000 to 5000')
					elif region_val > 5000 and region_val <= 6000:
						color = '#253494' # TODO
						ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = '5000 to 6000')

				else:
					ax.add_geometries([geom], crs=proj_lat_lon, edgecolor='#ffffff', facecolor=color,label = 'No value')

			colors = ['#ffffcc','#c7e9b4','#7fcdbb','#41b6c4','#2c7fb8','#253494','#e0e0e0']
			labels = ['0 to 1000','1000 to 2000','2000 to 3000','3000 to 4000','4000 to 5000','5000 to 6000','No value']
			# Legend
			legend_handles = []
			for c in range(len(colors)):
				legend_handles.append(mpatches.Patch(color=colors[c], label=labels[c]))

			ax.legend(
				handles=legend_handles,
				title = 'Population numbers',
				loc='lower right'
				)
		else:
			hazard_file = os.path.join(config['paths']['incoming_data'], '2','radios censales','radioscensales.shp')
			# Create color map
			colors = plt.get_cmap('YlBuGn')

			# Read in raster data
			data, lat_lon_extent = get_data(hazard_file)
			data[(data <= 0) | (data > 5)] = np.nan
			max_val = np.nanmax(data)
			norm=mpl.colors.Normalize(vmin=0, vmax=max_val)

			# Plot population data
			im = ax.imshow(data, extent=lat_lon_extent,transform=proj_lat_lon, cmap=colors,norm =norm, zorder=2)

			# Add colorbar
			cbar = plt.colorbar(im, ax=ax,fraction=0.1, shrink=0.87,pad=0.01, drawedges=False, orientation='horizontal',
								norm=mpl.colors.Normalize(vmin=0, vmax=max_val), ticks=list(np.linspace(0,max_val,3)))
			cbar.set_clim(vmin=0,vmax=max_val)

			cbar.outline.set_color("none")
			cbar.ax.yaxis.set_tick_params(color='black')
			cbar.ax.set_xlabel('Population estimates',fontsize=12,color='black')

		plt.title(figure_names[f_i], fontsize = 14)
		save_fig(output_file)
		plt.close()


if __name__ == '__main__':
	CONFIG = load_config()
	main(CONFIG)
