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

The economic model uses [GAMS](https://www.gams.com/) (General Algebraic Modeling System) via
its python API. GAMS provide [installation and
licensing](https://www.gams.com/latest/docs/UG_MAIN.htm) instructions.


## Configuration

The location of data and output files are configured by a `config.json` file. Copy
`config.template.json` and edit the file path details to locate the files on your system.

Note that on Windows, you will need to use double backslashes (`\\`) in the file paths, for
example:

    "data": "C:\\Users\\Username\\projects\\vtra\\data"


## Development notes

### Notebooks in git

Make sure not to commit data inadvertently if working with jupyter notebooks. Suggest using
[nbstripout](https://github.com/kynan/nbstripout) to automatically strip output.

Install git hooks to filter notebooks when committing to git:

    cd /path/to/argentina-transport
    nbstripout --install


Data processing and model scripts for Argentina Transport Risk Analysis.

## Code organisation

- `src` contains project-specific processing, analysis and visualisation scripts

## Setup

To add the packages in `src` to your python environment, run:

```
python setup.py develop
```

To point the scripts to the shared folder locations:
- copy `config.template.json` to `config.json`
- edit `config.json` to provide the paths to your working copy of the OneDrive shared
  directories (scripts may assume that file locations within the shared folders are consistent)
  - `incoming_data`: /incoming_data
  - `data`: /data
  - `figures`: /figures
  - `output`: /results


## Acknowledgements

This project has been developed by Oxford Infrastructure Analytics as part of a project funded
by the World Bank.

All code is copyright Oxford Infrastructure Analytics, licensed MIT (see the `LICENSE` file for
details) and is available on GitHub at
[oi-analytics/argentina-transport](https://github.com/oi-analytics/argentina-transport).
