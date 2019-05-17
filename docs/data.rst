=======================
Processed Data Assembly
=======================
.. Important::
	- This section describes processed datasets that are used as inputs in Analysis and Results steps of the Argentina Transport Risk Analysis (ATRA)
	- The formats and attributes created in these datasets form the essential inputs for implementing the rest of the ATRA model
	- To implement the ATRA without any changes in existing codes, all data described here should be created and stored exactly as indicated below

Networks
--------
1. All finalised networks data are stored:
	- In the file path - ``/data/network/``
	- As csv file with post-processed network nodes and edges
	- As Shapefiles with post-processed network nodes and edges

2. All nodes have the following attributes:
	- ``node_id`` - String Node ID
	- ``geometry`` - Point geometry of node with projection ESPG:4326
	- Several other atttributes depending upon the specific transport sector

3. Attributes only present in bridge nodes:
	- ``bridge_id`` - String Bridge ID

4. All edges have the following attributes:
	- ``edge_id`` - String edge ID
	- ``from_node`` - String node ID that should be present in node_id column
	- ``to_node`` - String node ID that should be present in node_id column
	- ``geometry`` - LineString geometry of edge with projection ESPG:4326
	- ``length`` - Float estimated length in kilometers of edge
	- ``min_speed`` - Float estimated minimum speed in km/hr on edge
	- ``max_speed`` - Float estimated maximum speed in km/hr on edge
	- ``min_time`` - Float estimated minimum time of travel in hours on edge
	- ``max_time`` - Float estimated maximum time of travel in hours on edge
	- ``min_gcost`` - Float estimated minimum generalized cost in USD/ton on edge
	- ``max_gcost`` - Float estimated maximum generalized cost in USD/ton on edge
	- Several other atttributes depending upon the specific transport sector 

4. Attributes only present in province and national roads edges:
	- ``road_name`` - String name or number of road
	- ``surface`` - String value for surface
	- ``road_type`` - String value of either national, province or rural
	- ``road_cond`` - String value: paved or unpaved
	- ``width`` - Float width of edge in meters
	- ``min_time_cost`` - Float estimated minimum cost of time in USD on edge
	- ``max_time_cost`` - Float estimated maximum cost of time in USD on edge
	- ``min_tariff_cost`` - Float estimated minimum tariff cost in USD on edge
	- ``max_tariff_cost`` - Float estimated maximum tariff cost in USD on edge
	- ``tmda_count`` - Integer number of daily vehicle counts on edge

OD matrices
-----------
1. All finalised OD matrices are stored:
	- In the path - ``/data/OD_data/``
	- As csv file with names ``{mode}_nodes_daily_ods.csv``
	- As csv file with names ``{mode}_province_annual_ods.csv``
	- As Excel sheets with combined Province level annual OD matrices

The essential attributes in these OD matrices are listed below. See the data for all attributes

2. All node-level daily OD matrices contain mode-wise and total OD flows and should have attributes:
	- ``origin_id`` - String node IDs of origin nodes
	- ``destination_id`` - String node IDs of destination nodes
	- ``origin_province`` - String names of origin Provinces
	- ``destination_province`` - String names of destination Provinces
	- ``min_total_tons`` - Float values of minimum daily tonnages between OD nodes
	- ``max_total_tons`` - Float values of maximum daily tonnages between OD nodes
	- ``commodity_names`` - Float values of daily min-max tonnages of commodities/industries between OD nodes: here based on OD data
	- If min-max values cannot be estimated then there is a ``total_tons`` column - for roads only

3. All aggregated province-level OD matrices contain mode-wise and total OD flows and should have attributes:
	- ``origin_province`` - String names of origin Provinces
	- ``destination_province`` - String names of destination Provinces
	- ``min_total_tons`` - Float values of minimum daily tonnages between OD Provinces
	- ``max_total_tons`` - Float values of maximum daily tonnages between OD Provinces
	- ``commodity_names`` - Float values of daily min-max tonnages of commodities/industries between OD Provinces
	- If min-max values cannot be estimated then there is a ``total_tons`` column - for roads only


Hazards
-------
1. All hazard datasets are stored:
	- In sub-folders in the path - ``/data/flood_data/FATHOM``
	- As GeoTiff files
	- See ``/data/flood_data/hazard_data_folder_data_info.xlsx`` for details of all hazard files

2. Single-band GeoTiff hazard raster files should have attributes:
	- values - between 0 and 1000
	- raster grid geometry
	- projection systems: Default assumed = EPSG:4326


Administrative Areas with Statistics
------------------------------------
1. Argentina boundary datasets are stored:
	- In the path - ``/incoming_data/2/departamento``
	- In the path - ``/incoming_data/2/provincia``
	- As Shapefiles

2. Global boundary dataset for map plotting are stored:
	- In the path - ``/data/boundaries/``
	- As Shapefiles

3. Census boundary data are stored:
	- In the path - ``/incoming_data/2/radios censales/``
	- As Shapefiles

The essential attributes in the Argentina boundary datasets are listed below. See the data for all attributes

4. All Argentina Department boundary datasets should have the attributes:
	- ``name`` - String names Spanish - attribute name changed to ``department_name``
	- ``OBJECTID`` - Integer IDs - attribute name changed to ``department_id``
	- ``geometry`` - Polygon geometries of boundary with projection ESPG:4326

5. All Argentina Province boundary datasets should have attributes:
	- ``nombre`` - String names Spanish - attribute name changed to ``province_name``
	- ``OBJECTID`` - Integer IDs - attribute name changed to ``province_id``
	- ``geometry`` - Polygon geometries of boundary with projection ESPG:4326

6. All global boundary datasets should have attributes:
	- ``name`` - String names of boundaries in English
	- ``geometry`` - Polygon geometry of boundary with projection ESPG:4326

6. The census datasets should have attributes:
	- ``poblacion`` - Float value of population
	- ``geometry`` - Polygon geometry of boundary with projection ESPG:4326


Macroeconomic Data
------------------
1. For the macroeconomic analysis we use the national IO table for Argentina:
	- In the file in path - ``data/economic_IO_tables/input/IO_ARGENTINA.xlsx``
	- In the file in path - ``data/economic_IO_tables/input/MRIO_ARGENTINA_FULL.xlsx``


Adaptation Options
------------------
1. All adaptation options input datasets are stored:
	- In the file - ``/data/adaptation_options/ROCKS - Database - ARNG (Version 2.3) Feb2018.xlsx``
	- We use the sheet ``Resultados Consolidados`` for our analysis
