=================================
Pre-processing data for the model
=================================
.. Important::
    The topological network data and parameters described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_ had to be created from several data sources, which had several gaps.

    - This section describes collected datasets that are used to create data for the Argentina Transport Risk Analysis (ATRA)
    - The datasets listed here are specfic to Argentina and are used as inputs to make the finalized data used in the rest of the model
    - To implement the ATRA pre-processing without any changes in existing codes, all data described here should be created and stored exactly as indicated below
    - Python scripts were created specific to clean and modify these datasets, due to which changes made to the way the data are organized will most probably also result in making changes to the Python scripts
    - In some instances some values for data are encoded within the Python scripts, so the users should be able to make changes directly in the Python scripts
    - If the users want to use the same data and make modifications in values of data then they can follow the steps and codes explained below. Otherwise this whole process can be skipped if the users know how to create the networks in the formats specified in the `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_

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
       "OpenStreetMaps (OSM)", "https://openmaptiles.com/downloads/dataset/osm/south-america/argentina/#2.96/-40.83/-63.6"
       "National roads widths", "Provided through World Bank from DNV"
       "National roads speeds", "Provided through World Bank from DNV"
       "Road vehicle costs", "Provided through World Bank from DNV" 

    The portal https://ide.transporte.gob.ar/geoserver/web/ also contains open-source transport data that was downloaded, including the province and rural road networks. See the Python script :py:mod:`atra.preprocess.scrape_wfs` 

1. The road network data is stored:
    - In sub-folders in the file path - ``/data/pre_processed_networks_data/roads/``
    - As Shapefiles with attributes
    - File in sub-folder ``/national_roads/rutas/`` contains national roads
        - We extract the columns ``cod_ruta`` (for ``road_name``), ``sentido = A`` and ``geometry``
    - File in sub-folder ``/province_roads/`` contains province roads
        - We extract the columns ``nombre`` (for ``road_name``), ``clase`` (for ``surface``) and ``geometry``
    - File in sub-folder ``/rural_roads/`` contains rural roads
        - We extract the columns ``characteris`` (for ``surface``) and ``geometry``
    - File in sub-folder ``/osm_roads/`` contains OSM roads for gap filling
        - We extract the columns ``road_name``, ``road_type`` and ``geometry``

2. National Roads specifc GIS data are stored: 
    - In sub-folders in the path - ``/incoming_data/pre_processed_network_data/roads/national_roads/``
    - As Shapefiles with attributes
    - File in sub-folder ``/indice_de_estado/`` contains road surface quality as numeric values
        - We use the columns ``nro_regist`` as id,``valor`` for ``road_quality``, ``sentido = A`` and ``geometry``
        - Road surface quality is used to estimate speeds on the national roads
    - File in sub-folder ``/indice_de_serviciabilidad/`` contains road service quality as numeric values
        - We use the columns ``nro_regist`` as id,``valor`` for ``road_service``, ``sentido = A`` and ``geometry``
        - Road service quality is used to estimate speeds on the national roads
    - File in sub-folder ``/materialcarril_sel/`` contains road surface meterial as string values
        - We use the columns ``id_materia`` as id,``grupo`` for ``material_group``,``sentido = A`` and ``geometry``
        - Surface material determines the conditon of the national roads for adaptation investments
    - File in sub-folder ``/tmda/`` contains TMDA counts as numeric values
        - We use the columns ``nro_regist`` as id,``valor`` for ``road_service``, ``sentido = A`` and ``geometry``
        - TMDA gives observed vehcile counts on national roads
    - File in sub-folder ``/v_mojon/`` contains locations of kilometer markers
        - We use the columns ``id``, ``progresiva``, ``distancia`` and ``geometry``
        - kilometer markers are used in assinging properties on national roads and locating bridges

3. Data on select national roads widths and terrains are stored:
    - In the Excel file path - ``incoming_data/road_properties/Tramos por Rutas.xls``
    - We use the sheet ``Hoja1``

4. Data on select national roads speeds are stored:
    - In the Excel file path - ``incoming_data/road_properties/TMDA y Clasificación 2016.xlsx`` 
    - We use the sheet ``Clasificación 2016``

5. Road costs are stored:
    - In the path - ``/incoming_data/costs/road/``
    - As Excel files
    - The Vehicle Operating Costs are in the file ``Costos de Operación de Vehículos.xlsx``
    - We use the sheet ``Camión Pesado`` for costs
    - The tariff costs are in the file ``tariff_costs.xlsx``

.. Note::
    The finalized road network is created by executing 3 Python scripts:
        - Run :py:mod:`atra.preprocess.combine_roads` to extract data from the files described in Step 1 above
        - Run :py:mod:`atra.preprocess.network_road_topology` to create road nodes and edges topology  
        - Run :py:mod:`atra.preprocess.road_network_creation` to assign road properties described above. This is the main script that creates the finalized road network and requires several inputs

    The result of these scripts create the ``road_edges`` and ``road_nodes`` files described in the folder path ``data/network/``

    The Python codes require the specific inputs of the above datasets from the users to be able to identify the specific rows and columns in the data. If the users change these datasets in the future then, to use the same Python codes, then should preserve the column names and their properties

    In the excel sheets in ``incoming_data/road_properties/`` and ``incoming_data/costs/road/`` the original data obtained from the DNV are preserved, and changing the locations and columns and rows will require making changes to the scripts. When data is missing some assumptions of values are taken, which are hard coded in the Python script. 

    The users should familiarize themselves with the functions in the script :py:mod:`atra.preprocess.road_network_creation` if they want to change data. Below the kinds of user inputs changes in this script are explained
        - Lines 445-554 where all the inputs are given to the code. See the function:py:mod:`main`
        - Currency exchange rate from ARS to USD is 1 ARS = 0.026 USD. See the function:py:mod:`main`
        - The default ``surface`` of a national road is assumed to be ``Asfalto``, and other roads it is ``Tierra``. See the function :py:mod:`assign_road_surface`
        - The default ``width`` of national and province roads is assumed to be 7.3m (2-lane) and rural roads is 3.65m (1-lane). The default ``terrain`` is assumed flat. See the function :py:mod:`assign_road_terrain_and_width`
        - If no informattion on road speeds is provided through the data in ``incoming_data/road_properties/TMDA y Clasificación 2016.xlsx`` then the road speeds are assumed to be as following. See the function :py:mod:`assign_min_max_speeds_to_roads`
        - For national roads with poor to fair quality (0 < ``road_service`` <= 1) or (0 < ``road_quality`` <= 3) speeds vary from 50-80 km/hr
        - For national roads with fair to good quality (1 < ``road_service`` <= 2) or (3 < ``road_quality`` <= 6) speeds vary from 60-90 km/hr
        - For national roads with good to very good quality speeds vary from 70-100 km/hr
        - For all province roads speeds vary from 40-60 km/hr
        - For all rural roads speeds vary from 20-40 km/hr      

Creating the national roads bridges data
----------------------------------------
1. National-roads bridges GIS data are stored:
    - In the path - ``/incoming_data/pre_processed_network_data/bridges/puente_sel/``
    - As Shapefiles with Point geometry of nodes with projection ESPG:4326
    - As Excel file with bridges attributes
    - ``bridge_id`` - String bridge ID
    - ``edge_id`` - String edge ID matching ``edge_id`` of national-roads edges intersecting with bridges
    - ``length`` - Float values of bridge length in meters
    - ``width`` - Float values to bridge width in meters
    - ``type`` - String description of the type of bridge 
    - ``geometry`` - Point geometry of node with projection ESPG:4326
    - Several other attributes which are not used in the rest of the model

.. Note::
    The finalized national-roads bridges data is created by executing 1 Python script after the road network has been already created:
        - Run :py:mod:`atra.preprocess.road_bridge_matches` to extract data from the files described in Step 1 above
    
    The result of this script create the ``bridge_edges`` and ``bridges`` files described in the folder path ``data/network/``


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
    - In the Excel file path - ``incoming_data/costs/rail/rail_costs.xlsx``
    - We use the sheet ``route_costs``

3. Port costs are stored:
    - In the Excel file path - ``incoming_data/costs/port/port_costs.xlsx``  

Creating the rail, ports and air networks
-----------------------------------------
1. The network details are:
    - Railways are extracted from the sub-folder - ``/railways/national_rail/``
    - Ports are extracted from the sub-folder - ``/ports/``
    - Airlines are extracted from the sub-folder - ``/air/``
    - As Shapefiles with topology of network nodes and edges
    - The names of files are self-explanatory