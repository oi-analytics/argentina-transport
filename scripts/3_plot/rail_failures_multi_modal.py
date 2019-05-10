"""Network rerouting loss maps
"""
import os
import sys
from collections import OrderedDict

import numpy as np
import geopandas as gpd
import pandas as pd
import cartopy.crs as ccrs
import matplotlib as mpl
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.geometry import LineString
from atra.utils import *

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 10.
mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 10.
mpl.rcParams['xtick.labelsize'] = 9.
mpl.rcParams['ytick.labelsize'] = 9.


def plot_ranges(input_data, division_factor,x_label, y_label,plot_title,plot_color,plot_file_path,ylimit=None,yticks_loc=None,y_ticks_labels=None):
    fig, ax = plt.subplots(figsize=(8, 4))
    # vals_min_max = list(zip(*list(h for h in input_data.itertuples(index=False))))
    vals_min_max = []
    for a, b in input_data.itertuples(index=False):
        if a < b:
            min_, max_ = a, b
        else:
            min_, max_ = b, a
        vals_min_max.append((min_, max_))

    vals_min_max.sort(key=lambda el: el[1])

    vals_min_max = list(zip(*vals_min_max))

    percentlies = 100.0*np.arange(0,len(vals_min_max[0]))/len(vals_min_max[0])
    ax.plot(percentlies,
        1.0*np.array(vals_min_max[0])/division_factor,
        linewidth=0.5,
        color=plot_color
    )
    ax.plot(percentlies,
        1.0*np.array(vals_min_max[1])/division_factor,
        linewidth=0.5,
        color=plot_color
    )
    ax.fill_between(percentlies,
        1.0*np.array(vals_min_max[0])/division_factor,
        1.0*np.array(vals_min_max[1])/division_factor,
        alpha=0.5,
        edgecolor=None,
        facecolor=plot_color
    )

    if 'BCR' in y_label:
        ax.plot(np.arange(0,100),
            np.array([1]*100),
            linewidth=0.5,
            color='red',
            label = 'BCR = 1'
        )
        # ax.set_xscale('log')
        ax.legend(loc='upper left')
    if ylimit:
        max_val = input_data.max().max()
        y_ticks_labels += [str(int(max_val/division_factor))]
        ax.set_ylim(bottom=-0.5,top=ylimit/division_factor)
        plt.yticks(yticks_loc,y_ticks_labels)
    # ax.set_yscale('log')
    # ax.tick_params(axis='x', rotation=45)
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def change_to_infinity(x,dividend_column,divisor_column):
    if x[divisor_column] == 0 and x[dividend_column] == 0:
        return 0
    elif x[divisor_column] == 0 and x[dividend_column] > 0:
        return 1e9
    elif x[divisor_column] == 0 and x[dividend_column] < 0:
        return -1e9
    else:
        return 100.0*(x[dividend_column] - x[divisor_column])/x[divisor_column]

def main():
    config = load_config()
    data_path = config['paths']['data']

    duration = 10
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#fee08b','#fdae61','#f46d43','#d73027','#969696']
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0 to 10','10 to 50','50 to 100',' > 100','No change/value']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0.001,10),(10,50),(50,100),(100,1e10)]

    
    fail_file = pd.read_csv(os.path.join(config['paths']['output'], 'failure_results','minmax_combined_scenarios',
                               'single_edge_failures_minmax_rail_100_percent_disrupt_multi_modal.csv'))
    

    flow_file = pd.read_csv(os.path.join(config['paths']['output'], 'failure_results','minmax_combined_scenarios',
                               'single_edge_failures_minmax_rail_100_percent_disrupt.csv'))
    fail_file = pd.merge(fail_file,flow_file[['edge_id','min_econ_impact','max_econ_impact']],how='outer', on=['edge_id']).fillna(0)
    del flow_file

    flow_file = pd.read_csv(os.path.join(config['paths']['output'], 'network_stats',
                               'national_rail_hazard_intersections_risks.csv'))
    fail_file = pd.merge(fail_file,flow_file,how='left', on=['edge_id']).fillna(0)
    del flow_file

    fail_file['min_eael'] = duration*fail_file['risk_wt']*fail_file['min_econ_impact']
    fail_file['max_eael'] = duration*fail_file['risk_wt']*fail_file['max_econ_impact']

    fail_file['min_eael_multimodal'] = duration*fail_file['risk_wt']*fail_file['min_tr_loss']
    fail_file['max_eael_multimodal'] = duration*fail_file['risk_wt']*fail_file['max_tr_loss']

    fail_file.to_csv('test.csv')
    fail_file_min = fail_file.groupby(['edge_id'])['min_tr_loss','min_econ_impact','min_eael_multimodal','min_eael'].min().reset_index()
    fail_file_max = fail_file.groupby(['edge_id'])['max_tr_loss','max_econ_impact','max_eael_multimodal','max_eael'].max().reset_index()
    del fail_file

    region_file_path = os.path.join(config['paths']['data'], 'network',
                               'rail_edges.shp')
    region_file = gpd.read_file(region_file_path,encoding='utf-8')
    region_file = pd.merge(region_file[['edge_id','geometry']],fail_file_min,how='left',on=['edge_id']).fillna(0)
    region_file = pd.merge(region_file,fail_file_max,how='left',on=['edge_id']).fillna(0)
    del fail_file_min,fail_file_max

    flow_file = pd.read_csv(os.path.join(config['paths']['output'], 'flow_mapping_combined',
                                   'weighted_flows_rail_100_percent.csv'))
    region_file = pd.merge(region_file,flow_file,how='left', on=['edge_id']).fillna(0)

    region_file = region_file[region_file['max_total_tons'] > 0]
    del flow_file


    rail_color = '#006d2c'
    very_high_value = 4000000
    yticks_loc = [-0.5,0,0.5,1,1.5,2,2.5,3,3.5,4]
    y_ticks_labels = ['-0.5','0','0.5','1','1.5','2','2.5','.','.']
    plot_sets = [
        {
            'file_tag': 'loss',
            'no_access': [0, 1],
            'legend_label': "Economic loss (million USD/day)",
            'divisor': 1000000,
            'columns': ['min_tr_loss', 'max_tr_loss'],
            'title_cols': ['Rail - Multi-modal Economic impact (min)', 'Rail - Multi-modal Economic impact (max)']
        },

        {
            'file_tag': 'risk',
            'no_access': [0, 1],
            'legend_label': "EAEL million USD",
            'divisor': 1000000,
            'columns': ['min_eael_multimodal', 'max_eael_multimodal'],
            'title_cols': ['Rail - Multi-modal EAEL (min)', 'Rail - Multi-modal EAEL (max)']
        },
    ]

    change_sets = [
        {
            'columns': ['tr_loss', 'econ_impact'],
            'legend': 'daily losses',
            'title_col': 'Percentage change in Economic losses for rail multi-modal switches'
        },

        {
            'columns': ['eael_multimodal', 'eael'],
            'legend': 'EAEL',
            'title_col': 'Percentage change in EAEL for rail multi-modal switches'
        },
    ]

    plt_file_path = os.path.join(config['paths']['figures'],'rail-economic-loss-ranges-100-percent-multi-modal.png')
    plot_ranges(region_file[['min_tr_loss','max_tr_loss']],
                1000000,
                "Percentile rank (%)",
                "Economic impacts (million USD/day)",
                "Rail - Range of total economic impacts due to single link failures",
                rail_color,plt_file_path,very_high_value,yticks_loc,y_ticks_labels)

    plt_file_path = os.path.join(config['paths']['figures'],'rail-eael-ranges-100-percent-multi-modal.png')
    plot_ranges(region_file[['min_eael_multimodal','max_eael_multimodal']],
                1000000, 
                "Percentile rank (%)",
                "EAEL (million USD)",
                "Rail - Range of EAEL due to single link failures",
                rail_color,plt_file_path)

    
    for t in ['min','max']:
        for ch in change_sets: 
            edges_vals = region_file[['edge_id','geometry','{}_{}'.format(t,ch['columns'][0]),'{}_{}'.format(t,ch['columns'][1])]]
            # edges_vals.to_csv('test.csv')
            edges_vals['change'] = edges_vals.apply(lambda x:change_to_infinity(x,'{}_{}'.format(t,ch['columns'][0]),'{}_{}'.format(t,ch['columns'][1])),axis=1)
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=True)

            for record in edges_vals.itertuples():
                geom = record.geometry
                region_val = record.change
                if region_val:
                    cl = [c for c in range(len((change_ranges))) if region_val >= change_ranges[c][0] and region_val < change_ranges[c][1]]
                    if cl:
                        c = cl[0]
                        ax.add_geometries([geom],crs=proj_lat_lon,linewidth=2.0,edgecolor=change_colors[c],facecolor='none',zorder=8)
                        # ax.add_geometries([geom.buffer(0.1)],crs=proj_lat_lon,linewidth=0,facecolor=change_colors[c],edgecolor='none',zorder=8)
                else:
                    ax.add_geometries([geom], crs=proj_lat_lon, linewidth=1.5,edgecolor=change_colors[-1],facecolor='none',zorder=7)
                    # ax.add_geometries([geom.buffer(0.1)], crs=proj_lat_lon, linewidth=0,facecolor=change_colors[-1],edgecolor='none',zorder=7)
            # Legend
            legend_handles = []
            for c in range(len(change_colors)):
                legend_handles.append(mpatches.Patch(color=change_colors[c], label=change_labels[c]))

            ax.legend(
                handles=legend_handles,
                title='Percentage change in {}'.format(ch['legend']),
                loc=(0.5,0.2),
                fancybox=True,
                framealpha=1.0
            )

            print(" * Plotting {}".format(ch['title_col']))

            plt.title(ch['title_col'], fontsize=10)
            output_file = os.path.join(config['paths']['figures'],
                                       'national-rail-multi-modal-{}-{}-change-percentage.png'.format(t,ch['legend'].replace(' ','-')))
            save_fig(output_file)
            plt.close()

    for plot_set in plot_sets:
        for c in range(len(plot_set['columns'])):
            column = plot_set['columns'][c]

            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=True)


            weights = [
                record[column]
                for iter_,record in region_file.iterrows()
                if record[column] < very_high_value
            ]

            min_weight = min(weights)
            max_weight = max(weights)
            abs_max_weight = max([abs(w) for w in weights])

            width_by_range = OrderedDict()
            colors_by_range = {}
            n_steps = 8

            positive_colors = [
                '#f4a582',
                '#d6604d',
                '#b2182b',
                '#67001f',
            ]
            negative_colors = [
                '#92c5de',
                '#4393c3',
                '#2166ac',
                '#053061',
            ]
            width_step = 0.03

            mins = np.linspace(0, abs_max_weight, n_steps/2)
            # mins = np.geomspace(1, abs_max_weight, n_steps/2)

            maxs = list(mins)
            maxs.append(abs_max_weight*10)
            maxs = maxs[1:]

            # print (mins,maxs)

            assert len(maxs) == len(mins)

            # positive
            for i, (min_, max_) in reversed(list(enumerate(zip(mins, maxs)))):
                width_by_range[(min_, max_)] = (i + 2) * width_step
                colors_by_range[(min_, max_)] = positive_colors[i]

            # negative
            for i, (min_, max_) in enumerate(zip(mins, maxs)):
                width_by_range[(-max_, -min_)] = (i + 2) * width_step
                colors_by_range[(-max_, -min_)] = negative_colors[i]

            geoms_by_range = {}
            for value_range in width_by_range:
                geoms_by_range[value_range] = []

            zero_value_geoms = []
            for iter_,record in region_file.iterrows():
                val = record[column]
                geom = record.geometry
                if val != 0 and val < very_high_value:
                    for nmin, nmax in geoms_by_range:
                        if nmin <= val and val < nmax:
                            geoms_by_range[(nmin, nmax)].append(geom)
                else:
                    zero_value_geoms.append(geom)

            # plot
            for range_, width in width_by_range.items():
                ax.add_geometries(
                    [geom.buffer(width) for geom in geoms_by_range[range_]],
                    crs=proj_lat_lon,
                    edgecolor='none',
                    facecolor=colors_by_range[range_],
                    zorder=2)

            width_min = min([width for range_, width in width_by_range.items()])
            ax.add_geometries(
                [geom.buffer(width_min) for geom in zero_value_geoms],
                crs=proj_lat_lon,
                edgecolor='none',
                facecolor='#969696',
                zorder=1)

            x_l = -62.4
            x_r = x_l + 0.4
            base_y = -42.1
            y_step = 0.8
            y_text_nudge = 0.2
            x_text_nudge = 0.2

            ax.text(
                x_l - x_text_nudge,
                base_y + y_step - y_text_nudge,
                plot_set['legend_label'],
                horizontalalignment='left',
                transform=proj_lat_lon,
                size=8)

            divisor = plot_set['divisor']

            i = 0
            for (nmin, nmax), width in width_by_range.items():
                if not geoms_by_range[(nmin, nmax)]:
                    continue
                y = base_y - (i*y_step)
                i = i + 1
                line = LineString([(x_l, y), (x_r, y)])
                ax.add_geometries(
                    [line.buffer(width)],
                    crs=proj_lat_lon,
                    linewidth=0,
                    edgecolor=colors_by_range[(nmin, nmax)],
                    facecolor=colors_by_range[(nmin, nmax)],
                    zorder=2)
                if nmin == max_weight:
                    label = '>{:.2f}'.format(max_weight/divisor)
                elif nmax == -abs_max_weight:
                    label = '<{:.2f}'.format(-abs_max_weight/divisor)
                else:
                    label = '{:.2f} to {:.2f}'.format(nmin/divisor, nmax/divisor)
                ax.text(
                    x_r + x_text_nudge,
                    y - y_text_nudge,
                    label,
                    horizontalalignment='left',
                    transform=proj_lat_lon,
                    size=8)

            styles = OrderedDict([
                ('1',  Style(color='#b2182b', zindex=9, label='Economic loss effect')),  # green
                ('2',  Style(color='#2166ac', zindex=9, label='Economic gain effect')),
                ('3', Style(color='#969696', zindex=9, label='No hazard exposure/effect'))
            ])
            plt.title(plot_set['title_cols'][c], fontsize=14)
            legend_from_style_spec(ax, styles,loc='lower left')

            print ('* Plotting Rail {}'.format(plot_set['title_cols'][c]))
            output_file = os.path.join(
                      config['paths']['figures'], 'rail_failure-map-{}-{}-multi-modal-options.png'.format(plot_set['file_tag'], column))
            save_fig(output_file)
            plt.close()
            print(" >", output_file)


if __name__ == '__main__':
    main()
