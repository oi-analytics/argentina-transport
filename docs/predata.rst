=================================
Creating topological network data
=================================
.. Important::
    The topological network data and parameters described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_ had to be created from several data sources, which had several gaps.

    - This section describes collected datasets that are used to create data for the Argentina Transport Risk Analysis (ATRA)
    - The datasets listed here are specfic to Argentina and are used as inputs to make the finalized data used in the rest of the model
    - To implement the ATRA pre-processing without any changes in existing codes, all data described here should be created and stored exactly as indicated below
    - Python scripts were created specific to clean and modify these datasets, due to which changes made to the way the data are organized will most probably also result in making changes to the Python scripts
    - In some instances some values for data are encoded within the Python scripts, so the users should be able to make changes directly in the Python scripts
    - All pre-processed networks data are stored in sub-folders in the file path - ``/data/pre_processed_networks_data/``

Creating the road network
-------------------------
.. Note::
    The road network is combined from datasets of national, provincial and rural roads in Argentina. The raw GIS data for these three types of networks were obtained from the Ministry of Transport and Dirección Nacional de Vialidad (DNV)

    .. csv-table:: List of road datasets obtained from different resources in Argentina
       :header: "Road network", "Source"

       "National", "https://www.argentina.gob.ar/vialidad-nacional/sig-vial"
       "Province", "Provided through World Bank from MoT"
       "Rural", "Provided through World Bank from MoT"
       "National roads bridges","https://www.argentina.gob.ar/vialidad-nacional/sig-vial"
       "OpenStreetMaps", "https://openmaptiles.com/downloads/dataset/osm/south-america/argentina/#2.96/-40.83/-63.6"
       "National roads widths", "Provided through World Bank from DNV"
       "National roads speeds", "Provided through World Bank from DNV" 

    The portal https://ide.transporte.gob.ar/geoserver/web/ also contains open-source transport data that was downloaded, including the province and rural road networks. See the Python script :py:mod:`atra.preprocess.scrape_wfs` 

1. All pre-processed networks data are stored:
    - In sub-folders in the file path - ``/data/pre_processed_networks_data/``
    - Roads are extracted from the sub-folder - ``/roads/combined_roads``
    - Railways are extracted from the sub-folder - ``/railways/national_rail/``
    - Ports are extracted from the sub-folder - ``/ports/``
    - Airlines are extracted from the sub-folder - ``/air/``
    - As Shapefiles with topology of network nodes and edges
    - The names of files are self-explanatory
    
2. All nodes should have the following attributes:
    - ``node_id`` - String Node ID
    - ``geometry`` - Point geometry of node with projection ESPG:4326
    - variable list of attributes depending upon sector

3. All edges should have the following attributes:
    - ``edge_id`` - String edge ID
    - ``from_node`` - String node ID that should be present in node_id column
    - ``to_node`` - String node ID that should be present in node_id column
    - ``geometry`` - LineString geometry of edge with projection ESPG:4326
    - variable list of attributes depending upon sector

4. National Roads specifc GIS data are stored: 
    - In sub-folders in the path - ``/incoming_data/pre_processed_network_data/roads/national_roads/``
    - As Shapefiles with attributes
    - File in sub-folder ``/indice_de_estado/`` contains road surface quality as numeric values
    - File in sub-folder ``/indice_de_serviciabilidad/`` contains road service quality as numeric values
    - File in sub-folder ``/materialcarril_sel/`` contains road surface meterial as string values
    - File in sub-folder ``/tmda/`` contains TMDA counts as numeric values
    - File in sub-folder ``/v_mojon/`` contains locations of kilometer markers
    
5. National-roads bridges GIS data are stored:
    - In the path - ``/incoming_data/pre_processed_network_data/roads/national_roads//puente_sel/``
    - As Shapefiles with Point geometry of nodes with projection ESPG:4326
    - As Excel file with bridges attributes
    - ``bridge_id`` - String bridge ID
    - ``edge_id`` - String edge ID matching ``edge_id`` of national-roads edges intersecting with bridges
    - ``geometry`` - Point geometry of node with projection ESPG:4326

.. Note::
    We assume that networks are provided as topologically correct connected graphs: each edge
    is a single LineString (may be straight line or more complex line), but must have exactly
    two endpoints, which are labelled as ``from_node`` and ``to_node`` (the values of these
    attributes must correspond to the ``node_id`` of a node).

    Wherever two edges meet, we assume that there is a shared node, matching each of the intersecting edge endpoints. For example, at a t-junction there will be three edges meeting
    at one node.

Network OD data
---------------
1. Road commodity OD matrices data are stored:
    - In the path - ``/incoming_data/5/Matrices OD 2014- tablas/``
    - As Excel files
    - TThe name of the excel file and excel sheet correspond to commodity groups and subgroups
    - Each Excel Sheet is a 123-by-123 matrix of OD tons with first row and first column showing Zone IDs
    - We use the sheets ``Total Toneladas 2014`` if given otherwise add tons across sheets
    - Each Excel Sheet is a 123-by-123 matrix with first row and first column showing Zone IDs

2. Road commodity OD Zone data is stored:
    - In the path - ``/incoming_data/5/Lineas de deseo OD- 2014/3.6.1.10.zonas/``
    - As Shapefile
    - ``data`` - The ``od_id`` that matches the OD matrices Excel data
    - ``geometry`` - Polygon geometry of zone with projection ESPG:4326 

3. Rail OD matrices data are stored:
    - In the path - ``/incoming_data/5/rail_od_matrices/Matrices OD FFCC/``
    - As Excel files
    - The OD data in each excel sheet varies, but some information is necessary for OD matrix creation
    - ``origin_station`` - String name of origin station
    - ``origin_date`` - Datetime object for date of journey
    - ``destination_station`` - String name of destination station
    - ``commodity_group`` - String name of commodity groups
    - ``line_name`` - String name of thee line used for transport  
    - ``tons`` - Numeric values of tonnages

4. Port OD matrices data are stored:
    - In the Excel file path - ``/incoming_data/5/Puertos/Cargas No Containerizadas - SSPVNYMM.xlsx``
    - The OD data in each excel sheet varies, but some information is necessary for OD matrix creation
    - ``origin_port`` - String name of origin port
    - ``origin_date`` - Datetime object for date of journey
    - ``destination_port`` - String name of destination port
    - ``commodity_group`` - String name of commodity groups
    - ``operation_type`` - String name of operation type, associated to exports, imports, and transit
    - ``tons`` - Numeric values of tonnages

5. Air passenger OD data is contained in the airlines shapefile
    - In the file - ``/data/pre_processed_networks_data/air/SIAC2016pax.shp``


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