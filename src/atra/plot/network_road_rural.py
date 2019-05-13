"""Plot road network
"""
import os

import cartopy.crs as ccrs
import geopandas
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


from atra.utils import load_config, get_axes, plot_basemap, scale_bar, plot_basemap_labels, save_fig


def main(config):
    """Read shapes, plot map
    """
    data_path = config['paths']['data']

    # data
    output_file = os.path.join(config['paths']['figures'], 'network-rural-road-map.png')
    road_edge_file_rural = os.path.join(data_path, 'network', 'road_edges_rural.shp')


    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    colors = {
        'Rural': '#d95f0e'
    }

    # edges
    edges_rural = geopandas.read_file(road_edge_file_rural)
    ax.add_geometries(
        list(edges_rural.geometry),
        crs=proj_lat_lon,
        linewidth=0.5,
        edgecolor=colors['Rural'],
        facecolor='none',
        zorder=4
    )

    # legend
    legend_handles = [
        mpatches.Patch(color=color, label=label)
        for label, color in colors.items()
    ]
    plt.legend(handles=legend_handles, loc='lower left')

    # save
    save_fig(output_file)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
