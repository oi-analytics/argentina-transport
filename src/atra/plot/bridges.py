"""Plot road network
"""
import csv
import os
import sys
from collections import OrderedDict, defaultdict
from pprint import pprint

import pandas as pd
import geopandas
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from atra.utils import *

def main(config):
    """Read shapes, plot map
    """
    data_path = config['paths']['data']

    # data
    output_file = os.path.join(config['paths']['figures'], 'network-bridge-map.png')
    road_edge_file = os.path.join(data_path, 'network', 'road_edges.shp')
    bridge_file = os.path.join(data_path, 'network', 'bridges.shp')

    # basemap
    proj_lat_lon = ccrs.PlateCarree()
    ax = get_axes()
    plot_basemap(ax, data_path)
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, data_path, include_regions=False)

    styles = OrderedDict([
                ('national',  Style(color='#ba0f03', zindex=5, label='National roads')),
                ('MAYOR SOBRE AGUA Y RUTA', Style(color='#9467bd', zindex=7, label='AGUA Y RUTA')),
                ('MAYOR SOBRE FERROCARRIL', Style(color='#2ca02c', zindex=8, label='FERROCARRIL')),
                ('MAYOR SOBRE RUTA', Style(color= '#ff7f0e', zindex=9, label='RUTA')),
                ('MAYOR SOBRE RUTA Y FERROCARRIL', Style(color='#e377c2', zindex=10, label='RUTA Y FERROCARRIL')),
                ('MAYOR SOBRE RUTA, AGUA Y FERROCARRIL', Style(color='#8c564b', zindex=11, label='RUTA, AGUA Y FERROCARRIL')),
                ('MAYOR SOBRE VIA DE AGUA', Style(color='#1f77b4', zindex=6, label='VIA DE AGUA')),
            ])

    # edges
    geoms_by_category = {
                'national': [],
                'MAYOR SOBRE AGUA Y RUTA': [],
                'MAYOR SOBRE FERROCARRIL': [],
                'MAYOR SOBRE RUTA':[],
                'MAYOR SOBRE RUTA Y FERROCARRIL':[],
                'MAYOR SOBRE RUTA, AGUA Y FERROCARRIL':[],
                'MAYOR SOBRE VIA DE AGUA':[]
            }

    edges_national = geopandas.read_file(road_edge_file)
    edges_national = edges_national[edges_national['road_type'] == 'national']
    geoms_by_category['national'] = list(edges_national.geometry)


    bridges = geopandas.read_file(bridge_file,encoding='utf-8')
    for iter_, val in bridges.iterrows():
        cat = val['structur_1'].strip()
        geoms_by_category[cat].append(val.geometry)


    for cat, geoms in geoms_by_category.items():
        cat_style = styles[cat]
        if cat == 'national':
            ax.add_geometries(
                geoms,
                crs=proj_lat_lon,
                linewidth=1.25,
                facecolor='none',
                edgecolor=cat_style.color,
                zorder=cat_style.zindex
            )
        else:
            ax.scatter(
                [g.x for g in geoms],
                [g.y for g in geoms],
                transform=proj_lat_lon,
                facecolor=cat_style.color,
                s=6,
                zorder=cat_style.zindex
            )

    # legend
    legend_from_style_spec(ax, styles, loc=(0.48,0.2))

    # save
    save_fig(output_file)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
