"""Coastal network flows map
"""
import os
import sys
from collections import OrderedDict

import pandas as pd
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString
from atra.utils import *


def main():
    config = load_config()
    data_path = config['paths']['data']
    coastal_edge_file_path = os.path.join(
        config['paths']['data'], 'network', 'port_edges.shp')
    coastal_flow_file_path = os.path.join(config['paths']['output'], 'flow_mapping_combined',
                                   'weighted_flows_port_100_percent.csv')
    coastal_node_file = os.path.join(config['paths']['data'],
                                 'network', 'port_nodes.shp')


    mode_file = gpd.read_file(coastal_edge_file_path,encoding='utf-8')
    flow_file = pd.read_csv(coastal_flow_file_path,encoding='utf-8-sig')
    mode_file = pd.merge(mode_file,flow_file,how='left', on=['edge_id']).fillna(0)

    color = '#045a8d'
    color_by_type = {'coastal Line': color}

    plot_sets = [
        {
            'file_tag': 'commodities',
            'legend_label': "AADF ('000 tons/day)",
            'divisor': 1000,
            'columns': ['max_{}'.format(x) for x in ['total_tons','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'COMERCIO',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS',
                    'INDUSTRIA MANUFACTURERA',
                    'PESCA','TRANSPORTE Y COMUNICACIONES']],
            'title_cols': ['Total tonnage','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'COMERCIO',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS',
                    'INDUSTRIA MANUFACTURERA',
                    'PESCA','TRANSPORTE Y COMUNICACIONES'],
            'significance':0
        },
    ]
    for plot_set in plot_sets:
        for c in range(len(plot_set['columns'])):
            # basemap
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=True)

            column = 'max_total_tons'
            weights = [
                record[column]
                for iter_, record in mode_file.iterrows()
            ]
            max_weight = max(weights)
            width_by_range = generate_weight_bins(weights, n_steps=7, width_step=0.02)

            geoms_by_range = {}
            for value_range in width_by_range:
                geoms_by_range[value_range] = []

            column = plot_set['columns'][c]
            for iter_, record in mode_file.iterrows():
                val = record[column]
                geom = record.geometry
                for nmin, nmax in geoms_by_range:
                    if nmin <= val and val < nmax:
                        geoms_by_range[(nmin, nmax)].append(geom)

            # plot
            for range_, width in width_by_range.items():
                ax.add_geometries(
                    [geom.buffer(width) for geom in geoms_by_range[range_]],
                    crs=proj_lat_lon,
                    edgecolor='none',
                    facecolor=color,
                    zorder=2)

            x_l = -58.4
            x_r = x_l + 0.4
            base_y = -45.1
            y_step = 0.8
            y_text_nudge = 0.2
            x_text_nudge = 0.2

            ax.text(
                x_l,
                base_y + y_step - y_text_nudge,
                plot_set['legend_label'],
                horizontalalignment='left',
                transform=proj_lat_lon,
                size=10)

            divisor = plot_set['divisor']
            significance_ndigits = plot_set['significance']
            max_sig = []
            for (i, ((nmin, nmax), line_style)) in enumerate(width_by_range.items()):
                if round(nmin/divisor, significance_ndigits) < round(nmax/divisor, significance_ndigits):
                    max_sig.append(significance_ndigits)
                elif round(nmin/divisor, significance_ndigits+1) < round(nmax/divisor, significance_ndigits+1):
                    max_sig.append(significance_ndigits+1)
                elif round(nmin/divisor, significance_ndigits+2) < round(nmax/divisor, significance_ndigits+2):
                    max_sig.append(significance_ndigits+2)
                else:
                    max_sig.append(significance_ndigits+3)

            significance_ndigits = max(max_sig)

            for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
                y = base_y - (i*y_step)
                line = LineString([(x_l, y), (x_r, y)])
                ax.add_geometries(
                    [line.buffer(width)],
                    crs=proj_lat_lon,
                    linewidth=0,
                    edgecolor=color,
                    facecolor=color,
                    zorder=2)
                if nmin == max_weight:
                    value_template = '>{:.' + str(significance_ndigits) + 'f}'
                    label = value_template.format(
                        round(max_weight/divisor, significance_ndigits))
                else:
                    value_template = '{:.' + str(significance_ndigits) + \
                        'f}-{:.' + str(significance_ndigits) + 'f}'
                    label = value_template.format(
                        round(nmin/divisor, significance_ndigits), round(nmax/divisor, significance_ndigits))
                ax.text(
                    x_r + x_text_nudge,
                    y - y_text_nudge,
                    label,
                    horizontalalignment='left',
                    transform=proj_lat_lon,
                    size=10)

            plt.title('Max AADF - {}'.format(plot_set['title_cols'][c]), fontsize=10)
            output_file = os.path.join(config['paths']['figures'],
                                       'water_flow-map-{}-max-scale.png'.format(column))
            save_fig(output_file)
            plt.close()


if __name__ == '__main__':
    main()
