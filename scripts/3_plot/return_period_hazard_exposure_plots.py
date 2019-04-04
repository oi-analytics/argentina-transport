"""National hazard exposure maps
"""
import os
import sys
from collections import OrderedDict

import geopandas as gpd
import pandas as pd
import numpy as np
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from oia.utils import *

def main():
    config = load_config()

    data_path = config['paths']['data']
    modes = ['road', 'rail']
    hazard_cols = ['hazard_type','climate_scenario','year']
    return_periods = [10,100,1000]
    plot_set = [
        {
            'hazard': 'pluvial flooding',
            'color': ['#c6dbef', '#9ecae1', '#6baed6', '#3182bd', '#08519c','#d9d9d9'],
            'name': 'Pluvial flooding'
        },
        {
            'hazard': 'fluvial flooding',
            'color': ['#c6dbef', '#9ecae1', '#6baed6', '#3182bd', '#08519c','#d9d9d9'],
            'name': 'Fluvial flooding'
        },
    ]
    climate_change = False
    national_pth = os.path.join(config['paths']['output'],
            'network_stats',
            'national_scale_hazards_stats.xlsx')
    
    # Give the paths to the input data files
    # load provinces and get geometry of the right province
    print('* Reading provinces dataframe')
    province_path = os.path.join(config['paths']['incoming_data'],'2','provincia','Provincias.shp')
    provinces = gpd.read_file(province_path,encoding='utf-8')
    provinces = provinces.to_crs({'init': 'epsg:4326'})
    sindex_provinces = provinces.sindex
    
    '''Assign provinces to zones
    '''
    print('* Reading department dataframe')
    zones_path = os.path.join(config['paths']['incoming_data'], '2',
                                'departamento', 'Departamentos.shp')
    zones = gpd.read_file(zones_path,encoding='utf-8')
    zones = zones.to_crs({'init': 'epsg:4326'})
    zones.rename(columns={'OBJECTID':'department_id','Name':'department_name','Geometry':'geom_type'},inplace=True)

    zones['province_name'] = zones.apply(lambda x: extract_value_from_gdf(
        x, sindex_provinces, provinces,'nombre'), axis=1)
    zones['province_id'] = zones.apply(lambda x: extract_value_from_gdf(
        x, sindex_provinces, provinces,'OBJECTID'), axis=1)

    labels = ['0 to 5', '5 to 10', '10 to 20', '20 to 30', '> 30', 'No value']
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#fee08b','#fdae61','#f46d43','#d73027','#d9d9d9']
    change_labels = ['< -40','-40 to -20','-20 to -10','-10 to 0','0 to 10','10 to 20','20 to 40','> 40','No change/value']
    change_ranges = [(-1e10,-40),(-40,-20),(-20,-10),(-10,0),(0.001,10),(10,20),(20,40),(40,1e10)]

    for mode in modes:
        edge_fail_scenarios = pd.read_excel(national_pth,sheet_name=mode)
        edge_fail_scenarios = edge_fail_scenarios[hazard_cols + ['department_id','probability','percentage']]
        
        for rp in return_periods:
            print ('return period',rp)
            all_edge_fail_scenarios = edge_fail_scenarios[edge_fail_scenarios['probability'] == 1.0/rp]

            # Climate change effects
            if climate_change == True:
                all_edge_fail_scenarios = all_edge_fail_scenarios.set_index(['hazard_type','department_id'])
                scenarios = list(set(all_edge_fail_scenarios.index.values.tolist()))
                change_tup = []
                for sc in scenarios:
                    perc = all_edge_fail_scenarios.loc[[sc], 'percentage'].values.tolist()
                    yrs = all_edge_fail_scenarios.loc[[sc], 'year'].values.tolist()
                    cl = all_edge_fail_scenarios.loc[[sc], 'climate_scenario'].values.tolist()
                    if 2016 not in yrs:
                        change_tup += list(zip([sc[0]]*len(cl),[sc[1]]*len(cl),cl,yrs,[1e9]*len(cl)))
                    elif len(cl) > 1:
                        vals = list(zip(cl,perc,yrs))
                        vals = sorted(vals, key=lambda pair: pair[-1])
                        change = np.array([p for (c,p,y) in vals[1:]]) - vals[0][1]
                        cl = [c for (c,p,y) in vals[1:]]
                        yrs = [y for (c,p,y) in vals[1:]]
                        change_tup += list(zip([sc[0]]*len(cl),[sc[1]]*len(cl),cl,yrs,change))

                change_df = pd.DataFrame(change_tup,columns=['hazard_type','department_id','climate_scenario','year','change'])
                change_df.to_csv(os.path.join(config['paths']['output'],
                    'hazard_scenarios',
                    '{}_climate_change.csv'.format(mode)
                    ), index=False
                )

                # Change effects
                change_df = change_df.set_index(hazard_cols)
                scenarios = list(set(change_df.index.values.tolist()))
                for sc in scenarios:
                    hazard_type = sc[0]
                    climate_scenario = sc[1]
                    year = sc[2]
                    percentage = change_df.loc[[sc], 'change'].values.tolist()
                    communes = change_df.loc[[sc], 'department_id'].values.tolist()
                    communes_df = pd.DataFrame(list(zip(communes,percentage)),columns=['department_id','change'])
                    commune_vals = pd.merge(region_file,communes_df,how='left',on=['department_id']).fillna(0)
                    del percentage,communes,communes_df

                    proj = ccrs.PlateCarree()
                    ax = get_axes()
                    plot_basemap(ax, data_path)
                    scale_bar(ax, location=(0.8, 0.05))
                    plot_basemap_labels(ax, data_path, include_regions=True)

                    name = [c['name'] for c in plot_set if c['hazard'] == hazard_type][0]
                    for iter_,record in commune_vals.iterrows():
                        geom = record.geometry
                        region_val = record.change
                        if region_val:
                            cl = [c for c in range(len((change_ranges))) if region_val >= change_ranges[c][0] and region_val < change_ranges[c][1]]
                            if cl:
                                c = cl[0]
                                ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                                facecolor=change_colors[c], label=change_labels[c])
                            else:
                                ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                                facecolor=change_colors[-1], label=change_labels[-1])

                    # Legend
                    legend_handles = []
                    for c in range(len(change_colors)):
                        legend_handles.append(mpatches.Patch(color=change_colors[c], zorder=11,label=change_labels[c]))

                    ax.legend(
                        handles=legend_handles,
                        title='Percentage change in exposure',
                        loc='lower right',
                        fancybox=True,
                        framealpha=1.0
                    )
                    if climate_scenario == 'none':
                        climate_scenario = 'current'
                    else:
                        climate_scenario = climate_scenario.upper()
                    plt.title('Percentage change for {} {} {}'.format(name,climate_scenario,year), fontsize=14)
                    output_file = os.path.join(config['paths']['figures'],
                                               '{}-{}-{}-{}-exposure-change-percentage.png'.format(mode.replace(' ',''),name,climate_scenario.replace('.',''),year))
                    save_fig(output_file)
                    plt.close()

            # Absolute effects
            all_edge_fail_scenarios = all_edge_fail_scenarios.reset_index()
            all_edge_fail_scenarios = all_edge_fail_scenarios.set_index(hazard_cols)
            scenarios = list(set(all_edge_fail_scenarios.index.values.tolist()))
            for sc in scenarios:
                hazard_type = sc[0]
                climate_scenario = sc[1]
                year = sc[2]
                percentage = all_edge_fail_scenarios.loc[[sc], 'percentage'].values.tolist()
                communes = all_edge_fail_scenarios.loc[[sc], 'department_id'].values.tolist()
                communes_df = pd.DataFrame(list(zip(communes,percentage)),columns=['department_id','percentage'])
                commune_vals = pd.merge(zones,communes_df,how='left',on=['department_id']).fillna(0)
                del percentage,communes,communes_df

                proj = ccrs.PlateCarree()
                ax = get_axes()
                plot_basemap(ax, data_path)
                scale_bar(ax, location=(0.8, 0.05))
                plot_basemap_labels(ax, data_path, include_regions=True)

                colors = [c['color'] for c in plot_set if c['hazard'] == hazard_type][0]
                name = [c['name'] for c in plot_set if c['hazard'] == hazard_type][0]

                for iter_,record in commune_vals.iterrows():
                    geom = record.geometry
                    region_val = record.percentage
                    if region_val:
                        if region_val > 0 and region_val <= 5:
                            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                              facecolor=colors[0], label=labels[0])
                        elif region_val > 5 and region_val <= 10:
                            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                              facecolor=colors[1], label=labels[1])
                        if region_val > 10 and region_val <= 20:
                            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                              facecolor=colors[2], label=labels[2])
                        elif region_val > 20 and region_val <= 30:
                            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                              facecolor=colors[3], label=labels[3])
                        elif region_val > 30 and region_val <= 100:
                            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                              facecolor=colors[4], label=labels[4])

                    else:
                        ax.add_geometries([geom], crs=proj, edgecolor='#ffffff',
                                          facecolor=colors[5], label=labels[5])

                # Legend
                legend_handles = []
                for c in range(len(colors)):
                    legend_handles.append(mpatches.Patch(color=colors[c], label=labels[c]))
                
                ax.legend(
                    handles=legend_handles,
                    title='Percentage exposure',
                    loc=(0.6,0.2),
                    fancybox=True,
                    framealpha=1.0
                )
                if climate_scenario == 'none':
                    climate_scenario = 'current'
                else:
                    climate_scenario = climate_scenario.upper()
                plt.title('Percentage exposure for {}-year {} {} {}'.format(rp,name,climate_scenario,year), fontsize=10)
                output_file = os.path.join(config['paths']['figures'],
                                           '{}-{}-year-{}-{}-{}-exposure-percentage.png'.format(mode.replace(' ',''),rp,name,climate_scenario.replace('.',''),year))
                save_fig(output_file)
                plt.close()


if __name__ == '__main__':
    main()
