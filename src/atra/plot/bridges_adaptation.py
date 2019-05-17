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
from atra.utils import *


def main():
    config = load_config()

    hazard_cols = ['hazard_type','climate_scenario','year']
    duration = 10
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
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0 to 10','10 to 50','50 to 100',' > 100','No change/value/BCR<1']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0.001,10),(10,50),(50,100),(100,1e10)]

    
    adapt_set = [
            {
                'column': 'max_ini_adap_cost',
                'title': 'Max Initial Investment',
                'legend_label': "Initial Cost (USD million)",
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
                'legend_label': "Total Cost (USD million)",
                'divisor': 1000000,
                'significance': 0
            },
            {
                'column': 'max_ini_adap_cost_perkm',
                'title': 'Max Initial Investment per km',
                'legend_label': "Initial Cost (USD million/km)",
                'divisor': 1000000,
                'significance': 0
            },
            {
                'column': 'max_tot_adap_cost_perkm',
                'title': 'Max Investment per km over time',
                'legend_label': "Total Cost (USD million/km)",
                'divisor': 1000000,
                'significance': 0
            },
            {
                'column': 'max_bc_ratio',
                'title': 'Max BCR > 1',
                'legend_label': "BCR",
                'divisor': 1,
                'significance': 0
            }
    ]

    adapt_cols = ['max_benefit','max_ini_adap_cost','max_tot_adap_cost','max_bc_ratio','max_ini_adap_cost_perkm','max_tot_adap_cost_perkm']


    data_path = config['paths']['data']

    road_file_path = os.path.join(config['paths']['data'], 'network',
                                   'road_edges.shp')
    road_file = gpd.read_file(road_file_path,encoding='utf-8')
    road_file = road_file[road_file['road_type'] == 'national']


    region_file_path = os.path.join(config['paths']['data'], 'network',
                               'bridge_edges.shp')
    region_file = gpd.read_file(region_file_path,encoding='utf-8')

    flow_file_path = os.path.join(config['paths']['output'], 'adaptation_results',
                               'output_adaptation_bridge_{}_days_max_disruption_fixed_parameters.csv'.format(duration))

    fail_scenarios = pd.read_csv(flow_file_path,encoding='utf-8-sig')
    fail_scenarios['max_ini_adap_cost_perkm'] = 1000*fail_scenarios['max_ini_adap_cost']/fail_scenarios['edge_length']
    fail_scenarios['max_tot_adap_cost_perkm'] = 1000*fail_scenarios['max_tot_adap_cost']/fail_scenarios['edge_length']

    
    # Climate change effects
    all_edge_fail_scenarios = fail_scenarios.groupby(['bridge_id','climate_scenario','year'])['max_bc_ratio'].max().reset_index()
    all_edge_fail_scenarios = all_edge_fail_scenarios.set_index(['bridge_id'])
    scenarios = list(set(all_edge_fail_scenarios.index.values.tolist()))
    change_tup = []
    for sc in scenarios:
        max_bc_ratio = all_edge_fail_scenarios.loc[[sc], 'max_bc_ratio'].values.tolist()
        yrs = all_edge_fail_scenarios.loc[[sc], 'year'].values.tolist()
        cl = all_edge_fail_scenarios.loc[[sc], 'climate_scenario'].values.tolist()
        if 2016 not in yrs:
            for e in range(len(max_bc_ratio)):
                if max_bc_ratio[e] > 0: 
                    # change_tup += list(zip([sc[0]]*len(cl),[sc[1]]*len(cl),cl,yrs,[0]*len(cl),eael,[1e9]*len(cl)))
                    change_tup += [(sc,cl[e],yrs[e],0,max_bc_ratio[e],1e9)]
        elif len(yrs) > 1:
            vals = list(zip(cl,max_bc_ratio,yrs))
            vals = sorted(vals, key=lambda pair: pair[-1])
            change = 100.0*(np.array([p for (c,p,y) in vals[1:]]) - vals[0][1])/vals[0][1]
            cl = [c for (c,p,y) in vals[1:]]
            yrs = [y for (c,p,y) in vals[1:]]
            fut = [p for (c,p,y) in vals[1:]]
            change_tup += list(zip([sc]*len(cl),cl,yrs,[vals[0][1]]*len(cl),fut,change))

    change_df = pd.DataFrame(change_tup,columns=['bridge_id','climate_scenario','year','current','future','change']).fillna(0)
    # change_df = change_df[change_df['future'] != -1]
    change_df.to_csv(os.path.join(config['paths']['output'],
        'network_stats',
        'national_bridge_max_bc_ratios_climate_change_{}_days.csv'.format(duration)
        ), index=False
    )

    # Change effects
    change_df = change_df.set_index(['climate_scenario','year'])
    scenarios = list(set(change_df.index.values.tolist()))
    for sc in scenarios:
        climate_scenario = sc[0]
        year = sc[1]
        # percentage = change_df.loc[[sc], 'change'].values.tolist()
        # edges = change_df.loc[[sc], 'bridge_id'].values.tolist()
        sc_vals = [tuple(x) for x in change_df.loc[[sc], ['bridge_id','current','future','change']].values.tolist()]
        edges_df = pd.DataFrame(sc_vals,columns=['bridge_id','current','future','change'])
        edges_vals = pd.merge(region_file[['bridge_id','geometry']],edges_df,how='left',on=['bridge_id']).fillna(0)
        del sc_vals,edges_df

        proj_lat_lon = ccrs.PlateCarree()
        ax = get_axes()
        plot_basemap(ax, data_path)
        scale_bar(ax, location=(0.8, 0.05))
        plot_basemap_labels(ax, data_path, include_regions=False)

        ax.add_geometries(
            list(road_file.geometry),
            crs=proj_lat_lon,
            linewidth=1.0,
            edgecolor='#969696',
            facecolor='none',
            zorder=5
        )

        for record in edges_vals.itertuples():
            geom = record.geometry
            region_val = record.change
            if record.current > 1 or record.future > 1:
                if region_val:
                    cl = [c for c in range(len((change_ranges))) if region_val >= change_ranges[c][0] and region_val < change_ranges[c][1]]
                    if cl:
                        c = cl[0]
                        # ax.add_geometries([geom],crs=proj_lat_lon,linewidth=1.5,edgecolor=change_colors[c],facecolor='none',zorder=8)
                        ax.add_geometries([geom.buffer(0.1)],crs=proj_lat_lon,linewidth=0,facecolor=change_colors[c],edgecolor='none',zorder=8)
                else:
                    # ax.add_geometries([geom], crs=proj_lat_lon, linewidth=1.5,edgecolor=change_colors[-1],facecolor='none',zorder=7)
                    ax.add_geometries([geom.buffer(0.1)], crs=proj_lat_lon, linewidth=0,facecolor=change_colors[-1],edgecolor='none',zorder=7)
            else:
                ax.add_geometries([geom.buffer(0.1)], crs=proj_lat_lon, linewidth=0,facecolor=change_colors[-1],edgecolor='none',zorder=7)

        # Legend
        legend_handles = []
        for c in range(len(change_colors)):
            legend_handles.append(mpatches.Patch(color=change_colors[c], label=change_labels[c]))

        ax.legend(
            handles=legend_handles,
            title='Percentage change in BCR',
            loc=(0.55,0.2),
            fancybox=True,
            framealpha=1.0
        )
        if climate_scenario == 'none':
            climate_scenario = 'current'
        else:
            climate_scenario = climate_scenario.upper()

        title = 'Percentage change in BCR for {} {}'.format(climate_scenario.replace('_',' ').title(),year)
        print(" * Plotting {}".format(title))

        plt.title(title, fontsize=10)
        output_file = os.path.join(config['paths']['figures'],
                                   'national-bridges-{}-{}-bc-ratios-change-percentage.png'.format(climate_scenario.replace('-',' ').title(),year))
        save_fig(output_file)
        plt.close()


    fail_scenarios = fail_scenarios.reset_index()
    scenario_vals = fail_scenarios
    scenario_vals = scenario_vals.groupby(['bridge_id'])[adapt_cols].max().reset_index()
    edges_vals = pd.merge(region_file[['bridge_id','geometry']],scenario_vals,how='left',on=['bridge_id']).fillna(0)
    for c in range(len(adapt_set)):
        cat_label = 'No hazard exposure/effect'
        proj_lat_lon = ccrs.PlateCarree()
        ax = get_axes()
        plot_basemap(ax, data_path)
        scale_bar(ax, location=(0.8, 0.05))
        plot_basemap_labels(ax, data_path, include_regions=False)

        ax.add_geometries(
        list(road_file.geometry),
        crs=proj_lat_lon,
        linewidth=1.0,
        edgecolor='#969696',
        facecolor='none',
        zorder=5
        )


        # generate weight bins
        column = adapt_set[c]['column']
        if column in ['min_bc_ratio','max_bc_ratio']:
            weights = [record[column] for iter_, record in edges_vals.iterrows() if record[column] > 1]
            max_weight = max(weights)
            width_by_range = generate_weight_bins(weights, width_step=0.05, n_steps=5)
            width_by_range.update({(0,1):0.01})
            width_by_range.move_to_end((0,1), last=False)

        else:
            weights = [record[column] for iter_, record in edges_vals.iterrows()]
            max_weight = max(weights)
            width_by_range = generate_weight_bins(weights, width_step=0.04, n_steps=5)

        # print (width_by_range)
        road_geoms_by_category = {
            'national': [],
            'none':[]
        }

        for iter_,record in edges_vals.iterrows():
            geom = record.geometry
            val = record[column]
            if column in ['min_bc_ratio','max_bc_ratio']:
                if val < 1:
                    cat = 'none'
                    cat_label = 'No hazard exposure/effect/BCR < 1'
                else:
                    cat = 'national'

            else:
                if val <= 0:
                    cat = 'none'
                else:
                    cat = 'national'

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

        title = 'Bridges ({})'.format(adapt_set[c]['title'])
        print ('* Plotting ',title)

        plt.title(title, fontsize=14)
        legend_from_style_spec(ax, styles,loc='lower left')

        output_file = os.path.join(
            config['paths']['figures'], 'national-bridges-{}-{}-days.png'.format(adapt_set[c]['column'],duration))
        save_fig(output_file)
        plt.close()

    adapt_set = [
        {
            'column': 'max_bc_ratio',
            'title': 'Max BCR > 1',
            'legend_label': "BCR",
            'divisor': 1,
            'significance': 0
        }

    ]

    fail_scenarios = fail_scenarios.reset_index()
    cost_thr = [40,80]
    for cost in cost_thr:
        scenario_vals = fail_scenarios[['bridge_id']+adapt_cols]
        # scenario_vals = scenario_vals.groupby(['edge_id'])[adapt_cols].max().reset_index()
        scenario_vals = scenario_vals.sort_values(['max_bc_ratio'], ascending=False)
        scenario_vals.drop_duplicates(subset=['bridge_id'],keep='first',inplace=True)
        scenario_vals = scenario_vals[scenario_vals['max_bc_ratio']>=1]
        scenario_vals['tot_costs_cumsum'] = scenario_vals['max_tot_adap_cost'].cumsum()
        scenario_vals = scenario_vals[scenario_vals['tot_costs_cumsum'] <= 1e6*cost]
        edges_vals = pd.merge(region_file[['bridge_id','geometry']],scenario_vals,how='left',on=['bridge_id']).fillna(0)
        for c in range(len(adapt_set)):
            cat_label = 'No hazard exposure/effect'
            proj_lat_lon = ccrs.PlateCarree()
            ax = get_axes()
            plot_basemap(ax, data_path)
            scale_bar(ax, location=(0.8, 0.05))
            plot_basemap_labels(ax, data_path, include_regions=False)

            ax.add_geometries(
            list(road_file.geometry),
            crs=proj_lat_lon,
            linewidth=1.0,
            edgecolor='#969696',
            facecolor='none',
            zorder=5
            )


            # generate weight bins
            column = adapt_set[c]['column']
            if column in ['min_bc_ratio','max_bc_ratio']:
                weights = [record[column] for iter_, record in edges_vals.iterrows() if record[column] > 1]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights, width_step=0.05, n_steps=5)
                width_by_range.update({(0,1):0.01})
                width_by_range.move_to_end((0,1), last=False)

            else:
                weights = [record[column] for iter_, record in edges_vals.iterrows()]
                max_weight = max(weights)
                width_by_range = generate_weight_bins(weights, width_step=0.04, n_steps=5)

            # print (width_by_range)
            road_geoms_by_category = {
                'national': [],
                'none':[]
            }

            for iter_,record in edges_vals.iterrows():
                geom = record.geometry
                val = record[column]
                if column in ['min_bc_ratio','max_bc_ratio']:
                    if val < 1:
                        cat = 'none'
                        cat_label = 'No hazard exposure/effect/BCR < 1'
                    else:
                        cat = 'national'

                else:
                    if val <= 0:
                        cat = 'none'
                    else:
                        cat = 'national'

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

            title = 'Bridges with {} for {} million investment'.format(adapt_set[c]['title'],cost)
            print ('* Plotting ',title)

            plt.title(title, fontsize=14)
            legend_from_style_spec(ax, styles,loc='lower left')

            output_file = os.path.join(
                config['paths']['figures'], 'national-bridges-{}-{}-million-investment-{}-days.png'.format(adapt_set[c]['column'],cost,duration))
            save_fig(output_file)
            plt.close()


if __name__ == '__main__':
    main()
