# Data science on Gypsy EU4 

This project explores the Gypsy mod for EU4 from a data science perspective. You can use ipython jupyter notebooks for detailed experiments as well as python script to generate desired results. Covered features:

- Conversion of idea and policy files into yaml format (better readability)
- Build generation based on input weights of effects of your wish.
- Excel generation of policy matrix

More is coming....

## Prerequisites

All the default data comes with this repository so you only need to install used python modules via [pip](https://pip.pypa.io/en/stable/).

```bash
pip install -r requirements.txt 
```

## Usage

### Convert idea or policy files into yaml

This step is mainly necessary only if you are using a different idea or policy files but the ones we used for the experiments and computations. Common output folder is `data/processed/...`

```bash
# Idea file/folder conversion

# python scripts/process_ideas.py -help

python scripts/process_ideas.py -i {PATH_TO_IDEA_FOLDER} -o {OUTPUT_PATH}

# Example
python scripts/process_ideas.py -i data/raw/gypsy/common/ideas -o data/processed/gypsy-1-36-1

# Policy file/folder conversion
# python scripts/process_policies.py -help

python scripts/process_policies.py -i {PATH_TO_POLICY_FOLDER} -o {OUTPUT_PATH}

#Example
python scripts/process_policies.py -i data/raw/gypsy/common/policies -o data/processed/gypsy-1-36-1

```

### Generate policy dependency table

Script to generate policy table.

```bash
# python scripts/gen_policy_table.py -help

python scripts/gen_policy_table.py -i {LIST_OF_IDEA_FILES} -p {LIST_OF_POLICY_FILES}
# Example

python scripts/gen_policy_table.py -i data/processed/gypsy-1-36-1/00_basic_ideas.yaml data/processed/gypsy-1-36-1/00_flogi_ideas.yaml -p data/processed/gypsy-1-36-1/Idea_Variation_policies.yaml
```

### Generate builds by effect weights

You can either use the script to get N best builds per build size of you can use playbook `notebooks/template_build_search.ipynb` to start your research (make a copy of the template). In case of the script way, wou need to craft your own weights using `data/external/weights/weights_template.yaml`. Make an copy and adjust the numbers according your wish, then run the script. There are many parameters how to mainly speed up the process, but to start with, only the weights file is required combined with the religion and government of your choosing.

```bash
# python ./scripts/gen_builds.py -help

python ./scripts/gen_builds.py -w {PATH_TO_WEIGHTS_FILE} -r {RELIGION} -g {GOVERNMENT}

# Example 

python ./scripts/gen_builds.py -w data/external/weights/imperial_army.yaml -r protestant0 -g horde0
```

Other script options:

```
[-e] ... Use this flag if you with to use imperial_ambition instead of imperialism
[-p] {0-100} ... set this value if you wish to skip the questionary for potential filtering
[--exp-from] {4-5} ... from how many ideas the scrip uses only top M and random N best build to expand on (speed up)
[--exp-top] M
[--exp-rand] N
```