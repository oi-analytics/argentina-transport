"""Plot air network
"""
import os

import cartopy.crs as ccrs
import geopandas
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


from oia.utils import load_config, get_axes, plot_basemap, scale_bar, plot_basemap_labels, save_fig


def main(config):
    """Read shapes, plot map
    """
    data_path = config['paths']['data']

    # data
    output_file = os.path.join(config['paths']['figures'], 'network-air-map.png')
    air_edge_file = os.path.join(data_path, 'network', 'air_edges.shp')
    air_node_file = os.path.join(data_path, 'network', 'air_nodes.shp')
    # air_usage_file = os.path.join(data_path, 'usage', 'air_passenger.csv')

    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    colors = {
        'Air route': '#252525',
        'Airport': '#d95f0e'
    }

    # edges
    edges = geopandas.read_file(air_edge_file)
    ax.add_geometries(
        list(edges.geometry),
        crs=proj_lat_lon,
        linewidth=1.5,
        edgecolor=colors['Air route'],
        facecolor='none',
        zorder=4
    )

    # edges merged with usage
    # usage = pandas.read_csv(air_usage_file)
    # edges_with_usage = edges.merge(usage[['id', 'passengers_2016']], on='id')

    # nodes
    nodes = geopandas.read_file(air_node_file)
    ax.scatter(
        list(nodes.geometry.x),
        list(nodes.geometry.y),
        transform=proj_lat_lon,
        facecolor=colors['Airport'],
        s=12,
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
