"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import pandas as pd
import geopandas as gpd
import numpy as np
import igraph as ig
import copy
import unidecode
from scipy.spatial import Voronoi
from oia.utils import *
import datetime
from tqdm import tqdm

def assign_node_weights_by_area_population_proximity(commune_path,nodes,commune_pop_col):
    """Assign weights to nodes based on their nearest commune populations

        - By finding the communes that intersect with the Voronoi extents of nodes

    Parameters
        - commune_path - Path of commune shapefile
        - nodes_in - Path of nodes shapefile
        - commune_pop_col - String name of column containing commune population values

    Outputs
        - nodes - Geopandas dataframe of nodes with new column called weight
    """

    # load provinces and get geometry of the right communes within the provinces
    tqdm.pandas()
    communes = gpd.read_file(commune_path,encoding='utf-8')
    communes = communes.to_crs({'init': 'epsg:4326'})
    sindex_communes = communes.sindex

    # create Voronoi polygons for the nodes
    xy_list = []
    for iter_, values in nodes.iterrows():
        xy = list(values.geometry.coords)
        xy_list += [list(xy[0])]

    vor = Voronoi(np.array(xy_list))
    regions, vertices = voronoi_finite_polygons_2d(vor)
    min_x = vor.min_bound[0] - 0.1
    max_x = vor.max_bound[0] + 0.1
    min_y = vor.min_bound[1] - 0.1
    max_y = vor.max_bound[1] + 0.1

    mins = np.tile((min_x, min_y), (vertices.shape[0], 1))
    bounded_vertices = np.max((vertices, mins), axis=0)
    maxs = np.tile((max_x, max_y), (vertices.shape[0], 1))
    bounded_vertices = np.min((bounded_vertices, maxs), axis=0)

    box = Polygon([[min_x, min_y], [min_x, max_y], [max_x, max_y], [max_x, min_y]])

    poly_list = []
    for region in regions:
        polygon = vertices[region]
        # Clipping polygon
        poly = Polygon(polygon)
        poly = poly.intersection(box)
        poly_list.append(poly)

    poly_index = list(np.arange(0, len(poly_list), 1))
    poly_df = pd.DataFrame(list(zip(poly_index, poly_list)),
                                   columns=['gid', 'geometry'])
    gdf_voronoi = gpd.GeoDataFrame(poly_df, crs='epsg:4326')
    gdf_voronoi['node_id'] = gdf_voronoi.progress_apply(
        lambda x: extract_nodes_within_gdf(x, nodes, 'node_id'), axis=1)

    gdf_voronoi[commune_pop_col] = 0
    gdf_voronoi = assign_value_in_area_proportions(communes, gdf_voronoi, commune_pop_col)

    gdf_voronoi.rename(columns={commune_pop_col: 'weight'}, inplace=True)
    gdf_pops = gdf_voronoi[['node_id', 'weight']]
    del gdf_voronoi, poly_list, poly_df

    nodes = pd.merge(nodes, gdf_pops, how='left', on=['node_id']).fillna(0)
    del gdf_pops, communes

    return nodes

def assign_industry_names(x,industries_df):
    return industries_df.loc[(x.commodity_group,x.commodity_subgroup),'high_level_industry']

def assign_industry_od_flows_to_nodes(national_ods_df,ind_cols,modes_df,modes,od_fracs,o_id_col,d_id_col):
    """Assign VITRANSS 2 OD flows to nodes

    Parameters
        - national_ods_df - List of lists of Pandas dataframes
        - ind_cols - List of strings of names of indsutry columns
        - modes_df - List of Geopnadas dataframes with nodes of each transport mode
        - modes - List of strings of names of transport modes
        - od_fracs - Pandas dataframe of Industry OD flows and modal splits
        - o_id_col - String name of Origin province ID column
        - d_id_col - String name of Destination province ID column

    Outputs
        national_ods_df - List of Lists of Pandas dataframes with columns:
            - origin - Origin node ID
            - o_region - Origin province name
            - destination - Destination node ID
            - d_region - Destination province ID
            - ind - Tonnage values for the named industry
    """
    for ind in ind_cols:
        national_ods_modes_df = []
        for m in range(len(modes_df)):
            nodes = modes_df[m]
            od_nodes_regions = list(zip(nodes['node_id'].values.tolist(), nodes['province_name'].values.tolist(
            ), nodes['od_id'].values.tolist(), nodes['weight'].values.tolist()))
            ind_mode = modes[m] + '_' + ind
            od_fracs[ind_mode] = od_fracs[modes[m]]*od_fracs[ind]

            od_fracs_ind = od_fracs[[o_id_col, d_id_col, ind_mode]]
            od_fracs_ind = od_fracs_ind[od_fracs_ind[ind_mode] > 0]
            od_flows = list(zip(od_fracs_ind[o_id_col].values.tolist(
            ), od_fracs_ind[d_id_col].values.tolist(), od_fracs_ind[ind_mode].values.tolist()))
            origins = list(set(od_fracs_ind[o_id_col].values.tolist()))
            destinations = list(set(od_fracs_ind[d_id_col].values.tolist()))

            # print (od_flows)
            od_list = []
            for o in origins:
                for d in destinations:
                    fval = [fl for (org, des, fl) in od_flows if org == o and des == d]
                    if len(fval) == 1 and fval[0] > 0:
                        o_matches = [(item[0], item[1], item[3])
                                     for item in od_nodes_regions if item[2] == o]
                        if len(o_matches) > 0:
                            for o_vals in o_matches:
                                o_val = 1.0*fval[0]*(1.0*o_vals[2])
                                o_node = o_vals[0]
                                o_region = o_vals[1]
                                d_matches = [(item[0], item[1], item[3])
                                             for item in od_nodes_regions if item[2] == d]
                                if len(d_matches) > 0:
                                    for d_vals in d_matches:
                                        od_val = 1.0*o_val*(1.0*d_vals[2])
                                        d_node = d_vals[0]
                                        d_region = d_vals[1]
                                        if od_val > 0 and o_node != d_node:
                                            od_list.append(
                                                (o_node, o_region, d_node, d_region, od_val))


            national_ods_modes_df.append(pd.DataFrame(
                od_list, columns=['origin', 'o_region', 'destination', 'd_region', ind]))
            del od_list, nodes

        national_ods_df.append(national_ods_modes_df)

    return national_ods_df

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    road_od_folder = os.path.join(incoming_data_path,'5','Matrices OD 2014- tablas')
    total_tons_sheet = 'Total Toneladas 2014'
    file_desc = [{'file_name':'07. Matrices Grupo Granos',
        'commodity_group':'Granos'
        },
        {'file_name':'08. Matrices Grupo Carnes',
        'commodity_group':'Carnes'
        },
        {'file_name':'09. Matrices Grupo Mineria',
        'commodity_group':'Mineria'
        },
        {'file_name':'10. Matrices Grupo Regionales',
        'commodity_group':'Regionales'
        },
        {'file_name':'11. Matrices Grupo Industrializados',
        'commodity_group':'Industrializados'
        },
        {'file_name':'12. Matrices Grupo Semiterminados',
        'commodity_group':'Semiterminados'
        },
        {'file_name':'13. Matriz Grupo Combustibles',
        'commodity_group':'Combustibles'
        },
    ]

    od_ids = ['origin_id','net_origin_name','net_origin_line','net_origin_province','net_origin_operator',
            'destination_id','net_destination_name','net_destination_line','net_destination_province','net_destination_operator',
            'net_speed','chosen_speed','net_path','net_distance']

    
    population_threshold = 1000
    '''Get industries
    '''
    print('* Reading industry dataframe')
    industries_df = pd.read_excel(os.path.join(data_path,'economic_IO_tables','commodity_classifications-hp.xlsx'),sheet_name='road',index_col=[0,1]).reset_index()
    industry_cols = list(set(industries_df['high_level_industry'].values.tolist()))
    industries_df = list(industries_df.itertuples(index=False))

    # load provinces and get geometry of the right province
    print('* Reading provinces dataframe')
    province_path = os.path.join(incoming_data_path,'2','provincia','Provincias.shp')
    provinces = gpd.read_file(province_path,encoding='utf-8')
    provinces = provinces.to_crs({'init': 'epsg:4326'})
    sindex_provinces = provinces.sindex
    
    '''Assign provinces to zones
    '''
    print('* Reading zones dataframe')
    zones_path = os.path.join(incoming_data_path,'5','Lineas de deseo OD- 2014','3.6.1.10.zonas','ZonasSHP.shp')
    zones = gpd.read_file(zones_path,encoding='utf-8')
    zones = zones.to_crs({'init': 'epsg:4326'})
    zones.columns = map(str.lower, zones.columns)
    zones.rename(columns={'data':'od_id'},inplace=True)
    sindex_zones = zones.sindex

    '''Assign provinces to roads
    '''
    print('* Reading nodes dataframe and adding provinces and zone ids')
    road_nodes_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_nodes_4326.shp')
    road_nodes = gpd.read_file(road_nodes_path,encoding='utf-8').fillna(0)
    road_nodes = road_nodes.to_crs({'init': 'epsg:4326'})
    road_nodes.columns = map(str.lower, road_nodes.columns)
    road_nodes.rename(columns={'id':'node_id'},inplace=True)
    road_nodes = road_nodes[(road_nodes['road_type'] == 'national')| (road_nodes['road_type'] == 'province')]
    # road_nodes = road_nodes[(road_nodes['road_type'] == 'national')]
    road_nodes['provincia'] = road_nodes.progress_apply(lambda x: extract_gdf_values_containing_nodes(
        x, sindex_provinces, provinces,'nombre'), axis=1)
    road_nodes['od_id'] = road_nodes.progress_apply(lambda x: extract_gdf_values_containing_nodes(
        x, sindex_zones, zones,'od_id'), axis=1)
    del provinces


    '''Assign populations to road nodes selectively
    '''
    print('* Adding weights to selective nodes')
    road_nodes = assign_node_weights_by_area_population_proximity(os.path.join(incoming_data_path,
        '3','radios censales','radioscensales.shp'),
        road_nodes,'poblacion')

    road_nodes_subset = road_nodes[road_nodes['weight'] > population_threshold]
    road_nodes_subset.drop('weight', axis=1, inplace=True)
    road_nodes_subset = assign_node_weights_by_area_population_proximity(os.path.join(incoming_data_path,
        '3','radios censales','radioscensales.shp'),
        road_nodes_subset,'poblacion')
    # road_nodes.to_csv('test0.csv',index=False)
    road_nodes_sums = road_nodes_subset.groupby(['od_id', 'node_id']).agg({'weight': 'sum'})
    road_nodes_frac = road_nodes_sums.groupby(level=0).apply(lambda x: x/float(x.sum()))
    road_nodes_frac = road_nodes_frac.reset_index(level=['od_id', 'node_id'])

    road_nodes.drop('weight', axis=1, inplace=True)
    road_nodes = pd.merge(road_nodes, road_nodes_frac[['node_id', 'weight']],
                         how='left', on=['node_id']).fillna(0)
    # road_nodes = road_nodes[['node_id','weight']]
    # road_nodes = pd.merge(road_nodes,road_nodes_subset,how='left', on=['node_id']).fillna(0)

    # road_nodes.to_csv('test.csv',index=False)
    del zones, road_nodes_subset,road_nodes_frac,road_nodes_sums
    road_nodes = list(road_nodes.itertuples(index=False))

    '''Get road edge network
    '''
    # print('* Reading edges, addiing attributes and creating graph')
    # road_edges_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_edges_4326.shp')
    # road_edges = gpd.read_file(road_edges_path,encoding='utf-8').fillna(0)
    # road_edges.columns = map(str.lower, road_edges.columns)
    # road_edges.rename(columns={'id':'edge_id','from_id':'from_node','to_id':'to_node'},inplace=True)
    # # get the right linelength
    # road_edges['length'] = road_edges.geometry.progress_apply(line_length)
    # road_edges = road_edges[['edge_id','length','from_node','to_node','tmda','geometry']]
    # road_edges = road_edges.reindex(list(road_edges.columns)[2:]+list(road_edges.columns)[:2], axis=1)
    # road_net = ig.Graph.TupleList(road_edges.itertuples(index=False), edge_attrs=list(road_edges.columns)[2:])

    
    od_output_excel = os.path.join(incoming_data_path,'road_ods','road_ods.xlsx')
    excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(incoming_data_path,'road_ods','province_ods.xlsx')
    province_excel_writer = pd.ExcelWriter(od_output_excel)

    print('* Creating OD assignments')
    od_vals = []
    od_vals_group_industry = {}
    for fd in file_desc:
        file_name = os.path.join(road_od_folder,'{}.xlsx'.format(fd['file_name']))
        road_od_dict = pd.read_excel(file_name,sheet_name=None,index_col=0,encoding='utf-8-sig')
        for name,sheet in road_od_dict.items():
            # print (sheet)
            if 'Varios 1' in name:
                commodity = 'Alpiste-Lenteja-Poroto-Mijo-Arveja-Otr.Leg'
            elif 'Varios 2' in name:
                commodity = 'Colza-Avena-Cartamo-Triticale'
            elif 'Varios 3' in name:
                commodity = 'Maní-Lino-Centeno-Garbanzo-Otros'
            else:
                commodity = name.replace('Toneladas 2014','').replace('Ton. 2014','').replace('2014','')

            if unidecode.unidecode(commodity.lower().strip()) in [unidecode.unidecode(x.commodity_subgroup.lower().strip()) for x in industries_df]:
                print ('commodity',commodity)
                industry_name = [x.high_level_industry for x in industries_df \
                                if unidecode.unidecode(x.commodity_group.lower().strip()) == unidecode.unidecode(fd['commodity_group'].lower().strip()) \
                                and unidecode.unidecode(x.commodity_subgroup.lower().strip()) == unidecode.unidecode(commodity.lower().strip())][0]
                for o_index in range(1,124):
                    for d_index in range(1,124): 
                        fval = sheet.loc[o_index,d_index]
                        if fval > 0:
                            o_matches = [(item.node_id, item.provincia,item.weight) 
                                        for item in road_nodes if item.od_id == o_index and item.weight > 0]
                            if len(o_matches) > 0:
                                for o_vals in o_matches:
                                    o_val = 1.0*fval*(1.0*o_vals[2])
                                    o_node = o_vals[0]
                                    o_region = o_vals[1]
                                    d_matches = [(item.node_id, item.provincia,item.weight) 
                                                for item in road_nodes if item.od_id == d_index and item.weight > 0]
                                    if len(d_matches) > 0:
                                        for d_vals in d_matches:
                                            d_node = d_vals[0]
                                            if d_node != o_node:
                                                od_val = 1.0*o_val*(1.0*d_vals[2])
                                                d_region = d_vals[1]
                                                if od_val > 0:
                                                    od_vals.append((o_node,d_node,o_index,d_index,o_region,d_region,commodity,fd['commodity_group'],industry_name,od_val))
                                                    if '{}-{}'.format(o_node,d_node) not in od_vals_group_industry.keys():
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)] = {}
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['origin_zone_id'] = o_index 
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['destination_zone_id'] = d_index 
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['origin_province'] = o_region 
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['destination_province'] = d_region
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)][fd['commodity_group']] = od_val
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['total_tons'] = od_val
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)][industry_name] = od_val
                                                    else:
                                                        od_vals_group_industry['{}-{}'.format(o_node,d_node)]['total_tons'] += od_val 
                                                        if fd['commodity_group'] not in od_vals_group_industry['{}-{}'.format(o_node,d_node)].keys():
                                                            od_vals_group_industry['{}-{}'.format(o_node,d_node)][fd['commodity_group'] ] = od_val
                                                        else:
                                                             od_vals_group_industry['{}-{}'.format(o_node,d_node)][fd['commodity_group'] ] += od_val
                                                        if industry_name not in od_vals_group_industry['{}-{}'.format(o_node,d_node)].keys():
                                                            od_vals_group_industry['{}-{}'.format(o_node,d_node)][industry_name] = od_val
                                                        else:
                                                            od_vals_group_industry['{}-{}'.format(o_node,d_node)][industry_name] += od_val




                            print ('* Done with OD assignmenet between zones {} and {}'.format(o_index,d_index))

    
    print ('Number of unique OD pairs by commodity',len(od_vals))
    print ('Number of unique OD pairs',len(od_vals_group_industry.keys()))
    od_list = []
    for key,values in od_vals_group_industry.items():
        od_list.append({**{'origin_id':key.split('-')[0],'destination_id':key.split('-')[1]},**values})
    od_df = pd.DataFrame(od_list).fillna(0)
    
    del od_list, od_vals_group_industry

    province_ods = od_df[['origin_province','destination_province']+industry_cols + ['total_tons']]
    province_ods = province_ods.groupby(['origin_province','destination_province'])[industry_cols + ['total_tons']].sum().reset_index() 
    province_ods.to_csv(os.path.join(data_path,'OD_data','road_province_annual_ods.csv'),index=False,encoding='utf-8-sig') 
    province_ods.to_excel(province_excel_writer,'industries',index=False,encoding='utf-8-sig')
    province_excel_writer.save()

    od_df[industry_cols + ['total_tons']] = 1.0*od_df[industry_cols + ['total_tons']]/365.0
    od_df = od_df[od_df['total_tons'] > 0.5]
    print ('Number of unique OD pairs',len(od_df.index))
    # od_df.to_csv(os.path.join(incoming_data_path,'road_ods','road_ods.csv'),index=False,encoding='utf-8-sig')
    od_df.to_csv(os.path.join(data_path,'OD_data','road_nodes_daily_ods.csv'),index=False,encoding='utf-8-sig')

    od_df = pd.DataFrame(od_vals,columns=['origin_id','destination_id','origin_zone_id','destination_zone_id',
                                'origin_province','destination_province','commodity_subgroup','commodity_group','industry_name','tons'])
    province_ods = od_df.groupby(['origin_province','destination_province','industry_name'])['tons'].sum().reset_index()
    province_ods.to_excel(province_excel_writer,'road',index=False,encoding='utf-8-sig')
    province_excel_writer.save()


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
