"""Plot country and administrative areas
"""
import os

from oia.utils import load_config, get_axes, plot_basemap, scale_bar, plot_basemap_labels, save_fig


def main(config):
    """Read shapes, plot map
    """
    output_file = os.path.join(config['paths']['figures'], 'admin-map.png')
    ax = get_axes()
    plot_basemap(ax, config['paths']['data'])
    scale_bar(ax, location=(0.8, 0.05))
    plot_basemap_labels(ax, config['paths']['data'], include_regions=True)
    save_fig(output_file)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
