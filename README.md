# Argentina Transport Risk World Bank project

[![Documentation Status](https://readthedocs.org/projects/argentina-transport-risk-analysis/badge/?version=latest)](https://argentina-transport-risk-analysis.readthedocs.io/en/latest/?badge=latest)

## Requirements

### Python and libraries

Python version 3.6 is required to run the scripts in this project. We suggest using
[miniconda](https://conda.io/miniconda.html) to set up an environment and manage library
dependencies.

Create a conda environment from the `environment.yml` definition:

    conda env create -f environment.yml
    conda install python-igraph

See http://igraph.org/python/ for instructions on Windows installation of `python-igraph`.

Activate the environment:

    conda activate argentina-transport

Set up the `atra` package (this project) for development use:

    python setup.py develop


### GAMS

The macroeconomic loss model uses [GAMS](https://www.gams.com/) (General Algebraic Modeling
System) via its python API. GAMS provide [installation and
licensing](https://www.gams.com/latest/docs/UG_MAIN.htm) instructions.


## Configuration

The location of data and output files are configured by a `config.json` file.
To point the scripts to the shared folder locations:
- copy `config.template.json` to `config.json`
- edit `config.json` to provide the paths to your working copy of your system
  directories (scripts may assume that file locations within the shared folders are consistent)
  - `incoming_data`: /incoming_data
  - `data`: /data
  - `figures`: /figures
  - `output`: /results

Note that on Windows, you will need to use double backslashes (`\\`) in the file paths, for
example:

    "data": "C:\\Users\\Username\\projects\\atra\\data"


## Acknowledgements

This project has been developed by Oxford Infrastructure Analytics as part of a project funded
by the World Bank.

All code is copyright Oxford Infrastructure Analytics, licensed MIT (see the `LICENSE` file for
details) and is available on GitHub at
[oi-analytics/argentina-transport](https://github.com/oi-analytics/argentina-transport).
