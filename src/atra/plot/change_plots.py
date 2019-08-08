"""Road network risks and adaptation maps
"""
import os
import sys
from collections import defaultdict
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.ticker import (MaxNLocator,LinearLocator, MultipleLocator)
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
    durations = [10,30,60,100]
    value_thr = 1
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#969696','#fee08b','#fdae61','#f46d43','#d73027']
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0','0 to 10','10 to 50','50 to 100',' > 100']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0,1e-7),(1e-7,10),(10,50),(50,100),(100,1e10)]

    modes = ['roads','bridge']

    # for duration in durations:
    #     for m in range(len(modes)):
    #         # change_df = change_df[change_df['future'] != -1]
    #         change_df = pd.read_csv(os.path.join(config['paths']['output'],
    #             'network_stats',
    #             'national_{}_max_bc_ratios_climate_change_{}_days.csv'.format(modes[m],duration)
    #             )
    #         )

    #         # Change effects
    #         scenarios = list(set(change_df.climate_scenario.values.tolist()))
    #         for sc in scenarios:
    #             change_dict = dict.fromkeys(change_labels,0)
    #             zero = 0
    #             pos = 0
    #             neg = 0
    #             climate_scenario = sc[0]
    #             year = sc[1]
    #             vals = change_df[change_df['climate_scenario'] == sc]
    #             for record in vals.itertuples():
    #                 change_val = record.change
    #                 if record.current > value_thr or record.future > value_thr:
    #                     if change_val == 0:
    #                         zero += 1
    #                     elif change_val > 0:
    #                         pos += 1
    #                     else:
    #                         neg += 1

    #                     cl = [c for c in range(len((change_ranges))) if  change_ranges[c][0] <= change_val < change_ranges[c][1]]
    #                     if cl:
    #                         change_dict[change_labels[cl[0]]] += 1
                         

    #             print ('* Total counts of {} for {} days disruptions in {}: {}'.format(modes[m],duration,sc,sum([v for k,v in change_dict.items()])))
    #             print (change_dict)
    #             print ('* Positive changes: {}, Negative changes: {}, Zero changes: {}'.format(pos,neg,zero))
    #             change_labels, change_vals = list(zip(*[(k,v) for k,v in change_dict.items()]))

    #             fig, ax = plt.subplots(figsize=(8, 4))
    #             ax.bar(np.arange(0,len(change_vals)),change_vals,color=change_colors,tick_label=change_labels)
    #             for i in range(len(change_vals)):
    #                 ax.text(x = i-0.05 , y = change_vals[i]+0.15, s = change_vals[i], size = 8)


    #             x_label = 'Change in BCR (%)'
    #             y_label = 'Numbers of assets with BCR > 1'
    #             plot_title = '{} - Percentage changes from Baseline to {}'.format(modes[m].title(),sc.replace('_',' '))
    #             plot_file_path = os.path.join(config['paths']['figures'],'national-{}-{}-{}-days-change_histogram.png'.format(modes[m],sc,duration))
    #             # ax.tick_params(axis='x', rotation=45)
    #             plt.xlabel(x_label, fontweight='bold')
    #             plt.ylabel(y_label, fontweight='bold')
    #             plt.title(plot_title)

    #             plt.tight_layout()
    #             plt.savefig(plot_file_path, dpi=500)
    #             plt.close()

    
    growth_rate = '2p8'
    duration_list = np.arange(10,110,10)
    # growth_rates = np.arange(-2,4,0.2)
    modes = ['road','bridge']
    modes_id = ['edge_id','bridge_id']
    for m in range(len(modes)):
        change_results = []
        for dur in duration_list:
            adapt_file_path = os.path.join(config['paths']['output'], 
                            'adaptation_results',
                            'combined_climate',
                            'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(modes[m],dur,
                                                                                        growth_rate))

            adapt = pd.read_csv(adapt_file_path,encoding='utf-8-sig')
            adapt = adapt[adapt['max_bc_ratio'] > 1][[modes_id[m],'climate_scenario','max_bc_ratio']]
            adapt_scenarios = pd.DataFrame(list(set(adapt[modes_id[m]].values.tolist())),columns=[modes_id[m]])
            # print (adapt_scenarios)
            climate_scenarios = list(set(adapt['climate_scenario'].values.tolist()))
            # adapt_scenarios = []
            for cl in climate_scenarios:
                adapt_cl = adapt[adapt['climate_scenario'] == cl]
                adapt_cl.rename(columns={'max_bc_ratio':cl.lower().strip()},inplace=True)
                # print (adapt_cl)
                adapt_scenarios = pd.merge(adapt_scenarios,
                                            adapt_cl[[modes_id[m],cl.lower().strip()]],
                                            how='left',on=[modes_id[m]]).fillna(0)

            future_scenarios = [c.lower().strip() for c in climate_scenarios if c.lower().strip() != 'baseline']
            for sc in future_scenarios:
                zero = 0
                pos = 0
                neg = 0
                pos_robust = 0
                neg_robust = 0
                for record in adapt_scenarios.itertuples():
                    if record.baseline == getattr(record, sc):
                        zero+= 1
                    elif record.baseline < getattr(record, sc):
                        pos+= 1
                    else:
                        neg+=1

                    if record.baseline > 1 and getattr(record, sc) < 1:
                        neg_robust+= 1
                    elif record.baseline < 1 and getattr(record, sc) > 1:
                        pos_robust+= 1

                change_results.append((sc,dur,zero,pos,-1.0*neg,pos_robust,-1.0*neg_robust))


            print ('* Done {} {} days disruption'.format(modes[m],dur))

        change_results = pd.DataFrame(change_results,
                                    columns=['climate_scenario',
                                            'days','zero','pos',
                                            'neg','pos_robust','neg_robust'])


        climate_scenarios = list(set(change_results['climate_scenario'].values.tolist()))
        for sc in climate_scenarios:
            cl = change_results[change_results['climate_scenario'] == sc]
            cl = cl.sort_values(['days'], ascending=True)
            fig, ax = plt.subplots(figsize=(8, 4))
            # ax.hlines(y=cl.days, xmin=-5, xmax=5, 
            #         color='tab:grey', alpha=1.0, 
            #         linewidth=5,
            #         label='Baseline BCR = {} BCR > 1'.format(sc.replace('_',' ').title()))

            ax.hlines(y=cl.days, xmin=0, xmax=cl.pos_robust, 
                    color='tab:red', alpha=1.0, 
                    linewidth=5,
                    label='Baseline BCR < 1 < {} BCR'.format(sc.replace('_',' ').title()))
            ax.hlines(y=cl.days, xmin=0, xmax=cl.neg_robust, 
                    color='tab:green', alpha=1.0, 
                    linewidth=5,
                    label='Baseline BCR > 1 > {} BCR'.format(sc.replace('_',' ').title()))

            ax.hlines(y=cl.days, xmin=cl.pos_robust, xmax=cl.pos, 
                    color='tab:red', alpha=0.5, 
                    linewidth=5,
                    label='1 < Baseline BCR < {} BCR'.format(sc.replace('_',' ').title()))
            ax.hlines(y=cl.days, xmin=cl.neg_robust, xmax=cl.neg, 
                    color='tab:green', alpha=0.5, 
                    linewidth=5,
                    label='Baseline BCR > {} BCR > 1'.format(sc.replace('_',' ').title()))
            

            for i in cl.itertuples():
                # ax.text(x = 0 , y = i.days, s = i.zero, size = 6)
                ax.text(x = i.pos+5 , y = i.days, s = i.pos, size = 8)
                ax.text(x = i.pos_robust+0.05 , y = i.days, s = i.pos_robust, size = 8)
                ax.text(x = i.neg-5 , y = i.days, s = int(abs(i.neg)), size = 8)
                ax.text(x = i.neg_robust-0.05 , y = i.days, s = int(abs(i.neg_robust)), size = 8)

            x_label = 'Numbers of changes in BCR from Baseline'
            y_label = 'Max. durations of disruptions (days)'
            plot_title = '{} - BCR changes from Baseline to {}'.format(modes[m].title(),sc.replace('_',' ').title())
            plot_file_path = os.path.join(config['paths']['figures'],
                            '{}-{}-BCR-change-histogram.png'.format(modes[m],sc))
            # ax.tick_params(axis='x', rotation=45)
            # ax.xaxis.set_ticks([])
            ax.xaxis.set_major_locator(MaxNLocator(nbins=20))
            ax.xaxis.set_ticks([])
            ax.yaxis.set_ticks(cl.days.values)
            ax.legend(loc='lower right',fontsize=8)
            plt.xlabel(x_label, fontweight='bold')
            plt.ylabel(y_label, fontweight='bold')
            plt.title(plot_title)

            plt.tight_layout()
            plt.savefig(plot_file_path, dpi=500)
            plt.close()

            # fig, ax = plt.subplots(figsize=(8, 4))
            # ax.hlines(y=cl.days, xmin=0, xmax=cl.pos_robust, 
            #         color='tab:red', alpha=0.4, 
            #         linewidth=5,
            #         label='Baseline BCR < 1; {} BCR > 1'.format(sc.replace('_',' ').title()))
            # ax.hlines(y=cl.days, xmin=0, xmax=cl.neg_robust, 
            #         color='tab:green', alpha=0.4, 
            #         linewidth=5,
            #         label='Baseline BCR > 1; {} BCR > 1'.format(sc.replace('_',' ').title()))

            # ax.legend(loc='lower right',fontsize=8)
            # x_label = 'Changes in BCR from Baseline'
            # y_label = 'Max. durations of disruptions (days)'
            # plot_title = '{} - BCR changes from Baseline to {}'.format(modes[m].title(),sc.replace('_',' ').title())
            # plot_file_path = os.path.join(config['paths']['figures'],
            #                 '{}-{}-BCR-robust-change-histogram.png'.format(modes[m],sc))
            # # ax.tick_params(axis='x', rotation=45)
            # ax.yaxis.set_ticks(cl.days.values)
            # plt.xlabel(x_label, fontweight='bold')
            # plt.ylabel(y_label, fontweight='bold')
            # plt.title(plot_title)

            # plt.tight_layout()
            # plt.savefig(plot_file_path, dpi=500)
            # plt.close()

            print ('* Done {} {} climate scenarios plot'.format(modes[m],sc.replace('_',' ').title()))
if __name__ == '__main__':
    main()
