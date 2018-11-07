"""Utility functions for working with psycopg2 postgres/postgis databases
"""

def drop_postgres_table_psycopg2(table_name,connection):
	with connection.cursor() as cursor:
		sql_query = "drop table if exists {0}".format(table_name)
		cursor.execute(sql_query)
		connection.commit()

def nodes_polygons_intersections_psycopg2(intersection_table,node_table,polygon_table,node_attr,polygon_attr,node_geom,polygon_geom,connection):
	attr_string = ''
	for n in node_attr:
		attr_string += 'A.{0}, '.format(n)

	for p in polygon_attr[:-1]:
		attr_string += 'B.{0}, '.format(p)

	attr_string += 'B.{0}'.format(polygon_attr[-1])

	with connection.cursor() as cursor:
		sql_query = '''create table {0} as select {1}
				from {2} as A, {3} as B
				where st_intersects(A.{4},B.{5}) is True
				'''.format(intersection_table,attr_string,node_table,polygon_table,node_geom,polygon_geom)

		cursor.execute(sql_query)
		connection.commit()

def nodes_polygons_nearest_psycopg2(intersection_table,node_table,polygon_table,node_attr,polygon_attr,node_geom,polygon_geom,connection):
	attr_string = ''
	for n in node_attr:
		attr_string += 'A.{0}, '.format(n)

	for p in polygon_attr[:-1]:
		attr_string += '''(select B.{0} from {1} as B order by st_distance(A.{2},B.{3}) asc limit 1),
					'''.format(p,polygon_table,node_geom,polygon_geom)

	attr_string += '''(select B.{0} from {1} as B order by st_distance(A.{2},B.{3}) asc limit 1)
				'''.format(polygon_attr[-1],polygon_table,node_geom,polygon_geom)


	with connection.cursor() as cursor:
		sql_query = '''create table {0} as select {1} from {2} as A'''.format(intersection_table,attr_string,node_table)

		cursor.execute(sql_query)
		connection.commit()

def nodes_polygons_within_psycopg2(intersection_table,node_table,polygon_table,node_attr,polygon_attr,node_geom,polygon_geom,connection):
	attr_string = ''
	for n in node_attr:
		attr_string += 'A.{0}, '.format(n)

	for p in polygon_attr[:-1]:
		attr_string += '''B.{0},
					'''.format(p)

	attr_string += '''B.{0} from {1} as A, {2} as B where st_within(A.{2},B.{3})
				'''.format(polygon_attr[-1],node_table,polygon_table,node_geom,polygon_geom)

	with connection.cursor() as cursor:
		sql_query = '''create table {0} as select {1}'''.format(intersection_table,attr_string)

		cursor.execute(sql_query)
		connection.commit()

def nodes_polygons_within_nearest_psycopg2(intersection_table,node_table,polygon_table,node_attr,node_id_attr,polygon_attr,node_geom,polygon_geom,connection):
	attr_string = ''
	for n in node_attr:
		attr_string += 'A.{0}, '.format(n)

	for p in polygon_attr[:-1]:
		attr_string += '''B.{0},
					'''.format(p)

	attr_string += '''B.{0} from {1} as A, {2} as B where st_within(A.{3},B.{4})
				'''.format(polygon_attr[-1],node_table,polygon_table,node_geom,polygon_geom)

	bttr_string = ''
	for n in node_attr:
		bttr_string += 'C.{0}, '.format(n)

	for p in polygon_attr[:-1]:
		bttr_string += '''(select D.{0} from {1} as D order by st_distance(C.{2},D.{3}) asc limit 1),
					'''.format(p,polygon_table,node_geom,polygon_geom)

	bttr_string += '''(select D.{0} from {1} as D order by st_distance(C.{2},D.{3}) asc limit 1)
				from {4} as C where C.{5} not in
				(select X.{6} from {7} as X, {8} as Y where st_within(X.{9},Y.{10}))
				'''.format(polygon_attr[-1],polygon_table,node_geom,polygon_geom,node_table,node_id_attr,node_id_attr,node_table,polygon_table,node_geom,polygon_geom)


	with connection.cursor() as cursor:
		sql_query = '''create table {0} as select {1} union select {2}'''.format(intersection_table,attr_string,bttr_string)

		# print (sql_query)
		cursor.execute(sql_query)
		connection.commit()

def nodes_voronoi_polygons_aggregations(intersection_table,node_table,polygon_table,node_attr,polygon_attr,node_geom,polygon_geom,polygon_aggr,connection):
	with connection.cursor() as cursor:
		sql_query = '''create table {0} as select A.{1},
				sum((B.{2}/st_area(B.{3}))*st_area(st_intersection(st_buffer(A.{4},0),st_buffer(B.{5},0)))) as {6}
				from {7} as A, {8} as B
				where st_intersects(A.{9},B.{10}) is True group by A.{11}
				'''.format(intersection_table,node_attr,polygon_attr,polygon_geom,node_geom,polygon_geom,polygon_aggr,node_table,polygon_table,node_geom,polygon_geom,node_attr)

		cursor.execute(sql_query)
		connection.commit()

def nodes_polygons_aggregations(intersection_table,node_table,polygon_table,node_id_attr,polygon_id_attr,node_polygon_attr,polygon_node_attr,polygon_attr,node_geom,polygon_geom,connection):
	drop_postgres_table_psycopg2('intermediate_table',connection)
	with connection.cursor() as cursor:
		sql_query = '''CREATE TABLE intermediate_table AS SELECT DISTINCT ON (A.{0}) A.{1}, A.{2}, B.{3}
					FROM {4} As A, {5} As B
					WHERE A.{6} = B.{7}
					ORDER BY A.{8}, ST_Distance(A.geom, B.geom);
					'''.format(polygon_id_attr,polygon_id_attr,polygon_attr,node_id_attr,
						polygon_table,node_table,node_polygon_attr,polygon_node_attr,
						polygon_id_attr,polygon_geom,node_geom)

		cursor.execute(sql_query)
		connection.commit()

		sql_query = '''create table {0} as select {1}, sum({2}) as {3}
				from intermediate_table group by {4}
				'''.format(intersection_table,node_id_attr,polygon_attr,polygon_attr,node_id_attr)

		cursor.execute(sql_query)
		connection.commit()

	drop_postgres_table_psycopg2('intermediate_table',connection)

def add_zeros_columns_to_table_psycopg2(table_name, col_name_list,col_type_list, connection):
	for c in range(len(col_name_list)):
		with connection.cursor() as cursor:
			sql_query = "alter table {0} drop column if exists {1}".format(table_name,col_name_list[c])
			cursor.execute(sql_query)
			connection.commit()

			sql_query = "alter table {0} add column {1} {2}".format(table_name,col_name_list[c],col_type_list[c])
			cursor.execute(sql_query)
			connection.commit()

			sql_query = "update %s set %s = 0"%(table_name,col_name_list[c])
			cursor.execute(sql_query)
			connection.commit()


def add_columns_to_table_psycopg2(table_name, table_match, col_name_list,col_type_list, col_id,connection):
	for c in range(len(col_name_list)):
		with connection.cursor() as cursor:
			sql_query = "alter table {0} drop column if exists {1}".format(table_name,col_name_list[c])
			cursor.execute(sql_query)
			connection.commit()

			sql_query = "alter table {0} add column {1} {2}".format(table_name,col_name_list[c],col_type_list[c])
			cursor.execute(sql_query)
			connection.commit()

			sql_query = '''
						UPDATE {0} t2 SET {1} = t1.{2}
						FROM   {3} t1 WHERE  t2.{4} = t1.{5}
						'''.format(table_name,col_name_list[c],col_name_list[c],table_match,col_id,col_id)
			cursor.execute(sql_query)
			connection.commit()

def add_geometry_column_to_table_psycopg2(table_name, table_match, col_name_list,col_type_list, col_id_list,connection):
	for c in range(len(col_name_list)):
		with connection.cursor() as cursor:
			sql_query = "alter table {0} add column {1} {2}".format(table_name,col_name_list[c],col_type_list[c])
			cursor.execute(sql_query)
			connection.commit()

			sql_query = '''
						update {0} set {1} = (select {2} from {3} as A where {4}.{5} = A.{6})
						'''.format(table_name,col_name_list[c],col_name_list[c],table_match,table_name,col_id_list[c],col_id_list[c])
			cursor.execute(sql_query)
			connection.commit()


def get_node_edge_flows(pd_dataframe,node_dict,edge_dict):
	for index, row in pd_dataframe.iterrows():
		npath = ast.literal_eval(row[0])
		epath = ast.literal_eval(row[1])
		val = row[2]

		for node in npath:
			node_key = str(node)
			if node_key not in node_dict.keys():
				node_dict.update({str(node_key):val})
			else:
				node_dict[str(node_key)] += val

		for edge in epath:
			edge_key = str(edge)
			if edge_key not in edge_dict.keys():
				edge_dict.update({str(edge_key):val})
			else:
				edge_dict[str(edge_key)] += val

	return(node_dict,edge_dict)

def get_id_flows(id_dict):
	f_info = []
	for key,value in id_dict.items():
		n_id = key
		if n_id.isdigit():
			n_id = int(n_id)

		f_info.append((n_id,value))

	return (f_info)
