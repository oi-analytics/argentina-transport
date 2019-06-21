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
    - The created networks are: ``road, rail, port, air``
    - ``bridge`` files are also created but they are not networks, as explained below  

.. Note::
    The names and properties of the attributes listed below are the essential network parameters for the whole model analysis. If the users wish to replace or change these datasets then they must retain the same names of columns with same types of values as given in the original data. 

    It is recommended that changes in parameter values should be made in the csv files, while the Shapefiles are mainly used for associating the geometries of the features. While we have provided the Shapefiles with parameter values as well, the model uses the Shapeflies mainly for performing geometry operations.

    For example if a new road edge is added to the road network, then all its properties should be added to the ``road_edges.csv`` file, while in the ``road_edges.shp`` file the ``edge_id`` and valid ``geometry`` should be added.

    The essential attributes in these networks are listed below. See the data for all attributes and try to recreate your data with similar column names and attribute values.

    Several of these parameters and their values are created from ``incoming_data`` which is explained in the section `Preparing data for the model <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/predata.html>`_ 

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

    The bridge datasets are not networks because they do not have a topology. Bridge nodes are matched to the road network to later match road flow and failure results with failed bridges. For example, we estimate the failure consequence of a road edge of the National Route 12 first, and if we know there is a bridge on this road that is also flooded then we assign the failure consequence to the bridge as well. Bridge edges are created to intersect with flood outlines to estimate the length of flooding of bridges.  


OD matrices requirements
------------------------
1. All finalised OD matrices are stored:
    - In the path - ``/data/OD_data/``
    - As csv file with names ``{mode}_nodes_daily_ods.csv`` where ``mode = {road, rail, port}``
    - As csv file with names ``{mode}_province_annual_ods.csv``
    - As Excel sheets with combined Province level annual OD matrices

2. All node-level daily OD matrices contain mode-wise and total OD flows and should have attributes:
    - ``origin_id`` - String node IDs of origin nodes. Value should be present in the ``node_id`` column of the sectors network file
    - ``destination_id`` - String node IDs of destination nodes. Value should be present in the ``node_id`` column of the sectors network file
    - ``origin_province`` - String names of origin Provinces
    - ``destination_province`` - String names of destination Provinces
    - ``min_total_tons`` - Float values of minimum daily tonnages between OD nodes
    - ``max_total_tons`` - Float values of maximum daily tonnages between OD nodes
    - Float values of daily min-max tonnages of commodities/industries between OD nodes: here based on OD data provided for each sector
    - If min-max values cannot be estimated then there is a ``total_tons`` column - for roads only

3. All aggregated province-level OD matrices contain mode-wise and total OD flows and should have attributes:
    - ``origin_province`` - String names of origin Provinces
    - ``destination_province`` - String names of destination Provinces
    - ``min_total_tons`` - Float values of minimum daily tonnages between OD Provinces
    - ``max_total_tons`` - Float values of maximum daily tonnages between OD Provinces
    - Float values of daily min-max tonnages of commodities/industries between OD Provinces: here based on OD data provided for each sector
    - If min-max values cannot be estimated then there is a ``total_tons`` column - for roads only

.. Note::
    The OD columns names and their attributes listed aobve are essential for the flow and failure model analysis. While the names of commodities/industries might vary it is important that the OD data has the columns specifically mentioned as ``origin_id, destination_id, origin_province, destination_province, min_total_tons (or total_tons), max_total_tons (or total_tons)``.

    The model can track individual commodity/industry flows and failure results, but in the overrall calculations it estimates the  flows and disruptions corresponding to the total tonnage (min or max). The commodity/industry names are important for doing macroeconomic loss analysis explained below. 

    Hence, if an new user input contains only the total tonnage values and no commodity/industry specific OD values, then the model codes will still run with no errors, except the macroeconomic analysis code will not be able to run.

    If the users wish to replace or change these datasets then they must retain the same names of columns with same types of values as given in the original data.
    

Hazards data requirements
-------------------------
1. All hazard datasets are stored:
    - In sub-folders in the path - ``/data/flood_data/FATHOM``
    - As GeoTiff files
    - See ``/data/flood_data/hazard_data_folder_data_info.xlsx`` for details of all hazard files

2. Single-band GeoTiff hazard raster files should have attributes:
    - values - between 0 and 1000 for flood depth in meters
    - raster grid geometry
    - projection systems: Default assumed = EPSG:4326

.. Note::
    The hazard datasets were obtained from a third-party consultant https://www.fathom.global who generated flood maps specific to this project

    It is assumed that all hazard data is provided in GeoTiff format with a projection system. If the users want to introduce new hazard data then it should be in GeoTiff format only.

    When new hazard files are given the ``hazard_data_folder_data_info.xlsx`` should be updated accordingly


Administrative areas with statistics data requirements
------------------------------------------------------
1. Argentina boundary datasets are stored:
    - In the path - ``/incoming_data/admin_boundaries_and_census/departamento/``
    - In the path - ``/incoming_data/admin_boundaries_and_census/provincia/``
    - As Shapefiles

2. Global boundary dataset for map plotting are stored:
    - In the path - ``/data/boundaries/``
    - As Shapefiles

3. Census boundary data are stored:
    - In the path - ``/incoming_data/admin_boundaries_and_census/radios censales/``
    - As a Shapefile

.. Note::
    The admin and boundary datasets were obtained from different sources in Argentina

    .. csv-table:: List of admin and boundary datasets obtained different resources in Argentina
       :header: "Admin boundary", "Source"

       "Department", "Provided through World Bank"
       "Province", "Provided through World Bank"
       "All admin levels", "https://www.naturalearthdata.com/downloads/10m-physical-vectors/"
       "Census - 2010","https://www.indec.gov.ar/"
    

    Admin boundary layers are generally available online. For example at https://data.humdata.org/dataset/argentina-administrative-level-0-boundaries. 

    The department, province and census datasets are used in the model, while the global boundaries are mainly used for generaing map backgrounds

    The names and properties of the attributes listed below are the essential boundary parameters for the whole model analysis. If the users wish to replace or change these datasets then they must retain the same names of columns with same types of values as given in the original data.

    For example if a new census dataset is introduced then it should contain the column ``poblacion`` with new population numbers. The census data used here is at Department level, but it could be replaced with other boundary level census estimates as well. 

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

7. The census datasets should have attributes:
    - ``poblacion`` - Float value of population
    - ``geometry`` - Polygon geometry of boundary with projection ESPG:4326


Macroeconomic data requirements
-------------------------------
1. For the macroeconomic analysis first a multi-regional IO matrix for 24 provinces in Argentina is created from a national-level IO matrix and province level Gross Production Values (GPV) of IO Industries

2. The multi-regional macroeconoic IO data is created from data downloaded from the Instituto Nacional de Estadística y Censos  (INDEC) website. The data is stored as: 
    - Industry and Commodity level IO accounts in the file path ``data/economic_IO_tables/input/sh_cou_06_16.xls`` 
    - Industry level GPV in the file path ``data/economic_IO_tables/input/PIB_provincial_06_17.xls``
    - Names of aggregated industries classification for Argentina in the file path ``data/economic_IO_tables/input/industry_high_level_classification.xlsx``, which should be present in the IO and GPV data files   

3. A set of look-up tables are created to match commodities in the OD matrices to IO industries
    - In the file in path - ``data/economic_IO_tables/input/commodity_classifications-hp.xlsx``
    - The sheetnames in the excel file are ``road, rail, port`` corresponding to the sector for which OD matrices are created
    - ``commodity_group`` - String name of commodity group identified in the OD matrices data
    - ``commodity_subgroup`` - String name of commodity subgroup identified in the OD matrices data
    - ``high_level_industry`` - String name of aggregated industry present in the ``industry_high_level_classification.xlsx`` file 

4. The multi-regional macroeconomic IO data creation, explained later, produces results:
    - In the file in path - ``data/economic_IO_tables/output/IO_ARGENTINA.xlsx``
    - In the file in path - ``data/economic_IO_tables/output/MRIO_ARGENTINA_FULL.xlsx``
    - This data is used in the macroeconomic loss analysis 

.. Note::
    The macroeconomic data are obtained from INDEC at https://www.indec.gob.ar/nivel3_default.asp?id_tema_1=3&id_tema_2=9&fbclid=IwAR02qnMIJeu86xUM5TFK5hrABN3FcJLGx6k5BYNhxLe4o0FhqJxuV2wxb5E. The PIB and COU datasets are used in the model

    If the users want to update the IO tables for Argentina then it is recommended that they replace the above files ``sh_cou_06_16.xls`` and ``PIB_provincial_06_17.xls`` with exactly the same sheetnames and data structures as given in the original data used by the IO model scripts.

    If the industry classifications are modified in the IO data then the changeas should also be made in ``industry_high_level_classification.xlsx`` and ``commodity_classifications-hp.xlsx`` files.  

Adaptation options and costs requirements
-----------------------------------------
1. All adaptation options input datasets are stored:
    - In the file - ``/data/adaptation_options/ROCKS - Database - ARNG (Version 2.3) Feb2018.xlsx``
    - We use the sheet ``Resultados Consolidados`` for our analysis

.. Note::
    The adaptation data is very specific and if new options are created then the users will need to change the scripts as well