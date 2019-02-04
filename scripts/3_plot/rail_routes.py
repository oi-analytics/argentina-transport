"""Rail network routes map
"""
import csv
import os
import sys
from collections import OrderedDict, defaultdict
from pprint import pprint

import pandas as pd
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from oia.utils import *


def main():
    config = load_config()
    data_path = config['paths']['data']
    output_file = os.path.join(config['paths']['figures'], 'rail-map-routes.png')
    rails_file = os.path.join(
        config['paths']['data'], 'network', 'rail_edges.shp')
    

    # colours = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    #            '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    #            '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    #            '#17becf', '#9edae5']

    colours = ['#1f77b4', '#ff7f0e', '#2ca02c','#9467bd','#8c564b','#e377c2','#d62728']
    lines = ['Belgrano','San Martin','Mitre', 'Roca','Sarmiento','Urquiza','Other']
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    rail_geoms_by_category = defaultdict(list)

    for record in shpreader.Reader(rails_file).records():
        cat = record.attributes['linea'].replace('FFCC ','').strip()
        if 'belgrano' in cat.lower().strip():
            cat = 'Belgrano'
        elif cat not in lines:
            cat = 'Other'
        geom = record.geometry
        rail_geoms_by_category[cat].append(geom)

    styles = OrderedDict([])

    for idx in range(len(lines)):
        styles.update({lines[idx]: Style(color=colours[idx], zindex=4, label=lines[idx])})

    for cat, geoms in rail_geoms_by_category.items():
        cat_style = styles[cat]
        ax.add_geometries(
            geoms,
            crs=proj_lat_lon,
            linewidth=1.5,
            edgecolor=cat_style.color,
            facecolor='none',
            zorder=cat_style.zindex
        )

    legend_from_style_spec(ax, styles, loc=(0.6,0.2))
    save_fig(output_file)


if __name__ == '__main__':
    main()
