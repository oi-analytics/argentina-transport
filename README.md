# Argentina Transport Risk World Bank project

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
