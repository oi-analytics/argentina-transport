"""Road network failure maps
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
    plot_set = [
        {
            'column': 'min_tr_loss',
            'no_access':[0],
            'title': 'Min Rerouting loss',
            'legend_label': "Rerouting Loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_tr_loss',
            'no_access':[0],
            'title': 'Max Rerouting loss',
            'legend_label': "Rerouting Loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_econ_impact',
            'no_access':[0,1],
            'title': 'Min Total Economic loss',
            'legend_label': "Economic Loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_econ_impact',
            'no_access':[0,1],
            'title': 'Max Total Economic loss',
            'legend_label': "Economic Loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_total_tons',
            'no_access':[0,1],
            'title': 'Min Daily Tons disrupted',
            'legend_label': "Tons disrupted ('000 tons/day)",
            'divisor': 1000,
            'significance': 0
        },
        {
            'column': 'max_total_tons',
            'no_access':[0,1],
            'title': 'Max Daily Tons disrupted',
            'legend_label': "Tons disrupted ('000 tons/day)",
            'divisor': 1000,
            'significance': 0
        },
        {
            'column': 'min_econ_loss',
            'no_access':[1],
            'title': 'Min Macroeconomic losses',
            'legend_label': "Economic loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_econ_loss',
            'no_access':[1],
            'title': 'Max Macroeconomic losses',
            'legend_label': "Economic loss (million USD/day)",
            'divisor': 1000000,
            'significance': 0
        }
    ]
    
    data_path = config['paths']['data']
    region_file_path = os.path.join(config['paths']['data'], 'network',
                                   'road_edges.shp')
    flow_file_path = os.path.join(config['paths']['output'], 'failure_results','minmax_combined_scenarios',
                               'single_edge_failures_minmax_road_100_percent_disrupt.csv')

    region_file = gpd.read_file(region_file_path,encoding='utf-8')
    flow_file = pd.read_csv(flow_file_path)
    region_file = pd.merge(region_file,flow_file,how='left', on=['edge_id']).fillna(0)
    region_file = region_file[(region_file['road_type'] == 'national') | (region_file['road_type'] == 'province') | (region_file['road_type'] == 'rural')]

    for c in range(len(plot_set)):
        proj_lat_lon = ccrs.PlateCarree()
        ax = get_axes()
        plot_basemap(ax, data_path)
        scale_bar(ax, location=(0.8, 0.05))
        plot_basemap_labels(ax, data_path, include_regions=True)

        column = plot_set[c]['column']

        weights = [
            getattr(record,column)
            for record in region_file.itertuples()
            if int(record.no_access) in plot_set[c]['no_access']
        ]

        max_weight = max(weights)
        width_by_range = generate_weight_bins(weights)

        road_geoms_by_category = {
                'national': [],
                'province': [],
                'rural': [],
                'none':[]
        }
        for record in region_file.itertuples():
            cat = str(record.road_type)
            if cat not in road_geoms_by_category:
                raise Exception
            geom = record.geometry
            val = getattr(record,column)
            if val == 0:
                cat = 'none'

            buffered_geom = None
            for (nmin, nmax), width in width_by_range.items():
                if nmin <= val and val < nmax:
                    buffered_geom = geom.buffer(width)

            if buffered_geom is not None:
                road_geoms_by_category[cat].append(buffered_geom)
            else:
                print("Feature was outside range to plot", record.Index)

        styles = OrderedDict([
                ('national',  Style(color='#e41a1c', zindex=9, label='National')),  # red
                ('province', Style(color='#377eb8', zindex=8, label='Provincial')),  # orange
                ('rural', Style(color='#4daf4a', zindex=7, label='Rural')),  # blue
                ('none', Style(color='#969696', zindex=6, label='No hazard exposure/effect'))
        ])

        for cat, geoms in road_geoms_by_category.items():
            cat_style = styles[cat]
            ax.add_geometries(
                geoms,
                crs=proj_lat_lon,
                linewidth=0,
                facecolor=cat_style.color,
                edgecolor='none',
                zorder=cat_style.zindex
            )

        x_l = -62.4
        x_r = x_l + 0.4
        base_y = -42.1
        y_step = 0.8
        y_text_nudge = 0.2
        x_text_nudge = 0.2

        ax.text(
            x_l,
            base_y + y_step - y_text_nudge,
            plot_set[c]['legend_label'],
            horizontalalignment='left',
            transform=proj_lat_lon,
            size=10)

        divisor = plot_set[c]['divisor']
        significance_ndigits = plot_set[c]['significance']
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

        plt.title(plot_set[c]['title'], fontsize=14)
        print ('* Plotting ',plot_set[c]['title'])
        legend_from_style_spec(ax, styles,loc='lower left')
        output_file = os.path.join(
            config['paths']['figures'], 'road_failure-map-{}.png'.format(column))
        save_fig(output_file)
        plt.close()


if __name__ == '__main__':
    main()
