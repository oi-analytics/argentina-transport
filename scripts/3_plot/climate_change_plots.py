"""Plot adaptation cost ranges (national results)
"""
import sys
import os
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from atra.utils import *

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 10.
mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 10.
mpl.rcParams['xtick.labelsize'] = 9.
mpl.rcParams['ytick.labelsize'] = 9.


def plot_values(input_data,index_column,index_values,x_column,y_column,division_factor,x_label,y_label,plot_title,plot_colors,plot_markers,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))
    for i in range(len(index_values)):
        xy_data = input_data[input_data[index_column] == index_values[i]]
        x_data = xy_data
        ax.plot(xy_data[x_column],
            1.0*xy_data[y_column]/division_factor,
            linewidth=0.5,
            color=plot_colors[i],
            marker = plot_markers[i],
            label = index_values[i].replace('_',' ')
        )

    # ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper left')
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def main():
    config = load_config()
    modes = ['road','rail','bridge','port','air']
    modes_y_labels = ['Length flooded (km)','Length flooded (km)','Numbers flooded','Numbers flooded','Numbers flooded']
    modes_y_titles = ['Length exposed','Length exposed','Numbers exposed','Numbers exposed','Numbers exposed']
    modes_y_column = ['exposure_length_km','exposure_length_km','counts','counts','counts']
    # modes_colors = ['#000004','#006d2c','#0689d7','#045a8d']
    flood_colors = ['#252525','#54278f','#08519c']
    flood_markers = [None,'s','8']
    flood_columns = ['Baseline','Future_Med','Future_High']
    # flood_colors = ['#252525','#54278f']
    flood_labels = ['Fluvial flooding','Pluvial flooding']
    for f in flood_labels:
        for m in range(len(modes)):
            stats_path = os.path.join(config['paths']['output'], 'network_stats',
                                           'national_scale_hazard_intersections_summary.xlsx')
            stats_file = pd.read_excel(stats_path,sheet_name=modes[m]).fillna(0)
            if 'return_period' not in stats_file.columns.values.tolist():
                stats_file['return_period'] = 1.0/stats_file['probability']

            plt_file_path = os.path.join(config['paths']['figures'],'{}-{}-climate-change-exposures-ranges.png'.format(modes[m],f.replace(' ','')))
            plot_values(stats_file[stats_file['hazard_type'] == f.lower()],
                'climate_scenario',
                flood_columns,
                'return_period',
                modes_y_column[m],
                1,
                "Return period (years)",
                modes_y_labels[m],
                "{} - {} to {}".format(modes[m].title(),modes_y_titles[m],f),
                flood_colors,
                flood_markers,
                plt_file_path
                )

if __name__ == '__main__':
    main()
