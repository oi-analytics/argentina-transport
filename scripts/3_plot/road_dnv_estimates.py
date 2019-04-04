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
from oia.utils import *
from tqdm import tqdm

def assign_veh_to_roads(x,veh_list):
    """Assign terrain as flat or mountain to national roads

    Parameters
        x - Pandas DataFrame of values
            - dia_hinh__ - String value of type of terrain

    Returns
        String value of terrain as flat or mountain
    """
    veh_no = 0
    road_no = x.road_no
    if str(road_no).isdigit():
        road_no = int(road_no)

    for vals in veh_list:
        rn = vals.ruta
        if str(rn).isdigit():
            rn = int(rn)

        if road_no == rn and x.inicio_km >= vals.inicio and x.fin_km <= vals.fin:
            veh_no = 0.01*(vals.ca + vals.semi)*vals.tmd
            break


    return veh_no

def main():
    tqdm.pandas()
    config = load_config()
    data_path = config['paths']['data']
    incoming_data_path = config['paths']['incoming_data']
    road_file_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_edges_4326.shp')
    # road_file_path = os.path.join(config['paths']['data'], 'network',
    #                                'road_edges.shp')

    road_file = gpd.read_file(road_file_path,encoding='utf-8')
    road_file = road_file[road_file['road_type'] == 'national']
    
    road_veh = pd.read_excel(os.path.join(incoming_data_path,'5','DNV_data_recieved_06082018','TMDA y Clasificación 2016.xlsx'),sheet_name='Clasificación 2016',skiprows=14,encoding='utf-8-sig').fillna(0)
    road_veh.columns = map(str.lower, road_veh.columns)
    road_veh = list(road_veh.itertuples(index=False))
    road_file['veh_no'] = road_file.progress_apply(lambda x: assign_veh_to_roads(x, road_veh), axis=1)

    road_file_path = os.path.join(incoming_data_path, '5','Lineas de deseo OD- 2014','3.6.1.9.asignacion_vial',
                                   'Asignacion_2014_vial.shp')
    dnv_file = gpd.read_file(road_file_path,encoding='utf-8')
    dnv_file.columns = map(str.lower, dnv_file.columns)
    dnv_file['road_type'] = 'national'

    veh_df = [road_file,dnv_file]

    plot_sets = [
        {
            'file_tag': 'veh_no',
            'legend_label': "AADT (vehicles/day)",
            'divisor': 1,
            'columns': ['veh_no'],
            'title_cols': ['Daily vehicle count'],
            'significance':0
        },
        {
            'file_tag': 'dnv_no',
            'legend_label': "AADT ('000 vehicles/year)",
            'divisor': 1000,
            'columns': ['total_grup'],
            'title_cols': ['Annual vehicle count'],
            'significance':0
        },
    ]

    for ps in range(len(plot_sets)):
        plot_set = plot_sets[ps]
        mode_file = veh_df[ps]
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
                record[column]
                for iter_, record in mode_file.iterrows()
            ]
            max_weight = max(weights)
            width_by_range = generate_weight_bins(weights, n_steps=7, width_step=0.02)

            road_geoms_by_category = {
                'national': [],
                'none': [],
            }

            column = plot_set['columns'][c]
            for iter_, record in mode_file.iterrows():
                cat = str(record['road_type'])
                if cat not in road_geoms_by_category:
                    raise Exception
                geom = record.geometry
                val = record[column]
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
                ('none', Style(color='#969696', zindex=6, label='No value'))
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

            plt.title('AADT - {}'.format(plot_set['title_cols'][c]), fontsize=10)
            legend_from_style_spec(ax, styles)
            output_file = os.path.join(
                config['paths']['figures'],
                'road_traffic-map-{}-{}.png'.format(plot_set['file_tag'], column))
            save_fig(output_file)
            plt.close()


if __name__ == '__main__':
    main()
