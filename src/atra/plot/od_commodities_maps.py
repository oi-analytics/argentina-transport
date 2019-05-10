"""Plot commodities maps
"""
import os

import cartopy.crs as ccrs
import geopandas
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import pandas


from atra.utils import load_config, get_axes, plot_basemap, scale_bar, plot_basemap_labels, save_fig


def main(config):
    """Read shapes, plot map
    """
    data_path = config['paths']['data']
    zones_file = os.path.join(data_path, 'boundaries', 'economic_od_zones.shp')
    od_file = os.path.join(data_path, 'usage', 'economic_od.csv')

    od = pandas.read_csv(od_file)
    zones = geopandas.read_file(zones_file)

    all_prod = od.groupby(['sector', 'from_zone']).sum()
    all_attr = od.groupby(['sector', 'to_zone']).sum()

    for sector in od.sector.unique():
        print(" >", sector)

        productions = all_prod.loc[sector, :]
        productions = zones.merge(productions, left_on='id', right_on='from_zone')
        attractions = all_attr.loc[sector, :]
        attractions = zones.merge(attractions, left_on='id', right_on='to_zone')
        norm = Normalize(
            vmin=min(productions.value.min(), attractions.value.min()),
            vmax=max(productions.value.max(), attractions.value.max())
        )

        label = "Commodity ({}) productions".format(sector)
        plot(productions, norm, data_path, label)
        save_fig(os.path.join(
            config['paths']['figures'], 'od_{}_orig_map.png'.format(sector)))

        label = "Commodity ({}) attractions".format(sector)
        plot(attractions, norm, data_path, label)
        save_fig(os.path.join(
            config['paths']['figures'], 'od_{}_dest_map.png'.format(sector)))


def plot(df, norm, data_path, label):
    """Plot df
    """
    cmap = plt.cm.ScalarMappable(norm=norm, cmap='magma_r')
    df['color'] = df.value.apply(cmap.to_rgba)

    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    # zones
    for zone in df.itertuples():
        ax.add_geometries(
            [zone.geometry],
            crs=proj_lat_lon,
            edgecolor='none',
            facecolor=zone.color,
            zorder=3
        )

    cmap.set_array(df.value)
    cbar = plt.colorbar(
        cmap, ax=ax, fraction=0.05, pad=0.04, drawedges=False,
        shrink=0.9, orientation='horizontal'
    )
    cbar.outline.set_color("none")
    cbar.ax.set_xlabel(label)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
