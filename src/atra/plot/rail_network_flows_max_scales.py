"""Road network flow maps
"""
import os
import sys
from collections import OrderedDict

import geopandas as gpd
import pandas as pd
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from atra.utils import *


def main():
    config = load_config()
    data_path = config['paths']['data']
    mode_file_path = os.path.join(config['paths']['data'], 'network',
                                   'rail_edges.shp')
    flow_file_path = os.path.join(config['paths']['output'], 'flow_mapping_combined',
                                   'weighted_flows_rail_100_percent.csv')


    mode_file = gpd.read_file(mode_file_path,encoding='utf-8')
    flow_file = pd.read_csv(flow_file_path)
    mode_file = pd.merge(mode_file,flow_file,how='left', on=['edge_id']).fillna(0)

    flow_color = '#006d2c'
    no_flow_color = '#636363'
    plot_sets = [
        {
            'file_tag': 'commodities',
            'legend_label': "AADF ('000 tons/day)",
            'divisor': 1000,
            'columns': ['max_total_tons','max_AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                        'max_COMERCIO', 'max_EXPLOTACIÓN DE MINAS Y CANTERAS',
                        'max_INDUSTRIA MANUFACTURERA', 'max_TRANSPORTE Y COMUNICACIONES'
                        ],
            'title_cols': ['Total tonnage','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'COMERCIO','EXPLOTACIÓN DE MINAS Y CANTERAS',
                    'INDUSTRIA MANUFACTURERA','TRANSPORTE Y COMUNICACIONES'
                    ],
            'significance':0
        },
    ]

    plot_sets = [
        {
            'file_tag': 'commodities',
            'legend_label': "AADF ('000 tons/day)",
            'divisor': 1000,
            'columns': ['max_total_tons'
                        ],
            'title_cols': ['Total tonnage'
                    ],
            'significance':0
        },
    ]

    styles = OrderedDict([
                ('1',  Style(color='#006d2c', zindex=6, label='Flow')),
                ('2', Style(color='#636363', zindex=8, label='No flow')),
            ])
    tot_length = 0
    for plot_set in plot_sets:
        for c in range(len(plot_set['columns'])):
            # basemap
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=False)

            # generate weight bins
            column = plot_set['columns'][c]
            weights = [
                record['max_total_tons']
                for iter_, record in mode_file.iterrows() if record['max_total_tons'] > 0
            ]
            max_weight = max(weights)
            width_by_range = generate_weight_bins(weights, n_steps=9, width_step=0.015, interpolation='log')

            geoms_by_range = {}
            for value_range in width_by_range:
                geoms_by_range[value_range] = []

            for iter_, record in mode_file.iterrows():
                val = record[column]
                geom = record.geometry
                if val > 0:
                    tot_length += line_length(geom)
                    for nmin, nmax in geoms_by_range:
                        if nmin <= val and val < nmax:
                            geoms_by_range[(nmin, nmax)].append(geom)
                else:
                    ax.add_geometries(
                    [geom],
                    crs=proj_lat_lon,
                    linewidth=0.5,
                    edgecolor=no_flow_color,
                    facecolor='none',
                    zorder=1)

            print ('Operational network {} kms'.format(tot_length))

                        # plot
            for range_, width in width_by_range.items():
                ax.add_geometries(
                    [geom.buffer(width) for geom in geoms_by_range[range_]],
                    crs=proj_lat_lon,
                    edgecolor='none',
                    facecolor=flow_color,
                    zorder=2)

            x_l = -62.4
            x_r = x_l + 0.4
            base_y = -42.1
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
                line = LineString([(x_l, y), (x_r, y)]).buffer(width)
                ax.add_geometries(
                    [line],
                    crs=proj_lat_lon,
                    linewidth=0,
                    edgecolor='#000000',
                    facecolor='#000000',
                    zorder=2)
                if abs(nmin - max_weight) < 1e-5:
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
            legend_from_style_spec(ax, styles)
            output_file = os.path.join(
                config['paths']['figures'],
                'rail_flow-map-{}-{}-max-scale.png'.format(plot_set['file_tag'], column))
            save_fig(output_file)
            plt.close()


if __name__ == '__main__':
    main()
