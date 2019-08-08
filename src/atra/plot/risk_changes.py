"""Road network risks and adaptation maps
"""
import os
import sys
from collections import defaultdict
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
from matplotlib.ticker import (MaxNLocator,LinearLocator, MultipleLocator)
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

def main():
    config = load_config()
    output_path = config['paths']['output']
    value_thr = 500000
    duration = [10,30]
    mode_colors = ['#636363','#1a9850','#d73027']
    modes = ['road','rail','bridge']
    risk_types = ['risks','eael','risks']
    risk_title = ['Risks','EAEL','Risks']
    xticks_loc = [-100,-75,-50,-25,0,25,50,75,100]
    x_ticks_labels = [r"$\leq$-100",'-75','-50','-25','0','25','50','75',r"$\geq$100"]

    for dur in duration:
        for m in range(len(modes)):
            # change_df = change_df[change_df['future'] != -1]

            change_df = pd.read_csv(os.path.join(output_path,
                'network_stats',
                'national_{}_{}_days_{}_climate_change_combined.csv'.format(modes[m],dur,risk_types[m])
                )
            )

            # Change effects
            scenarios = list(set(change_df.climate_scenario.values.tolist()))
            for sc in scenarios:
                vals = change_df[change_df['climate_scenario'] == sc]
                cv = []
                ch = []
                for record in vals.itertuples():
                    # if record.current > value_thr or record.future > value_thr:
                    if record.current > value_thr:
                        current = record.current
                        change_val = record.change
                        if change_val >= 100:
                            change_val = 100
                        elif change_val <= -100:
                            change_val = -100

                        cv.append(1e-6*current)
                        ch.append(change_val)
                
             
                fig, ax = plt.subplots(figsize=(8, 4))
                plt.scatter(np.array(ch),np.array(cv),alpha=0.5,s=8,color=mode_colors[m])

                ax.yaxis.set_major_locator(MaxNLocator(nbins=10))
                x_label = 'Change in {} (%)'.format(risk_title[m])
                y_label = 'Current {} (million US$)'.format(risk_title[m])
                plot_title = '{} - Baseline {} and change to {}'.format(modes[m].title(),risk_title[m],sc.replace('_',' '))
                plot_file_path = os.path.join(config['paths']['figures'],
                            'national-{}-{}-{}-{}-days-change-scatter-plot.png'.format(modes[m],sc,risk_types[m],dur))
                
                plt.xticks(xticks_loc,x_ticks_labels)
                plt.xlabel(x_label, fontweight='bold')
                plt.ylabel(y_label, fontweight='bold')
                plt.title(plot_title)

                plt.tight_layout()
                plt.savefig(plot_file_path, dpi=500)
                plt.close()


        for m in range(len(modes)):
            # change_df = change_df[change_df['future'] != -1]
            change_df = pd.read_csv(os.path.join(config['paths']['output'],
                'network_stats',
                'national_{}_{}_days_{}_climate_change_combined.csv'.format(modes[m],dur,risk_types[m])
                )
            )
            fig, ax = plt.subplots(figsize=(8, 4))
            # Change effects
            scenarios = list(set(change_df.climate_scenario.values.tolist()))
            for sc in scenarios:
                vals = change_df[change_df['climate_scenario'] == sc]
                cv = []
                ch = []
                for record in vals.itertuples():
                    # if record.current > value_thr or record.future > value_thr:
                    if record.current > value_thr:
                        current = record.current
                        change_val = record.change
                        if change_val >= 100:
                            change_val = 100
                        elif change_val <= -100:
                            change_val = -100

                        cv.append(1e-6*current)
                        ch.append(change_val)
                
                if sc == 'Future_Med':
                    color = 'tab:green' # 'tab:orange', 'tab:green'
                    label = 'Future Median'
                else:
                    color = 'tab:blue'
                    label = 'Future High'
                plt.scatter(np.array(ch),np.array(cv),alpha=0.5,color=color,label=label)

                # ax.set_yscale('log')
                # And a corresponding grid
                # cv_max = max(cv)+1
                # b = ax.yaxis.set_major_locator(MultipleLocator(cv_max/10))
                # print (b)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=10))
            ax.legend()
            x_label = 'Change in {} (%)'.format(risk_title[m])
            y_label = 'Current {} (million US$)'.format(risk_title[m])
            plot_title = '{} - Baseline {} and change to Future {} > {:,} US$'.format(modes[m].title(),
                                                                                    risk_title[m],
                                                                                    risk_title[m],
                                                                                    value_thr)
            plot_file_path = os.path.join(config['paths']['figures'],
                        'national-{}-{}-{}-days-change-scatter-plot.png'.format(modes[m],risk_types[m],dur))
            # ax.tick_params(axis='x', rotation=45)
            plt.xticks(xticks_loc,x_ticks_labels)
            plt.xlabel(x_label, fontweight='bold')
            plt.ylabel(y_label, fontweight='bold')
            plt.title(plot_title)

            plt.tight_layout()
            plt.savefig(plot_file_path, dpi=500)
            plt.close()
    


if __name__ == '__main__':
    main()
