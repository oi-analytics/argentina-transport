"""Plot rail network
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
    output_file = os.path.join(config['paths']['figures'], 'network-rail-map.png')
    rail_edge_file = os.path.join(data_path, 'network', 'rail_edges.shp')
    rail_node_file = os.path.join(data_path, 'network', 'rail_nodes.shp')

    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    colors = {
        'Railway': '#006d2c',
        'Station': '#003312'
    }

    # edges
    edges = geopandas.read_file(rail_edge_file)
    ax.add_geometries(
        list(edges.geometry),
        crs=proj_lat_lon,
        linewidth=1.25,
        edgecolor=colors['Railway'],
        facecolor='none',
        zorder=4
    )

    # nodes
    nodes = geopandas.read_file(rail_node_file)
    ax.scatter(
        list(nodes.geometry.x),
        list(nodes.geometry.y),
        transform=proj_lat_lon,
        facecolor=colors['Station'],
        s=4,
        zorder=5
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
