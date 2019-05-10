# -*- coding: utf-8 -*-
"""Assess national adaptation options
"""
import os
import sys
from atra.adaptation_options import *

def main():
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

    duration_list = [10,20,30]
    discount_rate = 10
    growth_rate = 2.9
    modes = ['road','bridge']
    # modes = ['bridge']

    for dur in duration_list:
        for file_id in modes:
            run_adaptation_calculation(
                file_id, data_path, output_path, duration_max=dur, discount_rate=discount_rate, growth_rate=growth_rate, read_from_file=read_from_file)



if __name__ == '__main__':
    main()
