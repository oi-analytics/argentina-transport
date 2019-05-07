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
from oia.utils import *

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 10.
mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 10.
mpl.rcParams['xtick.labelsize'] = 9.
mpl.rcParams['ytick.labelsize'] = 9.

def plot_ranges(input_data, division_factor,x_label, y_label,plot_title,plot_color,plot_file_path):
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

    # ax.tick_params(axis='x', rotation=45)
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def plot_many_ranges(input_dfs, division_factor,x_label, y_label,plot_title,plot_color,plot_labels,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))

    length = []
    for i in range(len(input_dfs)):
        input_data = input_dfs[i]

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
        length.append(len(vals_min_max[0]))
        ax.plot(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax.plot(percentlies,
            1.0*np.array(vals_min_max[1])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax.fill_between(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            1.0*np.array(vals_min_max[1])/division_factor,
            alpha=0.5,
            edgecolor=None,
            facecolor=plot_color[i],
            label = plot_labels[i]
        )

    length = max(length)
    if 'BCR' in y_label:
        ax.plot(np.arange(0,100),
            np.array([1]*100),
            linewidth=0.5,
            color='red',
            label = 'BCR = 1'
        )
        ax.set_yscale('log')

    # ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper left')
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def plot_many_ranges_subplots(input_dfs, division_factor,x_label, y_label,plot_title,plot_color,plot_labels,plot_file_path):
    # fig, ax = plt.subplots(figsize=(8, 4))
    fig, ax = plt.subplots(1, len(input_dfs), figsize=(8, 4), sharey=True)

    length = []
    for i in range(len(input_dfs)):
        input_data = input_dfs[i]

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
        length.append(len(vals_min_max[0]))
        ax[i].plot(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax[i].plot(percentlies,
            1.0*np.array(vals_min_max[1])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax[i].fill_between(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            1.0*np.array(vals_min_max[1])/division_factor,
            alpha=0.5,
            edgecolor=None,
            facecolor=plot_color[i],
            label = plot_labels[i]
        )

        if 'BCR' in y_label:
            ax[i].plot(np.arange(0,100),
                np.array([1]*100),
                linewidth=0.5,
                color='red',
                label = 'BCR = 1'
            )
            ax[i].set_yscale('log')

        # ax[i].set_yscale('log')

        # ax[i].tick_params(axis='x', rotation=45)
        ax[i].legend(loc='upper left')
        ax[i].set_xlabel(x_label, fontweight='bold')
    
    # fig.text(0.5, 0.04, 'Hazard scenarios', ha="center", va="center", fontweight='bold')
    fig.text(0.015, 0.5, y_label, ha="center", va="center", rotation=90, fontweight='bold')

    fig.text(0.5, 0.98, plot_title, ha="center", va="center", fontweight='bold')
    # plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize = 8)
    fig.subplots_adjust(hspace=0)

    # plt.ylabel(y_label, fontweight='bold')
    # plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def main():
    config = load_config()
    modes = ['road','rail','port','bridge']
    modes_id = ['edge_id','edge_id','node_id','bridge_id']
    modes_name = ['road','rail','waterways','bridges']
    modes_colors = ['#000004','#006d2c','#0689d7','#045a8d']
    flood_colors_change = ['#252525','#54278f','#08519c']
    flood_labels_change = ['Baseline','Future Median','Future High']
    flood_colors = ['#252525','#54278f']
    flood_labels = ['Fluvial','Pluvial']
    adapt_cols = ['min_benefit','min_ini_adap_cost','min_tot_adap_cost','min_bc_ratio','max_benefit','max_ini_adap_cost','max_tot_adap_cost','max_bc_ratio']
    adapt_groups = [['min_benefit','max_benefit'],['min_ini_adap_cost','max_ini_adap_cost'],['min_tot_adap_cost','max_tot_adap_cost'],['min_bc_ratio','max_bc_ratio']]
    adapt_names = ['benefit','ini_adap_cost','tot_adap_cost','bc_ratio']
    adapt_labels = ['Benefits','Initial investments','Total investments', 'BCR']
    adapt_units = ['million USD','million USD','million USD','ratio']
    adapt_divisor = [1000000,1000000,1000000,1]
    duration = 10
    for m in range(len(modes)):
        flow_file_path = os.path.join(config['paths']['output'], 'flow_mapping_combined',
                                       'weighted_flows_{}_100_percent.csv'.format(modes[m]))
        flow_file = pd.read_csv(flow_file_path).fillna(0)
        flow_file = flow_file[(flow_file['min_total_tons'] > 0) | (flow_file['max_total_tons'] > 0)]
        # flow_file = flow_file.sort_values(['max_total_tons'], ascending=True)
        plt_file_path = os.path.join(config['paths']['figures'],'national-{}-aadf-ranges.png'.format(modes[m]))
        plot_ranges(flow_file[['min_total_tons','max_total_tons']],1000, "Percentile rank (%)",
                "AADF ('000 tons/day)","{} - Range of AADF flows on links".format(modes_name[m].title()),modes_colors[m],plt_file_path)

        if modes[m] in ['road','rail','bridge']:
            flow_file_path = os.path.join(config['paths']['output'], 'failure_results','minmax_combined_scenarios',
                                       'single_edge_failures_minmax_{}_100_percent_disrupt.csv'.format(modes[m]))
            flow_file = pd.read_csv(flow_file_path).fillna(0)
            plt_file_path = os.path.join(config['paths']['figures'],'national-{}-economic-impact-ranges.png'.format(modes[m]))
            plot_ranges(flow_file[['min_econ_impact','max_econ_impact']],1000000, "Percentile rank(%)",
                    "Economic impacts (million USD/day)","{} - Range of total economic impacts due to single link failures".format(modes[m].title()),modes_colors[m],plt_file_path)

            plt_file_path = os.path.join(config['paths']['figures'],'national-{}-rerout-loss-ranges.png'.format(modes[m]))
            plot_ranges(flow_file[['min_tr_loss','max_tr_loss']],1000000, "Percentile rank(%)",
                    "Rerouting losses (million USD/day)","{} - Range of rerouting losses due to single link failures".format(modes[m].title()),modes_colors[m],plt_file_path)

            plt_file_path = os.path.join(config['paths']['figures'],'national-{}-macroeconomic-loss-ranges.png'.format(modes[m]))
            plot_ranges(flow_file[['min_econ_loss','max_econ_loss']],1000000, "Percentile rank(%)",
                    "Economic losses (million USD/day)","{} - Range of macroeconomic losses due to single link failures".format(modes[m].title()),modes_colors[m],plt_file_path)


            flow_file_path = os.path.join(config['paths']['output'], 'network_stats',
                               'national_{}_hazard_intersections_risks.csv'.format(modes[m]))

            fail_scenarios = pd.read_csv(flow_file_path)
            fail_scenarios = pd.merge(fail_scenarios,flow_file,how='left',on=[modes_id[m]]).fillna(0)
            fail_scenarios = fail_scenarios[fail_scenarios['max_econ_impact'] > 0]
            fail_scenarios['min_eael'] = duration*fail_scenarios['risk_wt']*fail_scenarios['min_econ_impact']
            fail_scenarios['max_eael'] = duration*fail_scenarios['risk_wt']*fail_scenarios['max_econ_impact']

            # fail_flu = fail_scenarios[fail_scenarios['hazard_type'] == 'fluvial flooding']
            # fail_flu.rename(columns={'min_eael':'min_eael_flu','max_eael':'max_eael_flu'},inplace=True)
            # # fail_rcp45_min = fail_rcp45.groupby([modes_id[m]])['min_eael_rcp45'].min().reset_index()
            # # fail_rcp45_max = fail_rcp45.groupby([modes_id[m]])['max_eael_rcp45'].max().reset_index()
            # # fail_rcp45 = pd.merge(fail_rcp45_min,fail_rcp45_max,how='left',on=[modes_id[m]]).fillna(0)
            # fail_flu = fail_flu.sort_values(['max_eael_flu'], ascending=True)

            # fail_plu = fail_scenarios[fail_scenarios['hazard_type'] == 'pluvial flooding']
            # fail_plu.rename(columns={'min_eael':'min_eael_plu','max_eael':'max_eael_plu'},inplace=True)
            # # fail_rcp45_min = fail_rcp45.groupby([modes_id[m]])['min_eael_rcp45'].min().reset_index()
            # # fail_rcp45_max = fail_rcp45.groupby([modes_id[m]])['max_eael_rcp45'].max().reset_index()
            # # fail_rcp45 = pd.merge(fail_rcp45_min,fail_rcp45_max,how='left',on=[modes_id[m]]).fillna(0)
            # fail_plu = fail_plu.sort_values(['max_eael_plu'], ascending=True)

            # fail_dfs = [fail_flu[['min_eael_flu','max_eael_flu']],fail_plu[['min_eael_plu','max_eael_plu']]]
            # print (fail_scenarios)

            for flooding in ['fluvial flooding','pluvial flooding']: 
                fail_rcp45 = fail_scenarios[(fail_scenarios['hazard_type'] == flooding) & (fail_scenarios['year'] > 2016) & (fail_scenarios['climate_scenario'] == 'Future_Med')]
                fail_rcp45.rename(columns={'min_eael':'min_eael_rcp45','max_eael':'max_eael_rcp45'},inplace=True)
                fail_rcp45_min = fail_rcp45.groupby([modes_id[m]])['min_eael_rcp45'].min().reset_index()
                fail_rcp45_max = fail_rcp45.groupby([modes_id[m]])['max_eael_rcp45'].max().reset_index()
                fail_rcp45 = pd.merge(fail_rcp45_min,fail_rcp45_max,how='left',on=[modes_id[m]]).fillna(0)
                fail_rcp45 = fail_rcp45.sort_values(['max_eael_rcp45'], ascending=True)

                fail_rcp85 = fail_scenarios[(fail_scenarios['hazard_type'] == flooding) & (fail_scenarios['year'] > 2016) & (fail_scenarios['climate_scenario'] == 'Future_High')]
                fail_rcp85.rename(columns={'min_eael':'min_eael_rcp85','max_eael':'max_eael_rcp85'},inplace=True)
                fail_rcp85_min = fail_rcp85.groupby([modes_id[m]])['min_eael_rcp85'].min().reset_index()
                fail_rcp85_max = fail_rcp85.groupby([modes_id[m]])['max_eael_rcp85'].max().reset_index()
                fail_rcp85 = pd.merge(fail_rcp85_min,fail_rcp85_max,how='left',on=[modes_id[m]]).fillna(0)
                fail_rcp85 = fail_rcp85.sort_values(['max_eael_rcp85'], ascending=True)

                fail_cur = fail_scenarios[(fail_scenarios['hazard_type'] == flooding) & (fail_scenarios['year'] == 2016)]
                fail_min = fail_cur.groupby([modes_id[m]])['min_eael'].min().reset_index()
                fail_max = fail_cur.groupby([modes_id[m]])['max_eael'].max().reset_index()
                fail_cur = pd.merge(fail_min,fail_max,how='left',on=[modes_id[m]]).fillna(0)
                fail_cur = fail_cur.sort_values(['max_eael'], ascending=True)

                fail_dfs = [fail_cur[['min_eael','max_eael']],fail_rcp45[['min_eael_rcp45','max_eael_rcp45']],fail_rcp85[['min_eael_rcp85','max_eael_rcp85']]]
                # print (fail_dfs)

                plt_file_path = os.path.join(config['paths']['figures'],'national-{}-{}-eael-ranges.png'.format(modes[m],flooding.replace(' ','-')))
                plot_many_ranges_subplots(fail_dfs,1000000, "Percentile rank (%)",
                        "EAEL (million USD)",
                        "{} - Range of EAEL due to link failures to {}".format(modes[m].title(),
                            flooding.title()),
                        flood_colors_change,flood_labels_change,plt_file_path)

        # if modes[m] == 'road':
        #     flow_file_path = os.path.join(config['paths']['output'], 'adaptation_results',
        #                            'output_adaptation_national_road_10_days_max_disruption_fixed_parameters.csv')
        #     fail_scenarios = pd.read_csv(flow_file_path)
        #     fail_scenarios = fail_scenarios[fail_scenarios['max_econ_impact'] > 0]

        #     for cols in ['min_ini_adap_cost','max_ini_adap_cost']:
        #         fail_scenarios[cols] = fail_scenarios[cols].apply(lambda x: np.max(np.array(ast.literal_eval(x))))

        #     # fail_scenarios = fail_scenarios.groupby([modes_id[m]])[adapt_cols].max().reset_index()

        #     for c in range(len(adapt_groups)):
        #         cols = adapt_groups[c]
        #         new_cols = ['{}_rcp45'.format(cols[0]),'{}_rcp45'.format(cols[1])]
        #         fail_rcp45 = fail_scenarios[(fail_scenarios['hazard_type'] == 'flooding') & (fail_scenarios['year'] > 2016) & (fail_scenarios['climate_scenario'] == 'rcp 4.5')]
        #         fail_rcp45 = fail_rcp45.groupby([modes_id[m]])[cols].max().reset_index()
        #         fail_rcp45.rename(columns={cols[0]:new_cols[0],cols[1]:new_cols[1]},inplace=True)
        #         fail_rcp45_min = fail_rcp45.groupby([modes_id[m]])[new_cols[0]].min().reset_index()
        #         fail_rcp45_max = fail_rcp45.groupby([modes_id[m]])[new_cols[1]].max().reset_index()
        #         fail_rcp45 = pd.merge(fail_rcp45_min,fail_rcp45_max,how='left',on=[modes_id[m]]).fillna(0)
        #         fail_rcp45 = fail_rcp45.sort_values([new_cols[1]], ascending=True)
        #         fail_rcp45 = fail_rcp45[new_cols]

        #         new_cols = ['{}_rcp85'.format(cols[0]),'{}_rcp85'.format(cols[1])]
        #         fail_rcp85 = fail_scenarios[(fail_scenarios['hazard_type'] == 'flooding') & (fail_scenarios['year'] > 2016) & (fail_scenarios['climate_scenario'] == 'rcp 4.5')]
        #         fail_rcp85 = fail_rcp85.groupby([modes_id[m]])[cols].max().reset_index()
        #         fail_rcp85.rename(columns={cols[0]:new_cols[0],cols[1]:new_cols[1]},inplace=True)
        #         fail_rcp85_min = fail_rcp85.groupby([modes_id[m]])[new_cols[0]].min().reset_index()
        #         fail_rcp85_max = fail_rcp85.groupby([modes_id[m]])[new_cols[1]].max().reset_index()
        #         fail_rcp85 = pd.merge(fail_rcp85_min,fail_rcp85_max,how='left',on=[modes_id[m]]).fillna(0)
        #         fail_rcp85 = fail_rcp85.sort_values([new_cols[1]], ascending=True)
        #         fail_rcp85 = fail_rcp85[new_cols]

        #         fail_cur = fail_scenarios[(fail_scenarios['hazard_type'] == 'flooding') & (fail_scenarios['year'] == 2016)]
        #         fail_cur = fail_cur.groupby([modes_id[m]])[cols].max().reset_index()
        #         fail_min = fail_cur.groupby([modes_id[m]])[cols[0]].min().reset_index()
        #         fail_max = fail_cur.groupby([modes_id[m]])[cols[1]].max().reset_index()
        #         fail_cur = pd.merge(fail_min,fail_max,how='left',on=[modes_id[m]]).fillna(0)
        #         fail_cur = fail_cur.sort_values([cols[1]], ascending=True)
        #         fail_cur = fail_cur[cols]

        #         fail_dfs = [fail_cur,fail_rcp45,fail_rcp85]
        #         plt_file_path = os.path.join(config['paths']['figures'],'national-road-{}-flooding-ranges-fixed-paramters.png'.format(adapt_names[c]))
        #         plot_many_ranges(fail_dfs,adapt_divisor[c], "Percentile rank".format(adapt_labels[c]),
        #                 "{} ({})".format(adapt_labels[c],adapt_units[c]),"Range of {} of adaptation".format(adapt_labels[c]),flood_colors,flood_labels,plt_file_path)
if __name__ == '__main__':
    main()
