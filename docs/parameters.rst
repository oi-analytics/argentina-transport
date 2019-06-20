==================================
Required data inputs and paramters
==================================
.. Important::
	- This section describes the required data inputs and parameters for the Argentina Transport Risk Analysis (ATRA)
	- To implement the ATRA all data described here should be created with the data properties and column names as described below
	- If these data properties and column names are not provided in the data then the Python scripts will give run-time errors

Spatial data requirements
-------------------------
1. All spatial data inputs must:
	- Be projected to a valid coordinate system. Spatial data with no projection system will give errors 
	- Have valid geometries. Null or Invalid geometries will give errors  

.. Note::
	- The assumed projection system used in the model is EPSG:4326
	- If the users change any spatial data they have to create new data with a valid projection system 

Topological network requirements
--------------------------------
1. A topological network is defined as a graph composed of nodes and edges  

2. All finalised networks data are created and stored:
	- In the file path - ``/data/network/``
	- As csv file with post-processed network nodes and edges
	- As Shapefiles with post-processed network nodes and edges
	- The created networks are: ``road``, ``rail``,``port``,``air``
	- ``bridge`` files are also created but they are not networks, as explained below  

.. Note::
	The names and properties of the attributes listed below are the essential network parameters for the whole model analysis. If the users wish to replace or change these datasets then they must retain the same names of columns with same types of values as given in the original data. It is recommended that changes in parameter values should be made in the csv files, while the Shapefiles are mainly used for associating the geometries of the features. While we have provided the Shapefiles with parameter values as well, the model uses the Shapeflies mainly for performing geometry operations.

	For example if a new road edge is added to the road network, then all its properties should be added to the ``road_edges.csv`` file, while in the ``road_edges.shp`` file the ``edge_id`` and valid ``geometry`` should be added.

3. All nodes have the following attributes:
	- ``node_id`` - String Node ID
	- ``geometry`` - Point geometry of node with projection ESPG:4326
	- Several other atttributes depending upon the specific transport sector

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
	- ``min_gcost`` - Float estimated minimum generalized cost in USD/ton on edge (not present in road edge files)
	- ``max_gcost`` - Float estimated maximum generalized cost in USD/ton on edge (not present in road edge files)
	- Several other atttributes depending upon the specific transport sector 

5. Attributes only present in roads edges:
	- ``road_name`` - String name or number of road
	- ``surface`` - String value for surface material of the road
	- ``road_type`` - String value of either national, province or rural
	- ``width`` - Float width of edge in meters
	- ``min_time_cost`` - Float estimated minimum cost of time in USD on edge
	- ``max_time_cost`` - Float estimated maximum cost of time in USD on edge
	- ``min_tariff_cost`` - Float estimated minimum tariff cost in USD on edge
	- ``max_tariff_cost`` - Float estimated maximum tariff cost in USD on edge
	- ``tmda_count`` - Integer number of daily vehicle counts on edge

6. National-roads bridges GIS data are also created as nodes containing:
	- ``bridge_id`` - String bridge ID
	- ``edge_id`` - String edge ID matching ``edge_id`` of national-roads edges intersecting with bridges
	- ``width`` - Float with of bridge in meters
	- ``length`` - Float length of bridge in meters
	- ``geometry`` - Point geometry of node with projection ESPG:4326
	- Several other atttributes depending upon the specific bridge input data

7. National-roads bridges GIS data are also created as edges containing:
	- ``bridge_id`` - String bridge ID
	- ``length`` - Float length of bridge in meters
	- ``geometry`` - LineString geometry of bridge with projection ESPG:4326

.. Note::
	We assume that networks are provided as topologically correct connected graphs: each edge
	is a single LineString (may be straight line or more complex line), but must have exactly
	two endpoints, which are labelled as ``from_node`` and ``to_node`` (the values of these
	attributes must correspond to the ``node_id`` of a node).

	Wherever two edges meet, we assume that there is a shared node, matching each of the intersecting edge endpoints. For example, at a t-junction there will be three edges meeting
	at one node.

	Due to gaps in geometries and connectivity in the raw datasets several dummy nodes and edges have been created in the node and edges join points and lines. For example there are more nodes in the rail network than stations in Argentina, and similarly in the port network. The road network contains severral edges with ``road_type = 0`` which represent a dummy edge created to join two roads.

	The bridge datasets are not networks because they do not have a topology. Bridge nodes are matched to the road network to later match road flow and failure results with failed bridges. For example we estimate the failure consequence of a road edge of the national route 12 first, and if we know there is a bridge on this road that is also flooded then we assign the failure consequence to the bridge as well. Bridge edges are created to intersect with flood outlines to estimate the length of flooding of bridges.  


OD matrices requirements
------------------------
1. All finalised OD matrices are stored:
	- In the path - ``/data/OD_data/``
	- As csv file with names ``{mode}_nodes_daily_ods.csv`` where ``mode = {road, rail, port}``
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


Network Transport Costs
-----------------------
1. Road costs are stored:
	- In the path - ``/incoming_data/5/road_costs/Matrices OD FFCC/``
	- As Excel files
	- The Vehicle Operating Costs are in the file ``Costos de Operación de Vehículos.xlsx``
	- We use the sheet ``Camión Pesado`` for costs
	- The tariff costs are in the file ``tariff_costs.xlsx``

2. Rail costs are stored:
	- In the Excel file path - ``incoming_data/5/rail_od_matrices/rail_costs.xlsx``
	- We use the sheet ``route_costs``

3. Port costs are stored:
	- In the Excel file path - ``incoming_data/5/Puertos/port_costs.xlsx``	

              
National Road speeds and widths
-------------------------------
1. Data on select national roads widths are stored:
	- In the Excel file path - ``incoming_data/5/DNV_data/Tramos por Rutas.xls``
	- We use the sheet ``Hoja1``

2. Data on select national roads speeds are stored:
	- In the Excel file path - ``incoming_data/5/DNV_data/TMDA y Clasificación 2016.xlsx`` 
	- We use the sheet ``Clasificación 2016``