"""Linear Regression analysis of Global Dams data
   Date: April 08, 2019
   Auhtor: Raghav Pant

   Code segments taken from:
        https://scikit-learn.org/stable/auto_examples/linear_model/plot_ols.html#sphx-glr-download-auto-examples-linear-model-plot-ols-py
"""
import csv
import os
import numpy as np
from tqdm import tqdm
import pandas as pd
from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import matplotlib as mpl
from atra.utils import *

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

    data_df = mode_file[mode_file['road_type'] == 'national']
    print ('Before filtering',len(data_df.index))
    data_df = data_df[(data_df['tmda_count'] > 0) & (data_df['max_total_tons'] > 0)]
    print ('After filtering',len(data_df.index))

    # X = 1.0/365*data_df['tmda_count'].values.reshape(-1, 1) # Transforrm single column data to matrix
    # y = data_df['max_total_tons'].values

    X = np.log(1.0/365*data_df['tmda_count'].values.reshape(-1, 1)) # Transforrm single column data to matrix
    y = np.log(data_df['max_total_tons'].values)
    lm = linear_model.LinearRegression(normalize=True)
    # model = lm.fit(np.log(X),np.log(y))
    model = lm.fit(X,y)
    # Make predictions using the testing set
    # y_pred = np.exp(lm.predict(np.log(X)))
    y_pred = lm.predict(X)

    # The coefficients
    print('Regression coefficients:', model.coef_)
    # The mean squared error
    print("Mean squared error:",mean_squared_error(y, y_pred))
    # Explained variance score: 1 is perfect prediction
    print('Variance score:',r2_score(y, y_pred))


    # Plot outputs
    mpl.style.use('ggplot')
    mpl.rcParams['font.size'] = 10.
    mpl.rcParams['font.family'] = 'tahoma'
    mpl.rcParams['axes.labelsize'] = 10.
    mpl.rcParams['xtick.labelsize'] = 9.
    mpl.rcParams['ytick.labelsize'] = 9.

    fig, ax = plt.subplots(figsize=(8, 4))
    plt.scatter(X.reshape(1,-1)[0], y,color='black')
    plt.plot(X.reshape(1,-1)[0], y_pred, color='blue', linewidth=2)
    # ax.set_yscale('symlog')
    # ax.set_xscale('symlog')
    plt.xlabel('log(AADT) (vehicles/day)', fontweight='bold')
    plt.ylabel('log(AADF) (tons/day)', fontweight='bold')
    plt.tight_layout()
    plot_file_path = os.path.join(
                config['paths']['figures'],
                'road-vehicle-tons-correlations.png')
    plt.savefig(plot_file_path, dpi=500)
    plt.close()


if __name__ == '__main__':
    main()
