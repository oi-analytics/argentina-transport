"""Shared plotting functions
"""
import csv
import json
import math
import os

from collections import namedtuple, OrderedDict

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from boltons.iterutils import pairwise
from geopy.distance import vincenty
from osgeo import gdal


def load_config():
    """Read config.json
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r') as config_fh:
        config = json.load(config_fh)
    return config


def get_axes(extent=(-74.04, -52.90, -20.29, -57.38), epsg=None):
    """Get map axes

    Default to Argentina extent // Lambert Conformal projection
    """
    if epsg is not None:
        ax_proj = ccrs.epsg(epsg)
    else:
        x0, x1, y0, y1 = extent
        cx = x0 + ((x1 - x0) / 2)
        cy = y0 + ((y1 - y0) / 2)
        ax_proj = ccrs.TransverseMercator(central_longitude=cx, central_latitude=cy)

    plt.figure(figsize=(6, 10), dpi=300)
    ax = plt.axes([0.025, 0.025, 0.95, 0.95], projection=ax_proj)
    proj = ccrs.PlateCarree()
    ax.set_extent(extent, crs=proj)
    set_ax_bg(ax)
    return ax


def save_fig(output_filename):
    plt.savefig(output_filename)


def set_ax_bg(ax, color='#c6e0ff'):
    """Set axis background color
    """
    ax.background_patch.set_facecolor(color)


def plot_basemap(ax, data_path, focus='ARG', neighbours=('CHL', 'BOL', 'PRY', 'BRA', 'URY'),
                 country_border='white', plot_regions=True):
    """Plot countries and regions background
    """
    proj = ccrs.PlateCarree()

    states_filename = os.path.join(
        data_path,
        'boundaries',
        'admin_0_boundaries.shp'
    )

    provinces_filename = os.path.join(
        data_path,
        'boundaries',
        'admin_1_boundaries.shp'
    )

    lakes_filename = os.path.join(
        data_path,
        'boundaries',
        'physical_lakes.shp'
    )

    # Neighbours
    for record in shpreader.Reader(states_filename).records():
        country_code = record.attributes['ISO_A3']
        if country_code == focus or country_code in neighbours:
            geom = record.geometry
            ax.add_geometries(
                [geom],
                crs=proj,
                edgecolor=country_border,
                facecolor='#e0e0e0',
                zorder=1)

    # Regions
    if plot_regions:
        for record in shpreader.Reader(provinces_filename).records():
            geom = record.geometry
            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff', facecolor='#d2d2d2')

    # Lakes
    for record in shpreader.Reader(lakes_filename).records():
        geom = record.geometry
        ax.add_geometries(
            [geom],
            crs=proj,
            edgecolor='none',
            facecolor='#c6e0ff',
            zorder=1)

def plot_basemap_labels(ax, data_path, labels=None, include_regions=False):
    """Plot countries and regions background
    """
    proj = ccrs.PlateCarree()
    extent = ax.get_extent()
    if labels is None:
        labels = load_labels(data_path, include_regions)

    for text, x, y, size in labels:
        if within_extent(x, y, extent):
            ax.text(
                x, y,
                text,
                alpha=0.7,
                size=size,
                horizontalalignment='center',
                transform=proj)


def load_labels(data_path, include_regions):
    labels_filename = os.path.join(
        data_path,
        'boundaries',
        'labels.csv'
    )
    region_labels_filename = os.path.join(
        data_path,
        'boundaries',
        'region_labels.csv'
    )
    labels = []
    with open(labels_filename, 'r') as fh:
        reader = csv.reader(fh)
        header = next(reader)
        print(header)
        assert header == ['text', 'lon', 'lat', 'size']
        labels = [(text, float(lon), float(lat), int(size))
            for text, lon, lat, size in reader]

    region_labels = []
    if include_regions:
        with open(region_labels_filename, 'r') as fh:
            reader = csv.reader(fh)
            print(header)
            header = next(reader)
            assert header == ['text', 'lon', 'lat', 'size']
            region_labels = [(text, float(lon), float(lat), int(size))
                for text, lon, lat, size in reader]

    return labels + region_labels


def within_extent(x, y, extent):
    """Test x, y coordinates against (xmin, xmax, ymin, ymax) extent
    """
    xmin, xmax, ymin, ymax = extent
    return (xmin < x) and (x < xmax) and (ymin < y) and (y < ymax)


def scale_bar(ax, length=100, location=(0.5, 0.05), linewidth=3):
    """Draw a scale bar

    Adapted from https://stackoverflow.com/questions/32333870/how-can-i-show-a-km-ruler-on-a-cartopy-matplotlib-plot/35705477#35705477

    Parameters
    ----------
    ax : axes
    length : int
        length of the scalebar in km.
    location: tuple
        center of the scalebar in axis coordinates (ie. 0.5 is the middle of the plot)
    linewidth: float
        thickness of the scalebar.
    """
    # lat-lon limits
    llx0, llx1, lly0, lly1 = ax.get_extent(ccrs.PlateCarree())

    # Transverse mercator for length
    x = (llx1 + llx0) / 2
    y = lly0 + (lly1 - lly0) * location[1]
    tmc = ccrs.TransverseMercator(x, y)

    # Extent of the plotted area in coordinates in metres
    x0, x1, y0, y1 = ax.get_extent(tmc)

    # Scalebar location coordinates in metres
    sbx = x0 + (x1 - x0) * location[0]
    sby = y0 + (y1 - y0) * location[1]
    bar_xs = [sbx - length * 500, sbx + length * 500]

    # Plot the scalebar and label
    ax.plot(bar_xs, [sby, sby], transform=tmc, color='k', linewidth=linewidth)
    ax.text(sbx, sby + 10*length, str(length) + ' km', transform=tmc,
            horizontalalignment='center', verticalalignment='bottom', size=8)


def generate_weight_bins(weights, n_steps=9, width_step=0.01):
    """Given a list of weight values, generate <n_steps> bins with a width
    value to use for plotting e.g. weighted network flow maps.
    """
    min_weight = min(weights)
    max_weight = max(weights)

    width_by_range = OrderedDict()

    mins = np.linspace(min_weight, max_weight, n_steps)
    maxs = list(mins)
    maxs.append(max_weight*10)
    maxs = maxs[1:]

    assert len(maxs) == len(mins)

    for i, (min_, max_) in enumerate(zip(mins, maxs)):
        width_by_range[(min_, max_)] = (i+1) * width_step

    return width_by_range


Style = namedtuple('Style', ['color', 'zindex', 'label'])
Style.__doc__ += """: class to hold an element's styles

Used to generate legend entries, apply uniform style to groups of map elements
(See network_map.py for example.)
"""


def legend_from_style_spec(ax, styles, loc='lower left'):
    """Plot legend
    """
    handles = [
        mpatches.Patch(color=style.color, label=style.label)
        for style in styles.values()
    ]
    ax.legend(
        handles=handles,
        loc=loc
    )


def round_sf(x, places=1):
    """Round number to significant figures
    """
    if x == 0:
        return 0
    sign = x / abs(x)
    x = abs(x)
    exp = math.floor(math.log10(x)) + 1
    shift = 10 ** (exp - places)
    rounded = round(x / shift) * shift
    return rounded * sign


def get_data(filename):
    """Read in data (as array) and extent of each raster
    """
    gdal.UseExceptions()
    ds = gdal.Open(filename)
    data = ds.ReadAsArray()
    data[data < 0] = 0

    gt = ds.GetGeoTransform()

    # get the edge coordinates
    width = ds.RasterXSize
    height = ds.RasterYSize
    xres = gt[1]
    yres = gt[5]

    xmin = gt[0]
    xmax = gt[0] + (xres * width)
    ymin = gt[3] + (yres * height)
    ymax = gt[3]

    lat_lon_extent = (xmin, xmax, ymax, ymin)

    return data, lat_lon_extent


def line_length(line, ellipsoid='WGS-84'):
    """Length of a line in meters, given in geographic coordinates.

    Adapted from https://gis.stackexchange.com/questions/4022/looking-for-a-pythonic-way-to-calculate-the-length-of-a-wkt-linestring#answer-115285

    Args:
        line: a shapely LineString object with WGS-84 coordinates.

        ellipsoid: string name of an ellipsoid that `geopy` understands (see http://geopy.readthedocs.io/en/latest/#module-geopy.distance).

    Returns:
        Length of line in kilometers.
    """
    if line.geometryType() == 'MultiLineString':
        return sum(line_length(segment) for segment in line)

    return sum(
        vincenty(tuple(reversed(a)), tuple(reversed(b)), ellipsoid=ellipsoid).kilometers
        for a, b in pairwise(line.coords)
    )


def gdf_clip(shape_in,clip_geom):
    """
    Inputs are:
        shape_in -- path string to shapefile to be clipped
    Outputs are:
        province_geom -- shapely geometry of province for what we do the calculation
    """
    gdf = gpd.read_file(shape_in)
    gdf = gdf.to_crs({'init': 'epsg:4326'})
    return gdf.loc[gdf['geometry'].apply(lambda x: x.within(clip_geom))].reset_index(drop=True)


def get_nearest_node(x,sindex_nodes,nodes,id_column):
    """
    Inputs are:
        x -- row of dataframe
        sindex_nodes -- spatial index of dataframe of nodes in the network
        nodes -- dataframe of nodes in the network
        id_column -- name of column of id of closest node
    Outputs are:
        Nearest node to geometry of row
    """
    return nodes.loc[list(sindex_nodes.nearest(x.bounds[:2]))][id_column].values[0]


def count_points_in_polygon(row, points_sindex):
    """
   Inputs are:
        row -- row of dataframe
        points_sindex -- spatial index of dataframe with points in the region to consider
    Outputs are:
        Amount of points in polygon
    """
    return len(list(points_sindex.intersection(row.bounds)))


def extract_value_from_gdf(row, gdf_sindex, gdf, column_name):
    """
   Inputs are:
        row -- row of dataframe
        gdf_sindex -- spatial index of dataframe of which we want to extract the value
        gdf -- GeoDataFrame of which we want to extract the value
        column_name -- column that contains the value we want to extract

    Outputs are:
        extracted value from other gdf
    """
    return gdf.loc[list(gdf_sindex.intersection(row.bounds[:2]))][column_name].values[0]
