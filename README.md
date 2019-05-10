# Argentina Transport Risk World Bank project

[![Documentation Status](https://readthedocs.org/projects/argentina-transport-risk-analyis/badge/?version=latest)](https://argentina-transport-risk-analyis.readthedocs.io/en/latest/?badge=latest)

Data processing and model scripts for Argentina Transport Risk Analysis

## Code organisation

- `scripts` contains project-specific processing, analysis and visualisation scripts
- `src` contains python packages for general OIA use

## Setup

To add the packages in `src` to your python environment, run:

```
python setup.py develop
```

To point the scripts to the shared folder locations:
- copy `config.template.json` to `config.json`
- edit `config.json` to provide the paths to your working copy of the OneDrive shared
  directories (scripts may assume that file locations within the shared folders are consistent)
  - `incoming_data`: 302 Argentina/C Incoming data
  - `data`: 302 Argentina/D Work Processes/Argentina/data
  - `figures`: 302 Argentina/D Work Processes/Argentina/figures


## Acknowledgements

This project has been developed by Oxford Infrastructure Analytics as part of a project funded
by the World Bank.

All code is copyright Oxford Infrastructure Analytics, licensed MIT (see the `LICENSE` file for
details) and is available on GitHub at
[oi-analytics/argentina-transport](https://github.com/oi-analytics/argentina-transport).
