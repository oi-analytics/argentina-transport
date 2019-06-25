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
    - In each Python script described below, see the inline comments to understand where the inputs are given
    - It is recommended to run the Python scripts in the same order as described here
    - If the users want to use the same data and make modifications in values of data then they can follow the steps and codes explained below. Otherwise this whole process can be skipped if the users know how to create the networks in the formats specified in the `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_
    - If the data are updated, especially if OD flows are updated to another year, then the users will have to make changes to the Python codes to be able to input new data files
    - Mostly all inputs are read using the Python libraries of `pandas <https://pandas.pydata.org>`_ and `geopandas <http://geopandas.org>`_. The user should familiarise themselves with file reading and writing functions in these libraries. For example most codes use the geopandas function `read_file <http://geopandas.org/io.html>`_  and `to_file <http://geopandas.org/io.html>`_to read and write shapefiles, and the pandas functions `read_excel and to_excel <http://pandas.pydata.org/pandas-docs/stable/user_guide/io.html>`_ and `read_csv and to_csv <http://pandas.pydata.org/pandas-docs/stable/user_guide/io.html>`_ to read and write excel and csv data respectively  

Creating the road network
-------------------------
.. Note::
    The road network is combined from datasets of national, provincial and rural roads in Argentina. The raw GIS data for these three types of networks were obtained from the Ministry of Transport and Dirección Nacional de Vialidad (DNV)

    .. csv-table:: List of road datasets obtained from different resources in Argentina
       :header: "Road data", "Source"

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

    The topology script above is very specific to the case of the particular input data provide here. Unfortunaly if the data is changed them the users might have to test their results again if they run the topology script. We had to manually clean, edit and add some new edges to complete the topology. But this depends upon the quality of input provided and not the python script!  

    The Python codes require the specific inputs of the above datasets from the users to be able to identify the specific rows and columns in the data. If the users change these datasets in the future then, to use the same Python codes, then should preserve the column names and their properties

    In the excel sheets in ``incoming_data/road_properties/`` and ``incoming_data/costs/road/`` the original data obtained from the DNV are preserved, and changing the locations and columns and rows will require making changes to the scripts. When data is missing some assumptions of values are taken, which are hard coded in the Python script. 

    The users should familiarize themselves with the functions 
    in the script :py:mod:`atra.preprocess.road_network_creation` if 
    they want to change data. Below the kinds of user inputs changes in this script are explained
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
    - As Excel file with bridges attributes in sheetname ``Consulta``

.. Note::     
    The finalized national-roads bridges data is created by executing 1 Python script after the road network has been already created:
        - Run :py:mod:`atra.preprocess.road_bridge_matches` to extract data from the files described in Step 1 above
    
    The original bridges data downloaded from https://www.argentina.gob.ar/vialidad-nacional/sig-vial provided a shapefile with only bridge locations, and the excel sheet with bridge properties. Unfortunately these two files did not have a common ID column to link them together. Hence the python script mainly matches the bridges to their location information using the kilometer marker locations specified for the bridge Excel data and matching these with the kilometer markers and national roads GIS data provided for the national roads, explained in `Creating the road network <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/predata.html#creating-the-road-network>`_. If the users alrready have a bridge dataset has all attribtues in a geocoded files, then they do not need to run the Python script. But they will still have to match the ``bridge_id`` to the ``edge_id`` column of the ``road_edges`` dataset.    

    The result of this script creates the ``bridge_edges`` and ``bridges`` files described in the folder path ``data/network/``. If the users change the bridges datasets in the folder path ``/incoming_data/pre_processed_network_data/bridges/puente_sel/``, then to use the same Python script to create new ``bridge_edges`` and ``bridges`` files they should replace the shapefile and excel sheet data while still retaining the following column names in their data
        - ``id_estruct`` - Numeric values to ID column only present in shapefile   
        - ``ids`` - Numeric values of bridge ID. Renamed to ``bridge_id`` by the model
        - ``longitud`` - Float values of bridge length in meters. Renamed to ``length`` by the model
        - ``ancho de vereda derecha`` - Float values of right lane width of bridge in meters. Used for estimating ``width``
        - ``ancho de vereda izquierda`` - Float values of left lane width of bridge in meters. Used for estimating ``width``
        - ``ancho pavimento asc.`` - Float values of pavement width of bridge in meters. Used for estimating ``width``
        - ``ancho pavimento desc.`` - Float values of pavement width of bridge in meters. Used for estimating ``width``
        - ``tipo de estructura`` - String description of the type of bridge. Renamed to ``structure_type`` by the model
        - ``ruta`` - String name to national road where bridge belongs
        - ``geometry`` - Point and line geometries of bridges with projection ESPG:4326
        - Several other attributes which are not used in the rest of the model


Creating road OD matrix at node level
-------------------------------------
.. Note::     
    The road OD matrix data is matched to the ``road_nodes`` data by executing 1 Python script after the road network has been already created:
        - Run :py:mod:`atra.preprocess.road_od_flows` to create the road OD matrix at node-node level 
    
    The original road OD data provided by the Secretaría de Planificación de Cargas contains high-level annual OD matrices for 123 domestic zones in Argentina. This data is disaggregated at the road node level based on follwing assumptions:
        - The nodes on national and province roads are only considered as OD nodes
        - For each node the near population (obtained from census data) is estimated and only those nodes with population above 1000 are considered as OD nodes
        - The OD nodes flows allocation is similar to a gravity model based on the importance of origin and destination nodes in creating and attracting OD flows. 
        - The OD matrices are annual and are converted to daily flows by dividing by 365   

    If the users want to change the high-level OD data then they should replace the OD datasets as described below. They can also can update the ``road_nodes``, province and census shapefiles described in `Administrative areas with statistics data requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#administrative-areas-with-statistics-data-requirements>`_

1. Road commodity OD matrices data are stored:
    - In the path - ``/incoming_data/OD_data/road/Matrices OD 2014- tablas/``
    - As Excel files
    - The name of the excel file and excel sheet correspond to commodity groups and subgroups
    - Each Excel Sheet is a 123-by-123 matrix of OD tons with first row and first column showing Zone IDs
    - We use the sheets ``Total Toneladas 2014`` if given otherwise add tons across sheets
    - Each Excel Sheet is a 123-by-123 matrix with first row and first column showing Zone IDs

2. Road commodity OD Zone data is stored:
    - In the path - ``/incoming_data/OD_data/road/Lineas de deseo OD- 2014/3.6.1.10.zonas/``
    - As Shapefile
    - ``data`` - The ``od_id`` that matches the OD matrices Excel data
    - ``geometry`` - Polygon geometry of zone with projection ESPG:4326

Creating the rail network and OD matrix
---------------------------------------
.. Note::     
    The finalized rail network and OD matrix data are all created by executing 1 Python script:
        - Run :py:mod:`atra.preprocess.rail_od_flows` to create the rail network and OD matrix at node-node level 
    
    .. csv-table:: List of rail datasets obtained from different resources in Argentina
       :header: "Rail data", "Source"

       "Rail lines", "Provided through World Bank from MoT"
       "Stations", "Provided through World Bank from MoT"
       "OD data", "Secretaría de Planificación de Cargas"
       "Transport Costs","Estimated from COSFER model by Secretaría de Planificación de Transporte"

    Rail GIS data can also be downloaded from the portal https://ide.transporte.gob.ar/geoserver/web/. See the Python script :py:mod:`atra.preprocess.scrape_wfs`

    The original rail OD data provided by the Secretaría de Planificación de Cargas contains station-station OD matrices which are time-stamped for the year 2015. But there are several issues with using the rail GIS network and OD data directly:
        - The names of the OD stations do not always match the nodes in the GIS data. So we do not always know the location of OD nodes
        - The route information does not match any GIS data, if it exists
        - In several cases the time-stamps are missing, so we do not know the time of start and end of a jounrey
        - In several cases the distance of travel is missing, so we do not know the length of the jounrey 
        - Only is some instances does the data indicate the origin and destination provinces
        - The GIS network shows several historic lines, which are no longer used. The GIS data does not indicate which lines are no longer in operation     

    The script :py:mod:`atra.preprocess.rail_od_flows` resolves some of the issues above. The following operations are performed by the script:
        - The OD nodes are matched to GIS nodes
        - The OD flows are routed on the GIS network, to check as best whether the observed OD distances match the estimated OD distances obtained from the GIS network. This helps in validating whether OD nodes were assigned correctly on the GIS network
        - The total OD tonnages are aggregated over a day, based on the start date. From this the minimum and maximum OD flows are estimated betwork OD pairs
        - Speeds are assigned based on the time-stamps of origin and destination stations. Default speeds of rail lines are assumed to be 20 km/hr

    Unfortunalety the script :py:mod:`atra.preprocess.rail_od_flows` is very specific to the input datasets, and relies on having the same column names and organisation of data as described in the input data used in this current version   

1. Rail GIS data are stored:
    - In the path - ``/incoming_data/pre_processed_network_data/railways/national_rail/``
    - As Shapefiles

.. Note::
    The topology is assumed to have already been created in the rail network. We had to create some of this manually, so we cannot provide a automated Python script to do so. The user is recommended to check tools in the Python library `snkit <https://github.com/tomalrussell/snkit>`_ for creating network topology.

2. Rail OD matrices data are stored:
    - In the path - ``/incoming_data/OD_data/rail/Matrices OD FFCC/``
    - As Excel files
    - The names of the sheets within the excel files vary. See the Python script for specific information
    - The OD data in each excel sheet varies, but some information is necessary for OD matrix creation
    - ``origin_station`` - String name of origin station
    - ``origin_date`` - Datetime object for date of journey
    - ``destination_station`` - String name of destination station
    - ``commodity_group`` - String name of commodity groups
    - ``line_name`` - String name of thee line used for transport  
    - ``tons`` - Numeric values of tonnages
    - Several other column, which are referred to in the Python script

3. A file to match names of OD stations to GIS nodes is stored:
    - In the path - ``/incoming_data/pre_processed_network_data/railways/rail_data_cleaning/station_renames.xlsx``
    - As Excel file
    - This was created manually by looking at the OD and GIS data, and inferring matches based on Google searches and our judgement

4. Rail costs are stored:
    - In the Excel file path - ``incoming_data/costs/rail/rail_costs.xlsx``
    - We use the sheet ``route_costs``

Creating the port network and OD matrix
---------------------------------------
.. Note::     
    The port network and OD matrix data are all created by executing 1 Python script:
        - Run :py:mod:`atra.preprocess.port_od_flows` to create the port network and OD matrix at node-node level 
    
    .. csv-table:: List of port datasets obtained from different resources in Argentina
       :header: "Port data", "Source"

       "Port locations", "Secretaría de Planificación de Cargas"
       "Maritime routes", "Created manually from OSM data"
       "OD data", "Secretaría de Planificación de Cargas"
       "Transport Costs","Estimated from data from Secretaría de Planificación de Transporte"

    Port GIS node data can also be downloaded from the portal https://ide.transporte.gob.ar/geoserver/web/. See the Python script :py:mod:`atra.preprocess.scrape_wfs`

    The original port OD data provided by the Secretaría de Planificación de Cargas contains port specific OD data which are time-stamped for the year 2017. But there are several issues with using the port GIS network and OD data directly:
        - The original data gives port specific information on how much different types of freight are exported, imported or transiting at the port 
        - The information on the origin and destination of the freights are mostly missing, so we have inferred them as best
        - In several cases the time-stamps are missing, so we do not know the time of start and end of a jounrey 
        - Only is some instances does the data indicate the origin and destination provinces or countries     

    The script :py:mod:`atra.preprocess.port_od_flows` resolves some of the issues above. The following operations are performed by the script:
        - The OD nodes are inferred by gap filling the port-level flow data
        - The total OD tonnages are aggregated over a day, based on the start date. From this the minimum and maximum OD flows are estimated betwork OD pairs
        - Default speeds are assumed to be 4-5 km/hr

    Unfortunalety the script :py:mod:`atra.preprocess.port_od_flows` is very specific to the input datasets, and relies on having the same column names and organisation of data as described in the input data used in this current version

1. Port GIS data are stored:
    - In the path - ``/incoming_data/pre_processed_network_data/ports/``
    - As Shapefiles

.. Note::
    The topology is assumed to have already been created in the rail network. We had to create some of this manually, so we cannot provide a automated Python script to do so. The user is recommended to check tools in the Python library `snkit <https://github.com/tomalrussell/snkit>`_ for creating network topology.

2. A file to match names of ports and commodity to GIS nodes is stored:
    - In the path - ``/incoming_data/pre_processed_network_data/ports/rail_od_cleaning/od_port_matches.xlsx``
    - As Excel file
    - This was created manually by looking at the OD and GIS data, and inferring matches based on Google searches and our judgement

3. Port specific freight data are stored:
    - In the Excel file path - ``/incoming_data/OD_data/ports/Puertos/Cargas No Containerizadas - SSPVNYMM.xlsx``
    - We use the excel sheet ``2017``
    - Some information is necessary for OD matrix creation
    - ``Puerto`` - String name of port where data is recorded
    - ``Puerto de Procedencia`` - String name of origin port
    - ``País de Procedencia`` - String name of origin country
    - ``Fecha Entrada`` - Datetime object for entrance date recorded at port
    - ``Puerto de Destino`` - String name of destination port
    - ``País de Destino`` - String name of destination country
    - ``Producto Corregido`` - String name of commodity subgroups 
    - ``Rubro`` - String name of commodity groups
    - ``Tipo de Operación`` - String name of operation type, associated to exports, imports, and transit
    - ``Total Tn`` - Numeric values of tonnages
    - ``Medida`` - String value of type of tonnages

4. Port costs are stored:
    - In the Excel file path - ``incoming_data/costs/port/port_costs.xlsx``
    - We use the excel sheet ``costs`` 

Creating the air network and passenger data
-------------------------------------------
.. Note::     
    The air network and passenger flow data are all created by executing 1 Python script:
        - Run :py:mod:`atra.preprocess.network_air` to create the air network and passenger flows at node-node level 
    
    .. csv-table:: List of port datasets obtained from different resources in Argentina
       :header: "Air data", "Source"

       "Airport locations", "https://ide.transporte.gob.ar/geoserver/web/"
       "Passenger number - 2016", "Secretaría de Planificación de Cargas"

    Airport GIS nodee data is downloaded from the portal https://ide.transporte.gob.ar/geoserver/web/. See the Python script :py:mod:`atra.preprocess.scrape_wfs`

1. Air passenger OD data is contained in the airlines shapefile
    - In the file - ``/data/pre_processed_networks_data/air/SIAC2016pax.shp``
    - Some information is necessary for OD matrix creation
    - ``Cod_Orig`` - String IATA code of origin airport
    - ``Cod_Destt`` - String IATA code of destination airport
    - ``Pax_2016`` - Numeric values of passenger numbers

Creating the multi-modal network edges
--------------------------------------
.. Note::     
    The multi-modal network edges are all created by executing 1 Python script:
        - Run :py:mod:`atra.preprocess.multi_modal_network_creation`

    The multi-modal edges can only be created once all the other network are created. The code inputs the finalized ``road``, ``rail`` and ``port`` files in the ``data/network/`` folder path


Industry specific province-level OD matrix
------------------------------------------
.. Note::     
    For macroeconomic analysis an industry specific province-level OD matrix is created by executing 1 Python script:
        - Run :py:mod:`atra.preprocess.od_combine`

    The province OD matric can only be created once all the other OD matrices are created. The code inputs the finalized ``{mode}_province_annual_ods.csv`` OD files in the ``data/OD_data/`` folder path
    

Preparing Hazard Data
---------------------
Purpose:
    - Convert GeoTiff raster hazard datasets to shapefiles based on masking and selecting values from
        - Single-band raster files

Execution:
    - Load data as described in `Processed Data Assembly <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/data.html>`_ `Hazards <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/data.html#hazards>`_
    - Run :py:mod:`atra.preprocess.convert_hazard_data`

Result:
    - Create hazard shapefiles with names described in excel sheet in `Processed Data Assembly <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/data.html>`_ `Hazards <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/data.html#hazards>`_ and attributes:
        - ``ID`` - equal to 1
        - ``geometry`` - Polygon outline of selected hazard
    - Store outputs in same paths in directory ``/data/flood_data/FATTHOM``
