# -*- coding: utf-8 -*-
"""Assess national adaptation options
"""
import os
import sys
import numpy as np
from atra.adaptation_options import *

def main():
    """
    (i) estimated cost to upgrade to a climate-resilient bituminous 2L 
        (applied to unpaved, gravel and bituminous 2L roads), 
    (ii) estimated cost to upgrade to a climate-resilient bituminous 4L 
        (applied to bituminous 4L roads), 
    (iii) estimated cost to upgrade to a climate-resilient concrete 2L 
        (applied to concrete 2L roads), 
    (iv) estimated cost to upgrade to a climate-resilient concrete 4L 
        (applied to concrete 4L roads).
    """
    read_from_file = False
    if len(sys.argv) == 2:
        if sys.argv[1] == '--read_from_file':
            read_from_file = True

    if read_from_file:
        print('Reading param values from file')
    else:
        print('Running with fixed param values,  --read_from_file to use file')

    config = load_config()
    data_path = config['paths']['data']
    calc_path = config['paths']['calc']
    output_path = config['paths']['output']

    adapt_results = os.path.join(output_path,'adaptation_results')
    if os.path.exists(adapt_results) == False:
        os.mkdir(adapt_results)

    duration_list = np.arange(10,110,10)
    discount_rate = 12
    growth_rates = np.arange(-2,4,0.2)

    modes = ['road','bridge']
    result_types = ['combined_climate','hazard_and_climate']
    start_year = 2016
    end_year = 2050
    min_periodic_year = 4
    max_periodic_year = 8

    for result_type in result_types:
        adapt_results = os.path.join(output_path,'adaptation_results',result_type)
        if os.path.exists(adapt_results) == False:
            os.mkdir(adapt_results)
        
        for dur in duration_list:
            for growth_rate in growth_rates:
                for file_id in modes:
                    run_adaptation_calculation(
                        file_id, data_path, output_path,result_type, 
                        duration_max=dur, 
                        discount_rate=discount_rate,
                        growth_rate=round(growth_rate,1),
                        start_year=start_year,
                        end_year=end_year,
                        min_period=min_periodic_year,
                        max_period=max_periodic_year,  
                        read_from_file=read_from_file)



if __name__ == '__main__':
    main()
