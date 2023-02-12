# Change Type Simulations

The code in this repository can be used to simulate different types of change (at this point metaphor, metonymy, generalization, and specialization).

This repository contains the following directories:
- data: data and code for the construction of the corpus
- detection_systems: the detection systems after running ``setup_systems.sh``
- nltk_data (potentially, if defined in the config)
- source: the code base

## Setup

To download the corpus data and set up the simulation environment run

``bash preprocessing.sh [-n] [-u]``

To set up the change detection systems, and a conda environment to run them in run

``bash setup_systems.sh [-n] [-u]``

The flags can be used to specify whether the respective conda environment should be initialized (`-n`) or updated (`-u`).

## Pre-processing

Use the script ``preprocessing.sh`` or follow the steps as described below. 

If you run ``preprocessing.sh``, make sure to check all the paths in ``config`` beforehand.
Also activate the conda environment

`conda activate ChangeSim`

and download all necessary NLTK packages:

`python -m nltk.downloader universal_tagset punkt averaged_perceptron_tagger`

### VUAMC
The corpus can be downloaded from [the Oxford Text Archive](https://ota.bodleian.ox.ac.uk/repository/xmlui/handle/20.500.12024/2541). We only need
the xml version of the corpus:

``wget -P data/VUAMC/ -O VUAMC.xml "https://ota.bodleian.ox.ac.uk/repository/xmlui/bitstream/handle/20.500.12024/2541/VUAMC.xml?sequence=7&isAllowed=y"``

The pos mapping function uses the file `vuamc.map`. To set up the mapping function, you have to download 
`taggers.universal_tagset` from `nltk` like

`python -m nltk.downloader universal_tagset`

Then place `data/VUAMC/en-vuamc.map` in `nltk_data/taggers/universal_tagset/`.

`cp data/VUAMC/en-vuamc.map ~/nltk_data/taggers/universal_tagset/en-vuamc.map`

To run the preprocessing call

`python source/preprocessing/process_vuamc.py data/VUAMC --process`

### SEMCOR

Download the corpora from NLTK:

`python -m nltk.downloader semcor wordnet`

`mkdir -p "$semcor_path"`

Preprocess the data:

`python source/preprocessing/process_semcor.py data/semcor --process`

### WiMCor

Download the wimcor corpus to `data` from https://kevinalexmathews.github.io/files/wimcor-v1.1.tar.gz; extract the files.

Mitigate encoding errors in the data:

`python source/preprocessing/reformat_wimcor.py "data/wimcor-v1.1/dataset/xml/"`

Preprocess the data:

`python source/preprocessing/process_wimcor.py "data/wimcor-v1.1/dataset/xml/" --process`

## Simulation

Use the script ``simulation.sh`` or follow the steps as described below. If you run ``simulation.sh``, make sure to check all the paths in ``config`` beforehand.
Additionally, you can set the following parameters in the config:

- rounds: the number of rounds to simulate per change type
- min_base: the minimal number of occurrences of the original sense
- min_other: the minimal number of occurrences of the new sense
- max_all: the maximal total number of occurrences of a target
- no_changes: the number of changes to simulate per type
- mode: the mode of simulation (base_other or frequency)
- semcor_types: the types you want to simulate in SemCor ("taxonomy-hypernym" "taxonomy-hyponym")

If you wish to simulate a change from a new corpus, make sure to format the corpus the right way, then refer to Simulation below.

### Retrieve Target Words

Retrieve possible targets, you can set min values and also max values:

`python source/preprocessing/process_wimcor.py "data/wimcor-v1.1/dataset/xml/" --min 45 20 [-pos ]`

`python source/preprocessing/process_semcor.py data/semcor --min 45 20`

`python source/preprocessing/process_vuamc.py data/VUAMC --min 45 20`

### Simulation

List the types first, then list the corpora behind `-c` and the lists of possible targets behind `-t`.
You can also specify `-n NUMBER` the number of changes to simulate per list of targets and `-m MODE` the mode.
E.g., to run the simulation with the demo corpus type:

``python source/simulation.py "met" -c data/demo/corpus.csv -t data/demo/targets.csv [-n NUMBER] [-m MODE]``

## Create the CoNLL, Token and Lemma Files

First run `create_conll.sh` to create ConLL files of all three corpora. If you only want one corpus or a different one run
`python source/simulation/create_conll.py PATH/TO/FILE -l LANGUAGE`.

Concatenate all CoNLL files into one:

`cat FILE1 FILE2 FILE3 > data/all.conll`

Then run `python source/simulation/apply_simulation.py data/all.conll -s simulations/` to apply all simulations stored in
the folder `simulations/`.

## Retrieve Scores

Specify the date of the simulations in the `config` (the first part prefix of the simulation files). Also specify the list
of times of the simulations (the second part prefix of the simulation files). Check the `simulations` variable in the `config`.
For each of the systems there is a separate evaluation file. Run them one after the other.

`bash eval_GramProfiles.sh`

`bash eval_UiOUvA.sh`

`bash eval_SGNS.sh`