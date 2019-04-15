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
import matplotlib as mpl
from oia.utils import *


def main():
    config = load_config()
    data_path = config['paths']['data']
    mode_file_path = os.path.join(config['paths']['data'], 'network',
                                   'road_edges.shp')
    flow_file_path = os.path.join(config['paths']['output'], 'flow_mapping_combined',
                                   'weighted_flows_road_100_percent.csv')


    mode_file = gpd.read_file(mode_file_path,encoding='utf-8')
    flow_file = pd.read_csv(flow_file_path)
    mode_file = pd.merge(mode_file,flow_file,how='left', on=['edge_id']).fillna(0)
    mode_file = mode_file[(mode_file['road_type'] == 'national') | (mode_file['road_type'] == 'province') | (mode_file['road_type'] == 'rural')]

    # mode_file = mode_file[mode_file['max_total_tons'] > 0]
    # mode_file = mode_file[(mode_file['road_type'] == 'rural') & (mode_file['max_total_tons'] > 0)]
    # print (mode_file)

    plot_sets = [
        {
            'file_tag': 'tmda',
            'legend_label': "AADT ('000 vehicles/day)",
            'divisor': 1000,
            'columns': ['tmda'],
            'title_cols': ['Vehicle Count'],
            'significance':0
        },
        {
            'file_tag': 'commodities',
            'legend_label': "AADF ('000 tons/day)",
            'divisor': 1000,
            'columns': ['max_{}'.format(x) for x in ['total_tons','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados']],
            'title_cols': ['Total tonnage','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados'],
            'significance':0
        },
    ]

    plot_sets = [
        {
            'file_tag': 'tmda',
            'legend_label': "AADT ('000 vehicles/day)",
            'divisor': 1000,
            'columns': ['tmda'],
            'title_cols': ['Vehicle Count'],
            'significance':0
        },
    ]

    plot_sets = [
        {
            'file_tag': 'commodities',
            'legend_label': "AADF ('000 tons/day)",
            'divisor': 1000,
            'columns': ['max_{}'.format(x) for x in ['total_tons','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados']],
            'title_cols': ['Total tonnage','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados'],
            'significance':0
        },
    ]

    '''scatter plot of flows and tonnages
    '''
    # veh_tons = mode_file[mode_file['road_type'] == 'national']
    # vt = [(int(str(record['tmda'])),record['max_total_tons']) 
    #                     for iter_, record in veh_tons.iterrows() if str(record['tmda']).isdigit() is True]
    # v,t = zip(*vt)
    # mpl.style.use('ggplot')
    # mpl.rcParams['font.size'] = 10.
    # mpl.rcParams['font.family'] = 'tahoma'
    # mpl.rcParams['axes.labelsize'] = 10.
    # mpl.rcParams['xtick.labelsize'] = 9.
    # mpl.rcParams['ytick.labelsize'] = 9.

    # fig, ax = plt.subplots(figsize=(8, 4))
    # plt.scatter(np.array(v),np.array(t),color='black')
    # ax.set_yscale('symlog')
    # ax.set_xscale('symlog')
    # plt.xlabel('AADT (Vehicles/day)', fontweight='bold')
    # plt.ylabel('AADF (tons/day)', fontweight='bold')
    # plt.tight_layout()
    # plot_file_path = os.path.join(
    #             config['paths']['figures'],
    #             'road-vehicle-tons-correlations.png')
    # plt.savefig(plot_file_path, dpi=500)
    # plt.close()


    for plot_set in plot_sets:
        for c in range(len(plot_set['columns'])):
            # basemap
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=False)

            # generate weight bins
            if plot_set['columns'][c] == 'tmda':
                column = plot_set['columns'][c]
                weights = [int(str(record[column])) 
                        for iter_, record in mode_file.iterrows() if str(record[column]).isdigit() is True and int(str(record[column])) > 0]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights, n_steps=9, width_step=0.01, interpolation='log')
            else:
                column = 'max_total_tons'
                weights = [
                    record[column]
                    for iter_, record in mode_file.iterrows()
                ]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights, n_steps=7, width_step=0.02)

            road_geoms_by_category = {
                'national': [],
                'province': [],
                'rural': [],
            }

            column = plot_set['columns'][c]
            for iter_, record in mode_file.iterrows():
                if column == 'tmda':
                    if str(record[column]).isdigit() is False:
                        val = 0
                    else:
                        val = int(str(record[column]))
                else:
                    val = record[column]

                if val > 0:
                    cat = str(record['road_type']).lower().strip()
                    if cat not in road_geoms_by_category:
                        raise Exception
                    geom = record.geometry


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
            legend_from_style_spec(ax, styles)
            output_file = os.path.join(
                config['paths']['figures'],
                'road_flow-map-{}-{}-max-scale.png'.format(plot_set['file_tag'], column))
            save_fig(output_file)
            plt.close()


if __name__ == '__main__':
    main()
