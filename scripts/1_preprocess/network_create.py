"""
Get a shapefile and convert it into a network
@author: Raghav Pant
Date: June 21, 2018

Python code to convert a point and line dataset into a node and edge network structure
The code:
1. Inputs in point and line shapefiles,
2. Writes them to a PostGreSQL/PostGIS database,
3. Matches the points and lines to each other,
4. Creates new lines by snapping existing lines to the points,
5. Eliminates multiple points with same locations to create a single commom point for intersecting lines,
6. Writes in the attributes to the original shapefile to the new node and edge tables,
7. Outputs the results as new shapefiles
"""
import configparser
import copy
import csv
import glob
import os
import sys
import subprocess as sp

import fiona
import fiona.crs
import networkx as nx
import osgeo.ogr as ogr
import psycopg2

from oia.utils import load_config
import oia.dbutils as db

def open_connection_psycopg2():
	# ========================================
	# Create the database connection
	# 1. Loads the configurations file
	# 2. Creates a psycopg2 connection
	# ========================================
	conf = load_config()

	connection = psycopg2.connect(**conf['database'])

	return connection

def to_edges(l):
	"""
	treat `l` as a Graph and returns it's edges
	to_edges(['a','b','c','d']) -> [(a,b), (b,c),(c,d)]
	"""
	it = iter(l)
	last = next(it)

	for current in it:
		yield last, current
		last = current

def to_graph(l):
	# ==================================================================
	# Take a list of lists of nodes and convert them in networkx graph
	#
	# Inputs are:
	# l - list of lists of nodes
	#
	# Outputs are:
	# G - networkx graph with nodes and edges
	# ===================================================================
	G = nx.Graph()
	for part in l:
		# each sublist is a bunch of nodes
		G.add_nodes_from(part)
		# it also implies a number of edges:
		G.add_edges_from(to_edges(part))
	return G

def extract_points(gm):
	# ========================================================
	# Extract x,y-points from a geometry using Gdal functions
	#
	# Inputs are:
	# gm - Geometry, which is a list of points
	#
	# Outputs are:
	# x_pts - List of x-coordinates of the points
	# y_pts - List of y-coordinates of the points
	# =========================================================

	x_pts = []
	y_pts = []
	for k in range(0, gm.GetPointCount()):
		pt = gm.GetPoint(k)
		x_pts.append(pt[0])
		y_pts.append(pt[1])

	return x_pts, y_pts


def get_geom_points(gtext):
	# ===========================================================================
	# Extract the x,y-coordinates from a line geometry text using Gdal functions
	# The line geometry is either a mulitlinestring or a linestring
	#
	# Inputs are:
	# gtext - the WKT geometry
	#
	# Outputs are:
	# x_list - List of the x-coordinates of the geometry
	# y_list - List of the y-coordinates of the geometry
	# ===========================================================================
	x_list = []
	y_list = []
	gtype = ogr.CreateGeometryFromWkt(gtext).GetGeometryName()
	if gtype == 'MULTILINESTRING':
		geom = ogr.CreateGeometryFromWkt(gtext)
		for tg in range(0, geom.GetGeometryCount()):
			gm = geom.GetGeometryRef(tg)
			gname = gm.GetGeometryName()
			x_p, y_p = extract_points(gm)
			x_list.append(x_p)
			y_list.append(y_p)
	elif gtype == 'LINESTRING':
		gm = ogr.CreateGeometryFromWkt(gtext)
		x_p, y_p = extract_points(gm)
		x_list.append(x_p)
		y_list.append(y_p)

	return x_list,y_list

def vector_details(file_path):
	# ==============================================================
	# Read a vector shapefile with fiona and get its vector details
	#
	# Inputs are:
	# file_path - The path of the vector shapefile
	#
	# Outputs are:
	# geometry_type - The type of geometries in the shapefile
	# crs - The projection of the geometries in the shapefile
	# ==============================================================
	try:
		with fiona.open(file_path, 'r') as source:
			geometry_type = source.schema['geometry']
			crs = fiona.crs.to_string(source.crs)
		return geometry_type, crs
	except Exception as ex:
		print("INFO: fiona read failure (likely not a vector file)")
		raise ex


def write_shapefiles_to_database(input_shape_file_path,shape_encoding):
	# =================================================================================
	# Go to the folder with the point and line shapefiles
	# Get the projection of the shapefile and write it to the database
	# The shapefile geometry is reprojected to EPSG = 4326
	# IMPORTANT:
	# The folder should contain only ONE line shapefile to work
	# There should be NO MORE THAN ONE point shapefile in the folder
	# It is understood that the point and line shapefiles are part of the same network
	#
	# Inputs are:
	# input_shape_file_path - The file path where the input shapefiles are stored
	#
	# Outputs are:
	# node_fname - point table written to the database
	# edge_fname - line table written to the database
	#
	# The point and line table are written to the database with:
	# gid - Column name for the unique ID attribute
	# geom - Column name of the geom attribute
	# =================================================================================

	conf = load_config()
	node_fname = ''
	edge_fname = ''
	node_geom_type = ''
	edge_geom_type = ''
	for file_ in os.listdir(input_shape_file_path):
		if file_.endswith(".shp"):
			fpath = os.path.join(input_shape_file_path, file_)
			geom_type, cr = vector_details(fpath)

			fname = file_.split(".")
			fname = fname[0].lower().strip()

			if geom_type.lower().strip() in ('point','multipoint'):
				node_fname = fname
				node_geom_type = geom_type.lower().strip()
			elif geom_type.lower().strip() in ('linestring','multilinestring'):
				edge_fname = fname
				edge_geom_type = 'multilinestring'

			cr_split = cr.split(':')
			fr_srid = [c for c in cr_split if c.isdigit() is True]
			if fr_srid:
				fr_srid = fr_srid[0]
			elif 'wgs84' in cr.lower().strip():
				fr_srid = '4326'

			command = "shp2pgsql -I -s {0}:4326 -d -W '{1}' -g geom \"{2}\" \"{3}\" | psql -U {4} -d {5} -h {6} -p {7}".format(
				fr_srid,
				shape_encoding,
				fpath,
				fname,
				conf['database']['user'],
				conf['database']['database'],
				conf['database']['host'],
				conf['database']['port']
			)
			print ("Running,", command)
			returncode = sp.call(command, shell=True)
			if returncode != 0:
				print("Command failed with", returncode)
				exit(returncode)


	return node_fname, edge_fname, node_geom_type, edge_geom_type

def convert_multipoint_to_singlepoint(point_table,point_epsg):
	conn = open_connection_psycopg2()
	with conn.cursor() as cur:
		sql_query = '''ALTER TABLE {0}
	    			ALTER COLUMN geom TYPE geometry(Point,{1}) USING ST_GeometryN(geom, 1)
					'''.format(point_table,point_epsg)

		cur.execute(sql_query)
		conn.commit()

	conn.close()


def merge_common_integer_ids_from_network(node_table,node_id,node_geom,node_dist,node_attributes):
	# ===============================================================================================
	# Find all nodes, assigned to the edges, which are located within a small distance to each other
	# It is assumed that these nodes are the same and duplicate each other
	# So they are removed from the node and edge tables
	#
	# The inputs are:
	# node_table - Name of the node table
	# node_id - Name of the node ID column
	# node_geom - Name of the node geometry column
	# node_dist - The distance threshold below which it is assumed nodes are the same
	#
	# Outputs are:
	# Updated edge table where the duplicating from_node and to_node ID's are replaced with common nodes
	# Updated node table where the duplicating nodes are deleted
	# ================================================================================================


	conn = open_connection_psycopg2()

	node_s_pairs = []
	with conn.cursor() as cur:
		if node_dist > 0:
			sql_query = '''SELECT A.{0}, B.{1}
						from {2} as A, {3} as B
						where ST_DWithin(A.{4}::geography,B.{5}::geography, {6})
						and A.{7} <> B.{8}
						'''.format(node_id,node_id,node_table,node_table,node_geom,node_geom,node_dist,node_id,node_id)
		else:
			sql_query = '''SELECT A.{0}, B.{1}
						from {2} as A, {3} as B
						where A.{4} = B.{5}
						and A.{6} <> B.{7}
						'''.format(node_id,node_id,node_table,node_table,node_geom,node_geom,node_id,node_id)

		cur.execute(sql_query)
		for row in cur:
			a_n = row[0]
			b_n = row[1]
			if ([a_n,b_n] not in node_s_pairs) and ([b_n,a_n] not in node_s_pairs):
				node_s_pairs.append([a_n,b_n])

		net = to_graph(node_s_pairs)
		out = nx.connected_components(net)

		for i in out:
			nodes = sorted(i)
			del_nodes = nodes[1:] + [0]

			for attributes in node_attributes:
				attributes_vals = []
				sql_query = '''SELECT A.{0}, B.{1}
							from {2} as A, {3} as B
							where A.{4} = {5}
							and B.{6} in {7}
							'''.format(attributes,attributes,node_table,node_table,node_id,nodes[0],node_id,tuple(del_nodes))

				cur.execute(sql_query)
				for row in cur:
					attributes_vals.append(row[0])
					attributes_vals.append(row[1])

				attributes_vals = list(set(attributes_vals))
				if len(attributes_vals) > 1:
					attributes_vals = '/'.join(attributes_vals)
				else:
					attributes_vals = attributes_vals[0]

				if isinstance(attributes_vals,int) or isinstance(attributes_vals,float):
					sql_query = '''UPDATE {0} SET {1} = {2} WHERE {3} = {4}
								'''.format(node_table,attributes,attributes_vals,node_id,nodes[0])
				else:
					sql_query = '''UPDATE {0} SET {1} = '{2}' WHERE {3} = {4}
								'''.format(node_table,attributes,attributes_vals,node_id,nodes[0])

				cur.execute(sql_query)
				conn.commit()

			sql_delete = '''DELETE FROM {0}
						WHERE {1} IN {2}
						'''.format(node_table,node_id,tuple(del_nodes))
			cur.execute(sql_delete)
			conn.commit()

	conn.close()

def merge_common_string_ids_from_network(node_table,node_id,node_geom,node_dist,node_attributes):
	# ===============================================================================================
	# Find all nodes, assigned to the edges, which are located within a small distance to each other
	# It is assumed that these nodes are the same and duplicate each other
	# So they are removed from the node and edge tables
	#
	# The inputs are:
	# node_table - Name of the node table
	# node_id - Name of the node ID column
	# node_geom - Name of the node geometry column
	# node_dist - The distance threshold below which it is assumed nodes are the same
	#
	# Outputs are:
	# Updated edge table where the duplicating from_node and to_node ID's are replaced with common nodes
	# Updated node table where the duplicating nodes are deleted
	# ================================================================================================


	conn = open_connection_psycopg2()

	node_s_pairs = []
	with conn.cursor() as cur:
		if node_dist > 0:
			sql_query = '''SELECT A.{0}, B.{1}
						from {2} as A, {3} as B
						where ST_DWithin(A.{4}::geography,B.{5}::geography, {6})
						and A.{7} <> B.{8}
						'''.format(node_id,node_id,node_table,node_table,node_geom,node_geom,node_dist,node_id,node_id)
		else:
			sql_query = '''SELECT A.{0}, B.{1}
						from {2} as A, {3} as B
						where A.{4} = B.{5}
						and A.{6} <> B.{7}
						'''.format(node_id,node_id,node_table,node_table,node_geom,node_geom,node_id,node_id)

		cur.execute(sql_query)
		for row in cur:
			a_n = row[0]
			b_n = row[1]
			if ([a_n,b_n] not in node_s_pairs) and ([b_n,a_n] not in node_s_pairs):
				node_s_pairs.append([a_n,b_n])

		net = to_graph(node_s_pairs)
		out = nx.connected_components(net)

		for i in out:
			i_int = sorted([int(x.split('_')[1]) for x in list(i)])
			i_name = [x.split('_')[0] for x in list(i)][0]
			nodes = [i_name + '_' + str(x) for x in i_int]

			del_nodes = nodes[1:] + ['0']

			for attributes in node_attributes:
				attributes_vals = []
				sql_query = '''SELECT A.{0}, B.{1}
							from {2} as A, {3} as B
							where A.{4} = '{5}'
							and B.{6} in {7}
							'''.format(attributes,attributes,node_table,node_table,node_id,nodes[0],node_id,str(tuple(del_nodes)))

				cur.execute(sql_query)
				for row in cur:
					attributes_vals.append(row[0])
					attributes_vals.append(row[1])

				attributes_vals = list(set(attributes_vals))
				if len(attributes_vals) > 1:
					attributes_vals = '/'.join(attributes_vals)
				else:
					attributes_vals = attributes_vals[0]

				if isinstance(attributes_vals,int) or isinstance(attributes_vals,float):
					sql_query = '''UPDATE {0} SET {1} = {2} WHERE {3} = '{4}'
								'''.format(node_table,attributes,attributes_vals,node_id,nodes[0])
				else:
					sql_query = '''UPDATE {0} SET {1} = '{2}' WHERE {3} = '{4}'
								'''.format(node_table,attributes,attributes_vals,node_id,nodes[0])

				cur.execute(sql_query)
				conn.commit()

			sql_delete = '''DELETE FROM {0}
						WHERE {1} IN {2}
						'''.format(node_table,node_id,str(tuple(del_nodes)))
			cur.execute(sql_delete)
			conn.commit()

	conn.close()

def convert_multiline_to_linestring(multiline_table,multiline_id,multiline_geom,multiline_attribute,multiline_attribute_type):
	# ==============================================================================
	# Create new line geometry table converting the multilinestrings to linestrings
	# Carry on the multilinestring tables GID column into the linestring table
	#
	# Inputs are:
	# multiline_table - Name of the table with the multiline geometries
	# multiline_id - Name of the unique ID column in the multiline table
	# multiline_geom - Name of the geometry column in the multiline table
	#
	# Outputs are:
	# The singleline table which has the following attributes:
	# gid - unique ID column
	# lineid - the gid column of the multiline table
	# geom - linestring gepmetry projected to EPSG 4326
	# ==============================================================================

	conn = open_connection_psycopg2()
	singleline_table = multiline_table + '_linegeom'

	db.drop_postgres_table_psycopg2(singleline_table,conn)


	new_edge_id = 0
	with conn.cursor() as cur:
		if not multiline_attribute:
			sql_query = '''CREATE TABLE public.{0}
						(
						gid integer,
						lineid integer,
						geom geometry(LineString,4326)
						)
						'''.format(singleline_table)
			cur.execute(sql_query)
			conn.commit()

			sql_query = '''SELECT {0}, ST_AsText({1}) FROM {2}'''.format(multiline_id,multiline_geom,multiline_table)
			cur.execute(sql_query)
			for row in cur:
				link = int(row[0])
				gt = row[1]

				if gt is not None:
					g_x,g_y = get_geom_points(gt)

					for j in range(0,len(g_x)):
						line_create = ogr.Geometry(ogr.wkbLineString)
						for i in range(0,len(g_x[j])):
							pt_x = g_x[j][i]
							pt_y = g_y[j][i]
							line_create.AddPoint_2D(pt_x,pt_y)

						line_gtext = line_create.ExportToWkt()
						new_edge_id += 1
						sql_query = '''INSERT INTO {0} (gid,lineid,geom)
									VALUES ({1},{2},ST_GeomFromText('{3}',4326))
									'''.format(singleline_table,new_edge_id,link,str(line_gtext))

						cur.execute(sql_query)
						conn.commit()
		else:
			sql_query = '''CREATE TABLE public.{0}
						(
						gid integer,
						lineid integer,
						{1} {2},
						geom geometry(LineString,4326)
						)
						'''.format(singleline_table,multiline_attribute,multiline_attribute_type)
			cur.execute(sql_query)
			conn.commit()

			sql_query = '''SELECT {0},{1},ST_AsText({2}) FROM {3}'''.format(multiline_id,multiline_attribute,multiline_geom,multiline_table)
			cur.execute(sql_query)
			for row in cur:
				link = int(row[0])
				attr = row[1]
				gt = row[2]

				if gt is not None:
					g_x,g_y = get_geom_points(gt)

					for j in range(0,len(g_x)):
						line_create = ogr.Geometry(ogr.wkbLineString)
						for i in range(0,len(g_x[j])):
							pt_x = g_x[j][i]
							pt_y = g_y[j][i]
							line_create.AddPoint_2D(pt_x,pt_y)

						line_gtext = line_create.ExportToWkt()
						new_edge_id += 1
						if multiline_attribute_type == 'character varying':
							sql_query = '''INSERT INTO {0} (gid,lineid,{1},geom)
										VALUES ({2},{3},'{4}',ST_GeomFromText('{5}',4326))
										'''.format(singleline_table,multiline_attribute,new_edge_id,link,attr,str(line_gtext))
						else:
							sql_query = '''INSERT INTO {0} (gid,lineid,{1},geom)
										VALUES ({2},{3},{4},ST_GeomFromText('{5}',4326))
										'''.format(singleline_table,multiline_attribute,new_edge_id,link,attr,str(line_gtext))

						cur.execute(sql_query)
						conn.commit()

	conn.close()

	return singleline_table


def create_node_edge_tables_from_point_line_tables(point_table,line_table):
	# ==============================================================================
	# Given a point and line table, create node and edge tables for Graph structure
	# The minimum requirement is to have a linetable
	# The points table might be optional

	# Inputs are:
	# point_table - name of the point table
	# line_table - name of the line table
	#
	# The edge table contains the following attributes:
	# edge_id - unique ID given as a character varying
	# g_id - unique ID given as an integer
	# from_node - start point of the edge
	# to_node - end point of the edge
	# gid - ID column of the line table to be used later for attribute matching
	# geom - single line geometry of the edge

	# The node table contains the following attributes:
	# node_id - unique ID given as a character varying
	# gid - integer ID given to the node
	# geom - point geometry of the node
	# ==============================================================================

	conn = open_connection_psycopg2()

	edge_table = line_table + '_edges'

	if point_table == '':
		node_table = line_table + '_nodes'
	else:
		node_table = point_table + '_nodes'

	db.drop_postgres_table_psycopg2(edge_table,conn)
	db.drop_postgres_table_psycopg2(node_table,conn)

	with conn.cursor() as cur:
		sql_query = '''CREATE TABLE public.{0}
					(
					edge_id character varying(254),
					g_id integer,
					from_node character varying(254),
					to_node character varying(254),
					gid integer,
					geom geometry(LineString,4326)
					)
					'''.format(edge_table)
		cur.execute(sql_query)
		conn.commit()


		sql_query = '''CREATE TABLE public.{0}
					(
					node_id character varying(254),
					gid integer,
					geom geometry(Point,4326)
					)
					'''.format(node_table)
		cur.execute(sql_query)
		conn.commit()

	conn.close()

	return node_table, edge_table

def insert_values_to_node_edge_tables(sector,nodefid,nodetid,edgeid,node_table,edge_table,lineid,linegeom,startptgeom,endptgeom,connection):
	# ===================================================================================================
	# Create a node and edge tables from given information on line geometries and their start-end points
	#
	# Inputs are:
	# sector - The sector to which the node and egde tables belong: E.g. road, rail, ports, airports
	# nodeid - The serial ID for creating new node IDs in the node and edge table
	# edgeid - The serial ID for creating new edge IDs in the node table
	# node_table - The name of the node table into which values are inserted
	# edge_table - The name of the edge table into which values are inserted
	# lineid - The ID column value of the line geometry that is inherited by the edge table
	# linegeom - The line geometry inserted into the edge table
	# startptgeom - The point geometry on the line that forms a node in the node table
	# endptgeom - The point geometry on the line that forms a node in the node table
	# connection - The psycopg2 connection to the database server
	#
	# Outputs are:
	# node table into which the following values are inserted:
	# node_id - Unique string node ID, which will be used for reference
	# gid - Unique integer node ID
	# geom - Point geometry of the node
	#
	# edge table into which the following values are inserted:
	# edge_id - Unique string edge ID, which will be used for reference
	# from_node - Unique string node ID of the start point of the edge
	# to_node - Unique string node ID of the end point of the edge
	# gid - Integer edge ID inherited from the line table
	# geom - LineString geometry of the edge
	# ===================================================================================================

	eid = sector + 'e_' + str(edgeid)

	nfid = sector + 'n_' + str(nodefid)

	ntid = sector + 'n_' + str(nodetid)

	with connection.cursor() as curs:
		sql_insert = '''INSERT INTO public.{0}
					(edge_id,g_id,from_node,to_node,gid,geom)
					VALUES ('{1}',{2},'{3}','{4}',{5},
					ST_GeomFromText('{6}',4326))
					'''.format(edge_table,eid,edgeid,nfid,ntid,lineid,linegeom)
		curs.execute(sql_insert)
		connection.commit()


		sql_insert = '''INSERT INTO public.{0}
					(node_id,gid,geom)
					VALUES ('{1}',{2},
					ST_GeomFromText('{3}',4326))
					'''.format(node_table,nfid,nodefid,startptgeom)
		curs.execute(sql_insert)
		connection.commit()

		sql_insert = '''INSERT INTO public.{0}
					(node_id,gid,geom)
					VALUES ('{1}',{2},
					ST_GeomFromText('{3}',4326))
					'''.format(node_table,ntid,nodetid,endptgeom)
		curs.execute(sql_insert)
		connection.commit()

def insert_to_node_edge_tables_from_line_table(sector,node_table,edge_table,line_table,line_id,line_geom):
	# =====================================================================================================
	# Given only a line table, insert values to node and edge tables to infer Graph structure
	# The nodes created are the end points of the edge geometry
	# No duplicates are eliminates at this stage

	# Inputs are:
	# node_table - name of the node table where values are inserted
	# edge_table - name of the edge table where values are inserted
	# line_table - name of the line table
	# line_id - ID column name in the line table which will be used later for attribute matching
	# line_geom - geometry column name in the line table
	# sector - name of the sector to which the line table belongs. This is used for names nodes and edges
	#
	# The edge table contains the following attributes:
	# edge_id - unique ID given as a character varying
	# from_node - start point of the edge
	# to_node - end point of the edge
	# gid - ID column of the line table to be used later for attribute matching
	# geom - single line geometry of the edge

	# The node table contains the following attributes:
	# node_id - unique ID given as a character varying
	# gid - integer ID given to the node
	# geom - point geometry of the node
	# ======================================================================================================

	conn = open_connection_psycopg2()

	with conn.cursor() as cur:
		n_id = 0
		e_id = 0
		sql_query = '''SELECT {0},
					ST_AsText({1}),
					ST_AsText(ST_StartPoint({2})),
					ST_AsText(ST_EndPoint({3}))
					FROM public.{4}
					'''.format(line_id,line_geom,line_geom,line_geom,line_table)

		cur.execute(sql_query)
		for row in cur:
			lid = int(row[0])
			gt = row[1]
			st_pt = row[2]
			en_pt = row[3]
			e_id += 1
			n_id += 1
			nf_id = n_id
			n_id += 1
			nt_id = n_id

			insert_values_to_node_edge_tables(sector,nf_id,nt_id,e_id,node_table,edge_table,lid,gt,st_pt,en_pt,conn)

	conn.close()


def match_points_to_lines(point_table,line_table,point_id,line_id,point_attr,line_attr,point_geom,line_geom,dist_threshold,dist_proximity):
	# =================================================================================================================
	# Given a point and line table that are not matched to each other
	# We want to infer which points and lines could be matched based on shared attributes and geometric proximity
	# For example: This is done to infer where points such as rail stations are matched to particular lines or not
	#
	# The process of matching is done as following:
	# 1. Find the line closest to the point and estimate their distance d1
	# 2. Find if the line cloest to the point is also the one with the shared attribute
	# 3. If 2. above is True then the point ID and line ID ar confirmed matched
	# 4. Else if 2. above is False then estimate the distance d2 between the point and its line with shared attribute
	# 5. If d1 is too big then the point is too far from any line and it is a forced match
	# 	with either the closest line or the line with the shared attribute
	# 6. Else If d1 is below an acceptable threshold then it is a confirmed match
	# 	with either the closest line or the line with the shared attribute if |d2-d1| <= some threshold
	#
	# Inputs are:
	# point_table - Name of the points table
	# line_table - Name of the line table
	# point_id - Name of the unique ID column of the point table
	# line_id - Name of the unique ID column of the line table
	# point_attr - Name of the attribute column of the point table whose values are shared with the line table
	# line_attr - Name of the attribute column of the line table whose values are shared with the point table
	# point_geom - Name of the geometry column of the point table
	# line_geom - Name of the geometry column of the line table
	# dist_threshold - Minimum distance above which the point and line are considered too far
	# dist_proximity - Maximum distance below which the point is considered close to the line with matching attributes
	#
	# Outputs are:
	# point_line_list - A tuple list with values (point_id,line_id,closest distance between point and line)
	# ==================================================================================================================

	conn = open_connection_psycopg2()

	point_line_list = []
	with conn.cursor() as cur:
		if point_attr and line_attr:
			sql_query = '''SELECT A.{0},
						(select B.{1} from {2} as B order by st_distance(A.{3},B.{4}) asc limit 1),
						COALESCE((select B.{5} from {6} as B where A.{7} = B.{8} order by st_distance(A.{9},B.{10}) asc limit 1),-9999),
						(select ST_distance(A.{11}::geography,B.{12}::geography) from {13} as B order by st_distance(A.{14},B.{15}) asc limit 1),
						COALESCE((select ST_distance(A.{16}::geography,B.{17}::geography) from {18} as B where A.{19} = B.{20}
						order by st_distance(A.{21},B.{22}) asc limit 1),-9999)
						from {23} as A
						'''.format(point_id,line_id,line_table,point_geom,line_geom,
							line_id,line_table,point_attr,line_attr,point_geom,line_geom,
							point_geom,line_geom,line_table,point_geom,line_geom,
							point_geom,line_geom,line_table,point_attr,line_attr,point_geom,line_geom,
							point_table)

			cur.execute(sql_query)
			for row in cur:
				nid = row[0]
				clid = row[1]
				sbid_lid = row[2]
				cl_dist = row[3]
				sbid_dist = row[4]

				if clid != sbid_lid:
					if cl_dist > dist_threshold:
						if sbid_dist > 0:
							'''
							Match the point to the line with the same attribute
							'''
							point_line_list.append((nid,sbid_lid,sbid_dist))
						else:
							'''
							Match the point to the closest line
							'''
							point_line_list.append((nid,clid,cl_dist))
					else:
						if abs(sbid_dist - cl_dist) < dist_proximity:
							'''
							Match the point to the line with the same attribute
							'''
							point_line_list.append((nid,sbid_lid,sbid_dist))
						else:
							'''
							Match the point to the closest line
							'''
							point_line_list.append((nid,clid,cl_dist))
				else:
					'''
					Match the point to the line with the same attribute
					'''
					point_line_list.append((nid,sbid_lid,sbid_dist))

		else:
			sql_query = '''SELECT A.{0},
						(select B.{1} from {2} as B order by st_distance(A.{3},B.{4}) asc limit 1),
						(select ST_distance(A.{5}::geography,B.{6}::geography) from {7} as B order by st_distance(A.{8},B.{9}) asc limit 1)
						from {10} as A
						'''.format(point_id,line_id,line_table,point_geom,line_geom,
							point_geom,line_geom,
							line_table,point_geom,line_geom,
							point_table)

			cur.execute(sql_query)
			for row in cur:
				nid = row[0]
				clid = row[1]
				cl_dist = row[2]
				point_line_list.append((nid,clid,cl_dist))


	conn.close()

	return point_line_list


def insert_to_node_edge_tables_from_given_points_lines(point_table,line_table,point_id,line_id,line_attr,point_geom,line_geom,point_line_list,sector,dist_threshold,node_table,edge_table):
	# ==========================================================================================================================
	# Given a point and a line table where points are already matched to the lines,
	# create and insert values to node and edge tables to infer Graph structure
	# The matching points intersect the lines somewhere in between so the lines need to be broken into segments between points
	# Each segement will have a start point and an end point which creates the network topology
	# No duplicates are eliminated at this stage
	#
	# Inputs are:
	# point_table - Name of the point table
	# line_table - Name of the line table
	# point_id - Name of ID column of the point table
	# line_id - Name of ID column of the line table
	# point_geom - Name of the geometry column of the point table
	# line_geom - Name of the geometry column of the line table
	# point_line_list - List of tuple with values (point_id, line_id, closest distance between point and line)
	# dist_threshold - The distance above which the point and line a considered too far
	# node_table - Name of the node table into which the values are inserted
	# edge_table - Name of the edge table into which the values are inserted
	#
	# Outputs are:
	# The edge table which contains the following attributes:
	# edge_id - unique ID given as a character varying
	# from_node - start point of the edge
	# to_node - end point of the edge
	# gid - ID column of the line table to be used later for attribute matching
	# geom - single line geometry of the edge
	#
	# The node table which contains the following attributes:
	# node_id - unique ID given as a character varying
	# gid - integer ID given to the node
	# geom - point geometry of the node
	# ======================================================================================================

	conn = open_connection_psycopg2()

	with conn.cursor() as cur:
		e_id = 0
		sql_query = '''SELECT max({0}) FROM {1}
					'''.format(point_id,point_table)
		cur.execute(sql_query)
		for row in cur:
			 n_id = row[0] + 1

		print ('max point',n_id)
		sql_query = '''SELECT {0}, {1} FROM {2}
					'''.format(line_id,line_attr,line_table)
		cur.execute(sql_query)
		for row in cur:
			lc = row[0]
			la = row[1]
			nlist = [(n,m) for (n,l,m) in point_line_list if l == lc]
			# print (lc,nlist)
			if len(nlist) > 0:
				'''
				Find the points which have some line matches in close proximity
				'''
				nl = [n for (n,m) in nlist if m < dist_threshold]
				if len(nl) > 0:
					nl = nl + [0]
					pt_tup_list = []
					sql_query = '''SELECT A.{0},
								ST_AsText(ST_ClosestPoint(B.{1},A.{2})),
								ST_Line_Locate_Point(B.{3},ST_ClosestPoint(B.{4},A.{5})),
								ST_AsText(ST_StartPoint(B.{6})), ST_AsText(ST_EndPoint(B.{7})),
								ST_Distance(ST_ClosestPoint(B.{8},A.{9}),ST_StartPoint(B.{10})),
								ST_Distance(ST_ClosestPoint(B.{11},A.{12}),ST_EndPoint(B.{13}))
								FROM {14} AS A,
								{15} AS B
								WHERE A.{16} IN {17}
								AND B.{18} = {19}
								'''.format(point_id,line_geom,point_geom,line_geom,line_geom,point_geom,
									line_geom,line_geom,line_geom,point_geom,line_geom,line_geom,point_geom,
									line_geom,point_table,line_table,point_id,str(tuple(nl)),line_id,lc)
					cur.execute(sql_query)
					r_layer = cur.fetchall()
					for r in r_layer:
						nid = r[0]
						pt_geom = r[1]
						frac = r[2]
						st_pt = r[3]
						en_pt = r[4]
						st_pt_dist = r[5]
						en_pt_dist = r[6]

						pt_tup_list.append((nid,pt_geom,st_pt_dist,en_pt_dist,frac))


					# print (pt_tup_list)
					if len(pt_tup_list) > 0:
						pt_id_sorted = [p for (p,w,x,y,z) in sorted(pt_tup_list, key=lambda pair: pair[-1])]
						pt_geom_sorted = [w for (p,w,x,y,z) in sorted(pt_tup_list, key=lambda pair: pair[-1])]
						pt_dist_st_sorted = [x for (p,w,x,y,z) in sorted(pt_tup_list, key=lambda pair: pair[-1])]
						pt_dist_en_sorted = [y for (p,w,x,y,z) in sorted(pt_tup_list, key=lambda pair: pair[-1])]
						pt_frac_sorted = [z for (p,w,x,y,z) in sorted(pt_tup_list, key=lambda pair: pair[-1])]

						if pt_dist_st_sorted[0] < 1e-10:
							pt_frac_sorted[0] = 0
							pt_geom_sorted[0] = st_pt

						if pt_dist_en_sorted[-1] < 1e-10:
							pt_frac_sorted[-1] = 1
							pt_geom_sorted[-1] = en_pt

						if min(pt_frac_sorted) > 0:
							pt_frac_sorted = [0] + pt_frac_sorted
							n_id += 1
							pt_id_sorted = [n_id] + pt_id_sorted
							pt_geom_sorted = [st_pt] + pt_geom_sorted

						if max(pt_frac_sorted) < 1:
							pt_frac_sorted = pt_frac_sorted + [1]
							n_id += 1
							pt_id_sorted = pt_id_sorted + [n_id]
							pt_geom_sorted = pt_geom_sorted + [en_pt]

						# print (pt_frac_sorted)
						# print (pt_id_sorted)
						for p in range(len(pt_frac_sorted)-1):
							e_id += 1
							eid = sector + 'e_' + str(e_id)
							pt_st_frac = pt_frac_sorted[p]
							pt_en_frac = pt_frac_sorted[p+1]

							nf_id = pt_id_sorted[p]
							nt_id = pt_id_sorted[p+1]

							nfid = sector + 'n_' + str(nf_id)
							ntid = sector + 'n_' + str(nt_id)

							sql_insert = '''INSERT INTO public.{0}
										(edge_id,g_id,from_node,to_node,gid,geom)
										VALUES ('{1}',{2},'{3}','{4}',{5},
										ST_GeomFromText((SELECT ST_AsText(ST_Line_Substring({6},{7},{8}))
										FROM {9} WHERE {10} = {11}),4326)
										)'''.format(edge_table,eid,e_id,nfid,ntid,la,line_geom,pt_st_frac,pt_en_frac,line_table,line_id,lc)
							cur.execute(sql_insert)
							conn.commit()
							# print ('Line from node matchs',e_id,nf_id,nt_id)


						for p in range(len(pt_id_sorted)):
							nid = sector + 'n_' + str(pt_id_sorted[p])
							pt = pt_geom_sorted[p]
							sql_insert = '''INSERT INTO public.{0}
										(node_id,gid,geom)
										VALUES ('{1}',{2},ST_GeomFromText('{3}',4326))
										'''.format(node_table,nid,pt_id_sorted[p],pt)
							cur.execute(sql_insert)
							conn.commit()

				'''
				Find the points which have some line matches but not in close proximity
				'''
				nl = [n for (n,m) in nlist if m >= dist_threshold]
				# print (nl)
				if len(nl) > 0:
					sql_query = '''SELECT ST_AsText({0}),
								ST_AsText(ST_StartPoint({1})),
								ST_AsText(ST_EndPoint({2}))
								FROM {3}
								WHERE {4} = {5}
								'''.format(line_geom,line_geom,line_geom,line_table,line_id,lc)
					cur.execute(sql_query)
					r_layer = cur.fetchall()
					for r in r_layer:
						gt = r[0]
						st_pt = r[1]
						en_pt = r[2]

						e_id += 1
						n_id += 1
						nf_id = n_id
						n_id += 1
						nt_id = n_id

						insert_values_to_node_edge_tables(sector,nf_id,nt_id,e_id,node_table,edge_table,la,gt,st_pt,en_pt,conn)

					nl = nl + [0]
					sql_query = '''SELECT A.{0},
								ST_AsText(A.{1}),
								ST_AsText(ST_ClosestPoint(B.{2},A.{3})),
								ST_AsText(ST_MakeLine(A.{4},ST_ClosestPoint(B.{5},A.{6})))
								FROM {7} AS A,
								{8} AS B
								WHERE A.{9} IN {10}
								AND B.{11} = {12}
								'''.format(point_id,point_geom,line_geom,point_geom,point_geom,line_geom,
									point_geom,point_table,line_table,point_id,str(tuple(nl)),line_id,lc)
					# print (sql_query)
					cur.execute(sql_query)
					r_layer = cur.fetchall()
					for r in r_layer:
						nid = r[0]
						pt_geom = r[1]
						cl_pt_geom = r[2]
						gt = r[3]
						e_id += 1
						eid = sector + 'e_' + str(e_id)

						n_id += 1

						nfid = sector + 'n_' + str(nid)
						ntid = sector + 'n_' + str(n_id)

						sql_query = '''INSERT INTO {0} (edge_id,g_id,from_node,to_node,gid,geom)
									VALUES ('{1}',{2},'{3}','{4}',{5},ST_GeomFromText('{6}',4326))
									'''.format(edge_table,eid,e_id,nfid,ntid,la,gt)
						# print (sql_query)
						cur.execute(sql_query)
						conn.commit()

						sql_query = '''INSERT INTO public.{0}
									(node_id,gid,geom)
									VALUES ('{1}',{2},
									ST_GeomFromText('{3}',4326))
									'''.format(node_table,nfid,nid,pt_geom)
						cur.execute(sql_query)
						conn.commit()

						sql_query = '''INSERT INTO public.{0}
									(node_id,gid,geom)
									VALUES ('{1}',{2},
									ST_GeomFromText('{3}',4326))
									'''.format(node_table,ntid,n_id,cl_pt_geom)
						cur.execute(sql_query)
						conn.commit()
						# print ('Joining point to lines',e_id,nid,n_id)


			else:
				sql_query = '''SELECT ST_AsText({0}),
							ST_AsText(ST_StartPoint({1})),
							ST_AsText(ST_EndPoint({2}))
							FROM {3}
							WHERE {4} = {5}
							'''.format(line_geom,line_geom,line_geom,line_table,line_id,lc)
				cur.execute(sql_query)
				r_layer = cur.fetchall()
				for r in r_layer:
					gt = r[0]
					st_pt = r[1]
					en_pt = r[2]

					e_id += 1
					n_id += 1
					nf_id = n_id
					n_id += 1
					nt_id = n_id

					insert_values_to_node_edge_tables(sector,nf_id,nt_id,e_id,node_table,edge_table,la,gt,st_pt,en_pt,conn)
					# print('nodes from end points',e_id,nf_id,nt_id)


	conn.close()

def eliminate_common_nodes_from_network(node_table,edge_table,node_id,node_geom,node_dist):
	# ===============================================================================================
	# Find all nodes, assigned to the edges, which are located within a small distance to each other
	# It is assumed that these nodes are the same and duplicate each other
	# So they are removed from the node and edge tables
	#
	# The inputs are:
	# node_table - Name of the node table
	# edge_table - Name of the edge table
	# node_id - Name of the node ID column
	# node_geom - Name of the node geometry column
	# node_dist - The distance threshold below which it is assumed nodes are the same
	#
	# Outputs are:
	# Updated edge table where the duplicating from_node and to_node ID's are replaced with common nodes
	# Updated node table where the duplicating nodes are deleted
	# ================================================================================================


	conn = open_connection_psycopg2()

	with conn.cursor() as cur:
		if node_dist > 0:
			node_s_pairs = []
			sql_query = '''SELECT A.{0}, B.{1}
						from {2} as A, {3} as B
						where ST_Distance(A.{4}::geography,B.{5}::geography) <= {6}
						and A.{7} <> B.{8}
						'''.format(node_id,node_id,node_table,node_table,node_geom,node_geom,node_dist,node_id,node_id)

			cur.execute(sql_query)
			for row in cur:
				a_n = row[0]
				b_n = row[1]
				if ([a_n,b_n] not in node_s_pairs) and ([b_n,a_n] not in node_s_pairs):
					node_s_pairs.append([a_n,b_n])

			net = to_graph(node_s_pairs)
			out = nx.connected_components(net)
			del net,node_s_pairs
		else:
			sql_query = '''SELECT array_agg({0}), count(*)
						FROM {1}
						GROUP BY {2}
						HAVING count({3}) > 1;
						'''.format(node_id,node_table,node_geom,node_id)

			cur.execute(sql_query)
			out = []
			for row in cur:
				out.append(list(row[0]))
			out = to_graph(out)
			out = nx.connected_components(out)

		del_nodes_list = []
		for i in out:
			i_int = sorted([int(x.split('_')[1]) for x in list(i)])
			i_name = [x.split('_')[0] for x in list(i)][0]
			nodes = [i_name + '_' + str(x) for x in i_int]

			del_nodes = nodes[1:] + ['0']
			del_nodes_list += nodes[1:]

			sql_update = '''UPDATE {0} SET from_node = '{1}'
						WHERE from_node in {2}
						'''.format(edge_table,nodes[0],str(tuple(del_nodes)))

			cur.execute(sql_update)
			conn.commit()

			sql_update = '''UPDATE {0} SET to_node = '{1}'
						WHERE to_node in {2}
						'''.format(edge_table,nodes[0],str(tuple(del_nodes)))
			cur.execute(sql_update)
			conn.commit()

		del_nodes_list = list(set(del_nodes_list))
		sql_delete = '''DELETE FROM {0}
					WHERE node_id IN {1}
					'''.format(node_table,str(tuple(del_nodes_list)))
		cur.execute(sql_delete)
		conn.commit()

	conn.close()

def bisect_lines_by_nodes(node_table,edge_table,node_id,edge_id,edge_int_id,from_node,to_node,edge_attr,node_geom,edge_geom,node_edge_dist):
	# ==============================================================================================================
	# Given a node and edge table where some of the nodes are in close proximity to their unassigned edges
	# It is assumed that such close proximity nodes will intersect the edges and divide them in smaller segments
	# The purpose here is to fill in gaps in a network where we can infer that some junctions might not be joined
	# So we try to join them at the intersecting node
	#
	# Inputs are:
	# node_table - Name of the node table
	# edge_table - Name of the edge table
	# node_id - Name of the string ID column of the node table
	# edge_id - Name of the string ID column of the edge table
	# edge_int_id - Name of the integer ID column of the edge table
	# from_node - Name of the from node ID column of the edge table
	# to_node - Name of the to node ID column of the edge table
	# edge_attr - Name of the attribute ID column of the edge which will be used later to match values
	# node_geom - Name of the node Point geometry column
	# edge_geom - Name of the edge Line geometry column
	# node_edge_dist - Distance threshold between the node and edge geometries to infer whether nodes bisect edges
	#
	# Outputs are:
	# Updated edge table where new edges are added which are derived from the old edges being bisected by nodes
	# Old edges are deleted to remove overlapping geometries
	# ==============================================================================================================

	conn = open_connection_psycopg2()

	cl_edges = []
	nodes_edges = []

	with conn.cursor() as cur:
		sql_query = "SELECT max({0}),max({1}) FROM {2}".format(edge_id,edge_int_id,edge_table)
		cur.execute(sql_query)
		for row in cur:
			sector = row[0].split('_')
			sector = sector[0]
			e_id = int(row[1])


		sql_query = '''SELECT A.{0},
					B.{1} from {2} as A, {3} as B where B.{4} != A.{5}
					and B.{6} != A.{7} and st_distance(A.{8}::geography,B.{9}::geography) <= {10}
					'''.format(node_id,edge_id,node_table,edge_table,from_node,node_id,to_node,node_id,node_geom,edge_geom,node_edge_dist)
		cur.execute(sql_query)
		for row in cur:
			a_n = row[0]
			b_n = row[1]

			nodes_edges.append((a_n,b_n))
			if b_n not in cl_edges:
				cl_edges.append(b_n)

		# print (cl_edges)
		for lc in cl_edges:
			'''
			Find the nodes which have some edge matches
			'''
			nl = [n for (n,m) in nodes_edges if m == lc]
			if len(nl) > 0:
				nl = nl + ['0']
				pt_tup_list = []
				sql_query = '''SELECT A.{0},
							ST_Line_Locate_Point(B.{1},ST_ClosestPoint(B.{2},A.{3})),
							B.{4}, B.{5}, B.{6}
							FROM public.{7} AS A,
							public.{8} AS B
							WHERE A.{9} IN {10}
							AND B.{11} = '{12}'
							'''.format(node_id,edge_geom,edge_geom,node_geom,from_node,
								to_node,edge_attr,node_table,edge_table,node_id,str(tuple(nl)),edge_id,lc)

				cur.execute(sql_query)
				for row in cur:
					n = row[0]
					frac = row[1]
					st_pt = row[2]
					en_pt = row[3]
					elr = row[4]

					pt_tup_list.append((n,frac))

				if len(pt_tup_list) > 0:
					pt_id_sorted = [x for (x,y) in sorted(pt_tup_list, key=lambda pair: pair[1])]
					pt_frac_sorted = [y for (x,y) in sorted(pt_tup_list, key=lambda pair: pair[1])]

					# print (pt_frac_sorted,min(pt_frac_sorted))
					if min(pt_frac_sorted) > 1e-5:
						pt_frac_sorted = [0] + pt_frac_sorted
						pt_id_sorted = [st_pt] + pt_id_sorted

					if max(pt_frac_sorted) < 1:
						pt_frac_sorted = pt_frac_sorted + [1]
						pt_id_sorted = pt_id_sorted + [en_pt]

					# print (pt_frac_sorted)

					for p in range(len(pt_frac_sorted)-1):
						e_id += 1
						pt_st_frac = pt_frac_sorted[p]
						pt_en_frac = pt_frac_sorted[p+1]

						if pt_st_frac < pt_en_frac:
							nf_id = pt_id_sorted[p]
							nt_id = pt_id_sorted[p+1]

							eid = sector + '_' + str(e_id)

							sql_insert = '''INSERT INTO public.{0}
										(edge_id,g_id,from_node,to_node,gid,geom)
										VALUES ('{1}',{2},'{3}','{4}',{5},
										ST_GeomFromText((SELECT ST_AsText(ST_Line_Substring({6},{7},{8}))
										FROM {9} WHERE {10} = '{11}'),4326)
										)'''.format(edge_table,eid,e_id,nf_id,nt_id,elr,edge_geom,pt_st_frac,pt_en_frac,edge_table,edge_id,lc)
							# print (sql_insert)
							cur.execute(sql_insert)
							conn.commit()



				sql_delete = '''DELETE FROM public.{0}
							WHERE {1} = '{2}'
							'''.format(edge_table,edge_id,lc)
				cur.execute(sql_delete)
				conn.commit()

	conn.close()

def add_all_columns_from_one_table_to_another(original_table,new_table,common_id,skip_id_list):
	# =========================================================================
	# Copy attribute columns from one table to another.
	# Excluding the geometry and ID columns which should already be there
	#
	# Inputs are:
	# original_table - The table whose attributes we want to copy
	# new_table - The table into which we want to add the attributes
	# common_id - The common ID column shared by both tables
	# geom_id - The geometry column shared by both tables
	#
	# Outputs are:
	# The new table inherits all column attributes and values of the old table
	# ==========================================================================

	conn = open_connection_psycopg2()

	col_names = []
	col_types = []
	with conn.cursor() as cur:
		sql_query = "SELECT column_name,data_type FROM information_schema.columns WHERE table_name = '{0}'".format(original_table)
		cur.execute(sql_query)
		for row in cur:
			if row[0] not in skip_id_list:
				col_names.append(row[0])
				col_types.append(row[1])


	db.add_columns_to_table_psycopg2(new_table, original_table, col_names, col_types,common_id,conn)
	conn.close()

def export_pgsql_to_shapefiles(output_shape_file_path,database_table):
	# =======================================================================
	# Export a database table to a shapefile
	#
	# Inputs are:
	# output_shape_file_path - The file path where the shapefile is exported
	# database_table - The table in the database which is exported
	#
	# Outputs are:
	# shapefile output of the postgis table
	# =======================================================================
	conf = load_config()

	shp_file_name = os.path.join(output_shape_file_path,database_table + '.shp')
	command = '''pgsql2shp -d -f {0} -h {1} -u {2} -P {3} {4} public.{5}
			'''.format(shp_file_name,conf['database']['host'],conf['database']['user'],
				conf['database']['password'],conf['database']['database'],database_table)
	sp.call(command, shell=True)
