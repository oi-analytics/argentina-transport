"""Plot water network
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
    output_file = os.path.join(config['paths']['figures'], 'network-water-map.png')
    water_edge_file = os.path.join(data_path, 'network', 'water_edges.shp')
    water_node_file = os.path.join(data_path, 'network', 'water_nodes.shp')

    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    colors = {
        'Waterway': '#045a8d',
        'Port': '#54278f'
    }

    # edges
    edges = geopandas.read_file(water_edge_file)
    ax.add_geometries(
        list(edges.geometry.buffer(0.02)),
        crs=proj_lat_lon,
        edgecolor='none',
        facecolor=colors['Waterway'],
        zorder=4
    )

    # nodes
    nodes = geopandas.read_file(water_node_file)
    ax.scatter(
        list(nodes.geometry.x),
        list(nodes.geometry.y),
        transform=proj_lat_lon,
        facecolor=colors['Port'],
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
