"""Road network risks and adaptation maps
"""
import os
import sys
from collections import OrderedDict

import ast
import numpy as np
import geopandas as gpd
import pandas as pd
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from oia.utils import *


def main():
    config = load_config()

    hazard_cols = ['hazard_type','climate_scenario','year']
    duration = 10
    cat_label = 'No hazard exposure/effect'
    hazard_set = [
        {
            'hazard': 'fluvial flooding',
            'name': 'Fluvial flooding'
        },
        {
            'hazard': 'pluvial flooding',
            'name': 'Pluvial flooding'
        }
    ]
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#fee08b','#fdae61','#f46d43','#d73027','#969696']
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0 to 10','10 to 50','50 to 100',' > 100','No change/value']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0.001,10),(10,50),(50,100),(100,1e10)]

    
    adapt_set = [
        {
            'column': 'min_ini_adap_cost',
            'title': 'Min Initial Investment',
            'legend_label': "Initial investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_ini_adap_cost',
            'title': 'Max Initial Investment',
            'legend_label': "Initial investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_benefit',
            'title': 'Min Benefit over time',
            'legend_label': "Benefit (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_benefit',
            'title': 'Max Benefit over time',
            'legend_label': "Benefit (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_tot_adap_cost',
            'title': 'Min Investment over time',
            'legend_label': "Total Investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_tot_adap_cost',
            'title': 'Max Investment over time',
            'legend_label': "Total Investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_ini_adap_cost_perkm',
            'title': 'Min Initial Investment per km',
            'legend_label': "Initial Investment (USD million/km)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_ini_adap_cost_perkm',
            'title': 'Max Initial Investment per km',
            'legend_label': "Initial Investment (USD million/km)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_tot_adap_cost_perkm',
            'title': 'Min Investment per km over time',
            'legend_label': "Total Investment (USD million/km)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_tot_adap_cost_perkm',
            'title': 'Max Investment per km over time',
            'legend_label': "Total Investment (USD million/km)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'min_bc_ratio',
            'title': 'Min BCR of adaptation over time',
            'legend_label': "BCR",
            'divisor': 1,
            'significance': 0
        },
        {
            'column': 'max_bc_ratio',
            'title': 'Max BCR of adaptation over time',
            'legend_label': "BCR",
            'divisor': 1,
            'significance': 0
        }
    ]


    adapt_set = [
        {
            'column': 'max_ini_adap_cost',
            'title': 'Max Initial Investment',
            'legend_label': "Initial investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_benefit',
            'title': 'Max Benefit over time',
            'legend_label': "Benefit (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_tot_adap_cost',
            'title': 'Max Investment over time',
            'legend_label': "Total Investment (USD million)",
            'divisor': 1000000,
            'significance': 0
        },
        {
            'column': 'max_bc_ratio',
            'title': 'Max BCR of adaptation over time',
            'legend_label': "BCR",
            'divisor': 1,
            'significance': 0
        }
    ]

    adapt_cols = ['max_benefit','max_ini_adap_cost','max_tot_adap_cost','max_bc_ratio']


    data_path = config['paths']['data']

    region_file_path = os.path.join(config['paths']['data'], 'network',
                               'road_edges.shp')
    region_file = gpd.read_file(region_file_path,encoding='utf-8')
    region_file = region_file[(region_file['road_type'] == 'national') | (region_file['road_type'] == 'province') | (region_file['road_type'] == 'rural')]

    flow_file_path = os.path.join(config['paths']['output'], 'adaptation_results',
                               'output_adaptation_road_10_days_max_disruption_fixed_parameters.csv')

    fail_scenarios = pd.read_csv(flow_file_path,encoding='utf-8-sig')

    climate_scenarios = list(set(fail_scenarios.climate_scenario.values.tolist()))
    for climate_scenario in climate_scenarios:
        scenario_vals = fail_scenarios[fail_scenarios['climate_scenario'] == climate_scenario]
        scenario_vals = scenario_vals.groupby(['edge_id'])[adapt_cols].max().reset_index()
        edges_vals = pd.merge(region_file[['edge_id','road_type','geometry']],scenario_vals,how='left',on=['edge_id']).fillna(0)
        for c in range(len(adapt_set)):
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=False)

            # generate weight bins
            column = adapt_set[c]['column']
            if column in ['min_bc_ratio','max_bc_ratio']:
                weights = [record[column] for iter_, record in edges_vals.iterrows() if record[column] > 1]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights, width_step=0.04, n_steps=5)
                width_by_range.update({(0,1):0.01})
                width_by_range.move_to_end((0,1), last=False)

            else:
                weights = [record[column] for iter_, record in edges_vals.iterrows()]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights,)

            # print (width_by_range)
            road_geoms_by_category = {
                'national': [],
                'province': [],
                'rural': [],
                'none':[]
            }

            for iter_,record in edges_vals.iterrows():
                cat = str(record['road_type'])
                if cat not in road_geoms_by_category:
                    raise Exception
                geom = record.geometry
                val = record[column]
                if column in ['min_bc_ratio','max_bc_ratio']:
                    if val < 1:
                        cat = 'none'
                        cat_label = 'No hazard exposure/effect/BCR < 1'

                else:
                    if val == 0:
                        cat = 'none'

                buffered_geom = None
                for (nmin, nmax), width in width_by_range.items():
                    if nmin <= val and val < nmax:
                        buffered_geom = geom.buffer(width)

                if buffered_geom is not None:
                    road_geoms_by_category[cat].append(buffered_geom)
                else:
                    print("Feature was outside range to plot", iter_)

            styles = OrderedDict([
                ('national',  Style(color='#e41a1c', zindex=9, label='National')),  # red
                ('province', Style(color='#377eb8', zindex=8, label='Provincial')),  # orange
                ('rural', Style(color='#4daf4a', zindex=7, label='Rural')),  # blue
                ('none', Style(color='#969696', zindex=6, label=cat_label))
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
            # name = [h['name'] for h in hazard_set if h['hazard'] == hazard_type][0]

            x_l = -62.4
            x_r = x_l + 0.4
            base_y = -42.1
            y_step = 0.8
            y_text_nudge = 0.2
            x_text_nudge = 0.2

            ax.text(
                x_l,
                base_y + y_step - y_text_nudge,
                adapt_set[c]['legend_label'],
                horizontalalignment='left',
                transform=proj_lat_lon,
                size=10)

            divisor = adapt_set[c]['divisor']
            significance_ndigits = adapt_set[c]['significance']
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

            if climate_scenario.lower().strip() == 'baseline':
                year = 2016
            else:
                year = 2050
            
            title = 'Roads ({}) {} {}'.format(adapt_set[c]['title'],climate_scenario.replace('_',' ').title(),year)
            print ('* Plotting ',title)

            plt.title(title, fontsize=14)
            legend_from_style_spec(ax, styles,loc='lower left')

            # output
            output_file = os.path.join(
                config['paths']['figures'], 'national-roads-{}-{}-{}.png'.format(climate_scenario.replace('.',''),year,adapt_set[c]['column']))
            save_fig(output_file)
            plt.close()

    


if __name__ == '__main__':
    main()
