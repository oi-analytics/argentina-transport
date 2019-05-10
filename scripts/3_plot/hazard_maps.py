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
    file_paths_info = [('GLOFRIS','WATCH','ARG_inunriver_historical_000000000WATCH_1980_rp01000.tif'),
    				('GLOFRIS','RCP45','ARG_inunriver_rcp4p5_0000GFDL-ESM2M_2030_rp01000.tif'),
    				('GLOFRIS','RCP85','ARG_inunriver_rcp8p5_0000GFDL-ESM2M_2030_rp01000.tif'),
    				('FATHOM','AR_fluvial_undefended_merged','AR-FU-1000.tif'),
    				('FATHOM','AR_pluvial_undefended_merged','AR-PU-1000.tif')
    				]
    figure_names = ['GLOFRIS-WATCH-fluvial','GLOFRIS-RCP45-fluvial','GLOFRIS-RCP85-fluvial','FATHOM-fluvial','FATHOM-pluvial']
    figure_titles = ['current fluvial flooding','RCP4.5 fluvial flooding','RCP8.5 fluvial flooding','current fluvial flooding','current pluvial flooding']
    for f_i in range(len(file_paths_info)):
	    hazard_file = os.path.join(config['paths']['data'],'flood_data', file_paths_info[f_i][0],file_paths_info[f_i][1],file_paths_info[f_i][2])
	    output_file = os.path.join(config['paths']['figures'], 'flood-map-{}.png'.format(figure_names[f_i]))
	    ax = get_axes()
	    plot_basemap(ax, config['paths']['data'])
	    scale_bar(ax, location=(0.8, 0.05))
	    plot_basemap_labels(ax, config['paths']['data'], include_regions=True,include_zorder=3)

	    proj_lat_lon = ccrs.PlateCarree()


	    # Create color map
	    colors = plt.get_cmap('Blues')

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
	    cbar.ax.set_xlabel('Flood depths (m)',fontsize=12,color='black')

	    plt.title('1 in 1000 year {}'.format(figure_titles[f_i]), fontsize = 14)
	    save_fig(output_file)
	    plt.close()


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
