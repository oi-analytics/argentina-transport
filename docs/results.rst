====================
Analysis and Results
====================
.. Important::
    - This section describes the steps Analysis and Results steps of the Argentina Transport Risk Analysis (ATRA)
    - To implement the ATRA without any changes in existing codes, all data described here should be created and stored exactly as indicated below


Mapping Flows onto Networks
---------------------------
Purpose:
    - Map the national-scale OD node level matrix values to network paths
        - For all transport modes at national scale
        - Estimate 2 values - A MIN and a MAX value of flows between each selected OD node pair
        - Based on MIN-MAX generalised costs estimates

Execution:
    - Load data as described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_ and `OD matrices requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#od-matrices-requirements>`_
    - For road, rail, port OD matrices run :py:mod:`atra.analysis.flow_mapping`

Result:
    - Store OD flow paths in csv outputs in ``/results/flow_mapping_paths/``
    - Store total OD flows on edges in csv files in ``/results/flow_mapping_combined/``
    - Optional - Store OD flows on edges in shapefiles in ``/results/flow_mapping_shapefiles/``
    
    - csv files in ``/results/flow_mapping_paths/`` contain attributes:
        - ``origin_id`` - String node ID of Origin
        - ``destination_id`` - String node ID of Destination
        - ``origin_province`` - String name of Province of Origin node ID
        - ``destination_province`` - String name of Province of Destination node ID
        - ``min_edge_path`` - List of string of edge IDs for paths with minimum generalised cost flows
        - ``max_edge_path`` - List of string of edge IDs for paths with maximum generalised cost flows
        - ``min_distance`` - Float values of estimated distance for paths with minimum generalised cost flows
        - ``max_distance`` - Float values of estimated distance for paths with maximum generalised cost flows
        - ``min_time`` - Float values of estimated time for paths with minimum generalised cost flows
        - ``max_time`` - Float values of estimated time for paths with maximum generalised cost flows
        - ``min_gcost`` - Float values of estimated generalised cost for paths with minimum generalised cost flows
        - ``max_gcost`` - Float values of estimated generalised cost for paths with maximum generalised cost flows
        - ``min_total_tons`` - Float values of estimated daily minimum total tonnages for all industries bettween OD pair
        - ``max_total_tons`` - Float values of estimated daily maximum total tonnages for all industries bettween OD pair
        - ``industry_columns`` - All daily tonnages of industry columns given in the OD matrix data for specific sectors
    
    - csv files in ``/results/flow_mapping_combined/`` contain attributes:
        - ``edge_id`` - String edge ID
        - ``min_total_tons`` - Float values of estimated daily minimum total tonnages on edge
        - ``max_total_tons`` - Float values of estimated daily maximum total tonnages on edge
        - ``commodity/industry_columns`` - All total daily tonnages of commodity/industry columns on edge


Hazard Exposure
---------------
Purpose:
    - Intersect hazards and network line and point geometries with hazatd polygons
        - Write final results to Shapefiles
    - Collect network-hazard intersection attributes
        - Combine with boundary Polygons to collect network-hazard-boundary intersection attributes
        - Write final results to an Excel sheet

Execution:
    - Load data as described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_ and `Preparing Hazard Data <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/predata.html#preparing-hazard-data>`_, and `Administrative areas with statistics data requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#administrative-areas-with-statistics-data-requirements>`_
    - Run :py:mod:`atra.analysis.hazards_networks_intersections`
    - Run :py:mod:`atra.analysis.hazards_network_intersections_results_collect`

Result:
    - Store shapefile outputs in the directory ``/results/networks_hazards_intersection_shapefiles/``
    - All hazard-edge intersection shapefiles with attributes:
        - ``edge_id`` - String name of intersecting edge ID
        - ``length`` - Float length of intersection of edge LineString and hazard Polygon
        - ``geometry`` - LineString geometry of intersection of edge LineString and hazard Polygon

    - All hazard-node intersection shapefile with attributes:
        - ``node_id`` - String name of intersecting node ID
        - ``geometry`` - Point geometry of intersecting node ID

    - Store summarised results in csv files in path ``/results/hazard_scenarios/``
    - csv files of network-hazard-boundary intersection with attributes:
        - ``edge_id``/``node_id`` - String name of intersecting edge ID or node ID
        - ``length`` - Float length of intersection of edge LineString and hazard Polygon: Only for edges
        - ``province_id`` - String/Integer ID of Province
        - ``province_name`` - String name of Province
        - ``department_id`` - String/Integer ID of Department
        - ``department_name`` - String name of Department
        - ``hazard_type`` - String name of hazard type
        - ``model`` - String name of hazard model
        - ``year`` - String name of hazard year
        - ``climate_scenario`` - String name of hazard scenario
        - ``probability`` - Float/String value of hazard probability
        - ``min_depth`` - Integer value of minimum value of flood depth of exposure
        - ``max_depth`` - Integer value of maximum value of flood depth of exposure


Combine hazard scenarios for risk weights
-----------------------------------------
Purpose
    - Combine failure scenarios across probability levels into single value per
      hazard type, scenario, network edges
    - The risk weights are the sum of probability*exposure for each hazard type intersecting network edges

Execution
    - Load results from `Hazard exposure <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#hazard-exposure>`_ and `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_
    - Run :py:mod:`atra.analysis.collect_network_hazard_scenarios_national`

Result
    - Combined scenarios in
      ``results/network_stats/{mode}_hazard_intersections_risk_weights.csv``
        - ``edge_id/bridge_id`` - string, name of failed edge
        - ``hazard_type`` - string, name of hazard
        - ``model`` - string, name of hazard model (if any)
        - ``climate_scenario`` - string, name of climate scenario (if any)
        - ``year`` - integer, year of hazard data
        - ``edge_length`` - float, length of edge
        - ``min/max_height`` - float, hazard height (if any)
        - ``min/max_exposure_percent`` - float, percentage of edge exposed to hazard
        - ``min/max_duration_wt`` - float, duration weight
        - ``min/max_exposure_length`` - float, length of edge exposed to hazard
        - ``risk_wt`` - float, risk weight
        - ``dam_wt`` - float, damage weight


Network Failure Analysis
------------------------
Purpose:
    - Failure analysis of edges in invidiual networks
        - To estimate flow isolations and rerouting effects on same network
    - Failure analysis of edges in networks with multi-modal options
        - To estimate flow isolations and rerouting effects with multi-modal options

Execution:
    - Load network and flow excel data as described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_, `Mapping Flows onto Networks <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#mapping-flows-onto-networks>`_, and failure scenarios from `Hazard exposure <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#hazard-exposure>`_
    - For all networks failure analysis run :py:mod:`atra.analysis.failure_estimation`
    - For networks failure analysis with multi-modal options run :py:mod:`atra.analysis.multi_modal_failure_estimation`
    
Result:
    - Store csv outputs in the directory ``/results/failure_results/``
    - Optional - Store shapefile outputs in ``/results/failure_shapefiles/``

    - All failure scenarios results in ``/results/failure_results/all_fail_scenarios/``
        - ``edge_id`` - String name or list of failed edges
        - ``origin_id`` - String node ID of Origin of disrupted OD flow
        - ``destination_id`` - String node ID of Destination of disrupted OD flow
        - ``origin_province`` - String name of Province of Origin node ID of disrupted OD flow
        - ``destination_province`` - String name of Province of Destination node ID of disrupted OD flow
        - ``no_access`` - Boolean 1 (no reroutng) or 0 (rerouting)
        - ``min/max_distance`` - Float value of estimated distance of OD journey before disruption
        - ``min/max_time`` - Float value of estimated time of OD journey before disruption
        - ``min/max_gcost`` - Float value of estimated travel cost of OD journey before disruption
        - ``new_cost`` - Float value of estimated cost of OD journey after disruption
        - ``new_distance`` - Float value of estimated distance of OD journey after disruption
        - ``new_path`` - List of string edge IDs of estimated new route of OD journey after disruption
        - ``new_time`` - Float value of estimated time of OD journey after disruption
        - ``dist_diff`` - Float value of Post disruption minus per-disruption distance
        - ``time_diff`` - Float value Post disruption minus per-disruption timee
        - ``min/max_tr_loss`` - Float value of estimated change in rerouting cost
        - ``industry_columns`` - Float values of all daily tonnages of industry columns along disrupted OD pairs
        - ``min/max_total_tons`` - Float values of total daily tonnages along disrupted OD pairs

    - Isolated OD scenarios - OD flows with no rerouting options in ``/results/failure_results/isolated_od_scenarios/``
        - ``edge_id`` - String name or list of failed edges
        - ``origin_province`` - String name of Province of Origin node ID of disrupted OD flow
        - ``destination_province`` - String name of Province of Destination node ID of disrupted OD flow
        - ``industry_columns`` - Float values of all daily tonnages of industry columns along disrupted OD pairs
        - ``min/max_total_tons`` - Float values of total daily tonnages along disrupted OD pairs

    - Rerouting scenarios - OD flows with rerouting options in ``/results/failure_results/rerouting_scenarios/``
        - ``edge_id`` - String name or list of failed edges
        - ``o_region`` - String name of Province of Origin node ID of disrupted OD flow
        - ``d_region`` - String name of Province of Destination node ID of disrupted OD flow
        - ``min/max_tr_loss`` - Float value of change in rerouting cost
        - ``min/max_total_tons`` - Float values of total daily tonnages along disrupted OD pairs

    - Min-max combined scenarios - Combined min-max results along each edge in ``/results/failure_results/minmax_combined_scenarios/``
        - ``edge_id`` - String name or list of failed edges
        - ``no_access`` - Boolean 1 (no reroutng) or 0 (rerouting)
        - ``min/max_tr_loss`` - Float values of change in rerouting cost
        - ``min/max_total_tons`` - Float values of total daily tonnages affected by disrupted edge

    - Shapefile min-max combined scenarios
        - ``edge_id`` - String name or list of failed edges
        - ``no_access`` - Boolean 1 (no reroutng) or 0 (rerouting)
        - ``min/max_tr_loss`` - Float values of change in rerouting cost
        - ``min/max_total_tons`` - Float values of total daily tonnages affted by disrupted edge
        - ``geometry`` - LineString geomtry of edges


Macroeconomic loss Analysis
---------------------------
Purpose:
    - Macroeconomic losses analysis due to edge failures in networks
        - To estimate economic impacts of flow isolations/disruptions
        - To understand the wider economic impacts of these disruptions

Execution:
    - Load data described in `Macroeconomic Data <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#macroeconomic-data-requirements>`_ and `OD matrices requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#od-matrices-requirements>`_
    - To create the multiregional input-output table for Argentina, run :py:mod:`atra.mrio.run_mrio`
    - To perform the loss analysis, run :py:mod:`atra.mria.run_mria`

Result:
    - Store the new multiregional input-output table in ``/data/economic_IO_tables/output_data/``
        - files ``IO_ARGENTINA.xlsx`` contain:
            - Sheetname ``T`` with the full multiregional table
            - Sheetname ``labels_T`` with the column and row labels of matrix ``T``
            - Sheetname ``FD`` with the final demand columns of the new table
            - Sheetname ``labels_FD`` with the column labels of matrix ``FD``
            - Sheetname ``ExpROW`` with the export to the Rest of the World columns of the new table
            - Sheetname ``labels_ExpROW`` with the column labels of matrix ``ExpROW``
            - Sheetname ``VA`` with the value added rows of the new table
            - Sheetname ``labels_VA`` with the row labels of matrix ``VA``
    - Store csv files in ``/results/economic_failure_losses/summarized/``
    - All summarized files have the following attributes:
        - ``edge_id`` - String edge IDs
        - ``total_losses`` - Value of the total economic losses due to the disruption of the corresponding edge ID
    - Store csv files in ``/results/economic_failure_losses/od_region_losses/``
    - All od_losses file have the following attributes:
        - ``edge_id`` - String edge IDs
        - ``region`` - String name of the region
        - ``dir_losses`` - Value of the direct losses due to the diruption of the corresponding edge ID in the corresponding region
        - ``total_losses`` - Value of the total losses due to the diruption of the corresponding edge ID in the corresponding region
        - ``ind_losses`` - Value of the indirect losses due to the diruption of the corresponding edge ID in the corresponding region


Combining Network Failure and Macroeconomic loss Results
--------------------------------------------------------
Purpose:
    - Combine macroeconomic loss estimates with rerouting losses

Execution:
    - Load data described in `Failure Analysis <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#failure-analysis>`_ and `Macroeconomic loss analysis <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#macroeconomic-loss-analysis>`_
    - Run :py:mod:`atra.analysis.economic_failure_combine_national`

Result:
    - Store csv files in ``/results/failure_results/minmax_combined_scenarios/``
    - Files with names ``single_edge_failures_minmax_national_{mode}_{x}_percent_disrupt.csv`` or ``single_edge_failures_minmax_national_{mode}_{x}_percent_disrupt_multi_modal.csv`` or ``single_edge_failures_minmax_national_{mode}_{x}_percent_modal_shift.csv`` contain
        - ``edge_id`` - String name or list of failed edges
        - ``no_access`` - Boolean 1 (no reroutng) or 0 (rerouting)
        - ``min/max_tr_loss`` - Float values of change in rerouting cost
        - ``min/max_total_tons`` - Float values of total daily tonnages affected by disrupted edge
        - ``min/max_econ_loss`` - Float values of total daily macroeconomic losses
        - ``min/max_econ_impact`` - Float values of sum of transport loss and macroeconomic loss

Estimating the bridge flows and failure losses
----------------------------------------------
Purpose:
    - Estimate the flows and failure losses on the national-roads bridges
    - This done after all road failure analysis is performed because bridges results are estimated through the road failures

Execution:
    - Run :py:mod:`atra.analysis.failure_estimation_bridges` 

Result:
    - Creates outputs for bridges similar to the ones explained in `Mapping Flows onto Networks <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#mapping-flows-onto-networks>`_
    - Creates outputs for bridges similar to the ones explained in `Combining Network Failure and Macroeconomic loss Results <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#combining-network-failure-and-macroeconomic-loss-results>`_

Adaptation
----------
Purpose:
    - Generate adaption scenarios/strategies and examine their costs, benefits, net present
      values and benefit-cost ratios
    - For roads and bridges, based on different types of hazards, road assets and
      climate-change conditions

Execution:
    - Load data described in `Topological network requirements <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/parameters.html#topological-network-requirements>`_, `Combining Network Failure and Macroeconomic loss Results <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/results.html#combining-network-failure-and-macroeconomic-loss-results>`_, and `Adaptation Options <https://argentina-transport-risk-analysis.readthedocs.io/en/latest/data.html#adaptation-options>`_
    - Common functions are in :py:mod:`atra.adaptation_options`
    - Run :py:mod:`atra.analysis.adaptation_analysis`

Result:
    - Store results as excel sheets in ``/results/adaptation_results/``
    - All adaptation results have the following attributes:
        - ``edge_id``/``bridge_id`` - string, edge or bridges IDs
        - ``hazard_type`` - string, names of hazard types
        - ``model`` - string, names of hazard models
        - ``climate_scenario`` - string, names of climate scenarios
        - ``year`` - integer, values of year of hazard climate models
        - ``width`` - float, edge widths
        - ``edge_length`` - float, edge lengths
        - ``min/max_depth`` - float, heights of hazard exposure - if flooding
        - ``min/max_exposure_percent`` - float, percent of edge length exposed to hazard
        - ``min/max_duration_wt`` - float, duration of disruption of edge
        - ``min/max_exposure_length`` - float, edge length exposed to hazard
        - ``risk_wt`` - float, weight given to estimating expected annual losses
        - ``dam_wt`` - float, weight given to estimating expected annual damage costs
        - ``min/max_econ_impact`` - float, minimum/maximum economic impact
        - ``min/max_benefit`` - float, minimum/maximum benefit
        - ``min/max_ini_adap_cost`` - float, minimum/maximum initial adaptation cost
        - ``min/max_tot_adap_cost`` - float, minimum/maximum total adaptation cost
        - ``min/max_bc_ratio`` - float, minimum/maximum benefit cost ratio
        - ``min/max_bc_diff`` - float, minimum/maximum benefit cost difference
        - Attributes specific to the roads or bridges


Processing outputs and plots
----------------------------
Purpose:
    - Several scripts are written to generate statistics and plots to process results
    - These codes are very specific to the kinds of data and outputs produced from the analysis
    - See the scripts with :py:mod:`atra.stats` and :py:mod:`atra.plot`