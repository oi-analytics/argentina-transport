"""Plot commodities matrices
"""
import os

import cartopy.crs as ccrs
import pandas

from atra.utils import load_config


def main(config):
    """Read data, plot charts
    """
    data_path = config['paths']['data']
    od_file = os.path.join(data_path, 'usage', 'economic_od.csv')
    od = pandas.read_csv(od_file)

    # TODO extend from notes to proof of concept

    # integer zone ids
    od.from_zone = od.from_zone.apply(lambda z: int(z.replace("econ_", "")))
    od.to_zone = od.to_zone.apply(lambda z: int(z.replace("econ_", "")))

    # pivot and plot
    mat = od[od.sector == 'meat'].drop('sector', axis=1).pivot("from_zone", "to_zone", "value")
    ax = seaborn.heatmap(mat, square=True, cmap='magma_r')


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
