"""Shared plotting functions
"""
import csv
import json
import math
import os

from collections import namedtuple, OrderedDict

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import fiona
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from boltons.iterutils import pairwise
from geopy.distance import vincenty
from osgeo import gdal

import shapely.geometry
import shapely.ops
from boltons.iterutils import pairwise
from colour import Color
from geopy.distance import vincenty
from osgeo import gdal
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, shape

def load_config():
    """Read config.json
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r') as config_fh:
        config = json.load(config_fh)
    return config


def transform_geo_file(source_file, sink_file, sink_schema, transform_record):
    """Transform a fiona-readable file

    Parameters
    ----------
    source_file: str
        source file path
    sink_file: str
        destination file path
    sink_schema: dict
        fiona schema for output
    transform_record: function
        function that accepts a fiona record and returns a fiona record or None
    """
    with fiona.open(source_file) as source:
        with fiona.open(
                sink_file,
                'w',
                driver=source.driver,
                crs=source.crs,
                schema=sink_schema) as sink:
            for record in source:
                out_record = transform_record(record)
                if out_record is not None:
                    sink.write(out_record)


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

    print(" * Setup axes")
    plt.figure(figsize=(6, 10), dpi=300)
    ax = plt.axes([0.025, 0.025, 0.95, 0.95], projection=ax_proj)
    proj = ccrs.PlateCarree()
    ax.set_extent(extent, crs=proj)
    set_ax_bg(ax)
    return ax


def save_fig(output_filename):
    print(" * Save", os.path.basename(output_filename))
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
    print(" * Load countries")
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
        print(" * Load regions")
        for record in shpreader.Reader(provinces_filename).records():
            geom = record.geometry
            ax.add_geometries([geom], crs=proj, edgecolor='#ffffff', facecolor='#d2d2d2')

    # Lakes
    print(" * Load lakes")
    for record in shpreader.Reader(lakes_filename).records():
        geom = record.geometry
        ax.add_geometries(
            [geom],
            crs=proj,
            edgecolor='none',
            facecolor='#c6e0ff',
            zorder=1)

def plot_basemap_labels(ax, data_path, labels=None, include_regions=False, include_zorder=2):
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
                zorder = include_zorder,
                transform=proj)


def load_labels(data_path, include_regions):
    labels_filename = os.path.join(
        data_path,
        'boundaries',
        'admin_0_labels.csv'
    )
    region_labels_filename = os.path.join(
        data_path,
        'boundaries',
        'admin_1_labels.csv'
    )
    labels = []
    with open(labels_filename, 'r', encoding='utf-8-sig') as fh:
        reader = csv.reader(fh)
        header = next(reader)
        assert header == ['text', 'lon', 'lat', 'size']
        labels = [(text, float(lon), float(lat), int(size))
                  for text, lon, lat, size in reader]

    region_labels = []
    if include_regions:
        with open(region_labels_filename, 'r', encoding='utf-8-sig') as fh:
            reader = csv.reader(fh)
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
    ax.text(sbx, sby + 50*length, str(length) + ' km', transform=tmc,
            horizontalalignment='center', verticalalignment='bottom', size=8)


def generate_weight_bins(weights, n_steps=9, width_step=0.01, interpolation='linear'):
    """Given a list of weight values, generate <n_steps> bins with a width
    value to use for plotting e.g. weighted network flow maps.
    """
    min_weight = min(weights)
    max_weight = max(weights)

    width_by_range = OrderedDict()

    if interpolation == 'linear':
        mins = np.linspace(min_weight, max_weight, n_steps)
    elif interpolation == 'log':
        mins = np.geomspace(min_weight, max_weight, n_steps)
    else:
        raise ValueError('Interpolation must be log or linear')
    maxs = list(mins)
    maxs.append(max_weight*10)
    maxs = maxs[1:]

    assert len(maxs) == len(mins)

    if interpolation == 'log':
        scale = np.geomspace(1, len(mins),len(mins))
    else:
        scale = np.linspace(1,len(mins),len(mins))


    for i, (min_, max_) in enumerate(zip(mins, maxs)):
        width_by_range[(min_, max_)] = scale[i] * width_step

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

def gdf_geom_clip(gdf_in, clip_geom):
    """Filter a dataframe to contain only features within a clipping geometry

    Parameters
    ---------
    gdf_in
        geopandas dataframe to be clipped in
    province_geom
        shapely geometry of province for what we do the calculation

    Returns
    -------
    filtered dataframe
    """
    return gdf_in.loc[gdf_in['geometry'].apply(lambda x: x.within(clip_geom))].reset_index(drop=True)

def get_nearest_node(x, sindex_input_nodes, input_nodes, id_column):
    """Get nearest node in a dataframe

    Parameters
    ----------
    x
        row of dataframe
    sindex_nodes
        spatial index of dataframe of nodes in the network
    nodes
        dataframe of nodes in the network
    id_column
        name of column of id of closest node

    Returns
    -------
    Nearest node to geometry of row
    """
    return input_nodes.loc[list(sindex_input_nodes.nearest(x.bounds[:2]))][id_column].values[0]


def get_nearest_node_within_region(x, input_nodes, id_column, region_id):
    select_nodes = input_nodes.loc[input_nodes[region_id] == x[region_id]]
    # print (input_nodes)
    if len(select_nodes.index) > 0:
        select_nodes = select_nodes.reset_index()
        sindex_input_nodes = select_nodes.sindex
        return select_nodes.loc[list(sindex_input_nodes.nearest(x.geometry.bounds[:2]))][id_column].values[0]
    else:
        return ''

def extract_nodes_within_gdf(x, input_nodes, column_name):
    return input_nodes.loc[list(input_nodes.geometry.within(x.geometry))][column_name].values[0]

def count_points_in_polygon(x, points_sindex):
    """Count points in a polygon

    Parameters
    ----------
    x
        row of dataframe
    points_sindex
        spatial index of dataframe with points in the region to consider

    Returns
    -------
    Number of points in polygon
    """
    return len(list(points_sindex.intersection(x.bounds)))

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
    return gdf.loc[list(gdf_sindex.intersection(row.geometry.bounds[:2]))][column_name].values[0]

def extract_gdf_values_containing_nodes(x, sindex_input_gdf, input_gdf, column_name):
    a = input_gdf.loc[list(input_gdf.geometry.contains(x.geometry))]
    if len(a.index) > 0:
        return a[column_name].values[0]
    else:
        return get_nearest_node(x.geometry, sindex_input_gdf, input_gdf, column_name)

def assign_value_in_area_proportions(poly_1_gpd, poly_2_gpd, poly_attribute):
    poly_1_sindex = poly_1_gpd.sindex
    for p_2_index, polys_2 in poly_2_gpd.iterrows():
        poly2_attr = 0
        intersected_polys = poly_1_gpd.iloc[list(
            poly_1_sindex.intersection(polys_2.geometry.bounds))]
        for p_1_index, polys_1 in intersected_polys.iterrows():
            if (polys_2['geometry'].intersects(polys_1['geometry']) is True) and (polys_1.geometry.is_valid is True) and (polys_2.geometry.is_valid is True):
                poly2_attr += polys_1[poly_attribute]*polys_2['geometry'].intersection(
                    polys_1['geometry']).area/polys_1['geometry'].area

        poly_2_gpd.loc[p_2_index, poly_attribute] = poly2_attr

    return poly_2_gpd


def assign_value_in_area_proportions_within_common_region(poly_1_gpd, poly_2_gpd, poly_attribute, common_region_id):
    poly_1_sindex = poly_1_gpd.sindex
    for p_2_index, polys_2 in poly_2_gpd.iterrows():
        poly2_attr = 0
        poly2_id = polys_2[common_region_id]
        intersected_polys = poly_1_gpd.iloc[list(
            poly_1_sindex.intersection(polys_2.geometry.bounds))]
        for p_1_index, polys_1 in intersected_polys.iterrows():
            if (polys_1[common_region_id] == poly2_id) and (polys_2['geometry'].intersects(polys_1['geometry']) is True) and (polys_1.geometry.is_valid is True) and (polys_2.geometry.is_valid is True):
                poly2_attr += polys_1[poly_attribute]*polys_2['geometry'].intersection(
                    polys_1['geometry']).area/polys_1['geometry'].area

        poly_2_gpd.loc[p_2_index, poly_attribute] = poly2_attr

    return poly_2_gpd

def voronoi_finite_polygons_2d(vor, radius=None):
    """Reconstruct infinite voronoi regions in a 2D diagram to finite regions.

    Source: https://stackoverflow.com/questions/36063533/clipping-a-voronoi-diagram-python

    Parameters
    ----------
    vor : Voronoi
        Input diagram
    radius : float, optional
        Distance to 'points at infinity'

    Returns
    -------
    regions : list of tuples
        Indices of vertices in each revised Voronoi regions.
    vertices : list of tuples
        Coordinates for revised Voronoi vertices. Same as coordinates
        of input vertices, with 'points at infinity' appended to the
        end
    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()*2

    # Construct a map containing all ridges for a given point
    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Reconstruct infinite regions
    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]

        if all(v >= 0 for v in vertices):
            # finite region
            new_regions.append(vertices)
            continue

        # reconstruct a non-finite region
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                # finite ridge: already in the region
                continue

            # Compute the missing endpoint of an infinite ridge

            t = vor.points[p2] - vor.points[p1]  # tangent
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])  # normal

            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        # sort region counterclockwise
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        # finish
        new_regions.append(new_region.tolist())

    return new_regions, np.asarray(new_vertices)
