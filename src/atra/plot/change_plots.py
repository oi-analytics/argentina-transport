"""Road network risks and adaptation maps
"""
import os
import sys
from collections import defaultdict
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from oia.utils import *
from oia.utils import *

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 10.
mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 10.
mpl.rcParams['xtick.labelsize'] = 9.
mpl.rcParams['ytick.labelsize'] = 9.

def main():
    config = load_config()
    durations = [10,30]
    value_thr = 1
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#969696','#fee08b','#fdae61','#f46d43','#d73027']
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0','0 to 10','10 to 50','50 to 100',' > 100']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0,1e-7),(1e-7,10),(10,50),(50,100),(100,1e10)]

    modes = ['roads','bridge']

    for duration in durations:
        for m in range(len(modes)):
            # change_df = change_df[change_df['future'] != -1]
            change_df = pd.read_csv(os.path.join(config['paths']['output'],
                'network_stats',
                'national_{}_max_bc_ratios_climate_change_{}_days.csv'.format(modes[m],duration)
                )
            )

            # Change effects
            scenarios = list(set(change_df.climate_scenario.values.tolist()))
            for sc in scenarios:
                change_dict = dict.fromkeys(change_labels,0)
                zero = 0
                pos = 0
                neg = 0
                climate_scenario = sc[0]
                year = sc[1]
                vals = change_df[change_df['climate_scenario'] == sc]
                for record in vals.itertuples():
                    change_val = record.change
                    if record.current > value_thr or record.future > value_thr:
                        if change_val == 0:
                            zero += 1
                        elif change_val > 0:
                            pos += 1
                        else:
                            neg += 1

                        cl = [c for c in range(len((change_ranges))) if  change_ranges[c][0] <= change_val < change_ranges[c][1]]
                        if cl:
                            change_dict[change_labels[cl[0]]] += 1
                         

                print ('* Total counts of {} for {} days disruptions in {}: {}'.format(modes[m],duration,sc,sum([v for k,v in change_dict.items()])))
                print (change_dict)
                print ('* Positive changes: {}, Negative changes: {}, Zero changes: {}'.format(pos,neg,zero))
                change_labels, change_vals = list(zip(*[(k,v) for k,v in change_dict.items()]))

                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(np.arange(0,len(change_vals)),change_vals,color=change_colors,tick_label=change_labels)
                for i in range(len(change_vals)):
                    ax.text(x = i-0.05 , y = change_vals[i]+0.15, s = change_vals[i], size = 8)


                x_label = 'Change in BCR (%)'
                y_label = 'Numbers of assets with BCR > 1'
                plot_title = '{} - Percentage changes from Baseline to {}'.format(modes[m].title(),sc.replace('_',' '))
                plot_file_path = os.path.join(config['paths']['figures'],'national-{}-{}-{}-days-change_histogram.png'.format(modes[m],sc,duration))
                # ax.tick_params(axis='x', rotation=45)
                plt.xlabel(x_label, fontweight='bold')
                plt.ylabel(y_label, fontweight='bold')
                plt.title(plot_title)

                plt.tight_layout()
                plt.savefig(plot_file_path, dpi=500)
                plt.close()

    


if __name__ == '__main__':
    main()
