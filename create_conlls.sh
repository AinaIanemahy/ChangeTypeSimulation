#!/bin/bash
if [[ ! ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi
source "$PWD/config"

THESIS=$PWD

if [[ (-d "$semcor_path") && (-d "$wimcor_path") && (-d "$vuamc_path") ]]; then
  if [[ ! -f "$semcor_path/semcor_preprocessed_new.conll" ]]; then
    python source/simulation/create_conll.py en "$semcor_path/semcor_preprocessed_new.csv" -p "$stanza_path"
  fi
  if [[ ! -f "$wimcor_path/wimcor_preprocessed_new.conll" ]]; then
    python source/simulation/create_conll.py en "$wimcor_path/wimcor_preprocessed_new.csv" -p "$stanza_path"
  fi
  if [[ ! -f "$vuamc_path/VUAMC_preprocessed_new.conll" ]]; then
    python source/simulation/create_conll.py en "$vuamc_path/VUAMC_preprocessed_new.csv" -p "$stanza_path"
  fi
else
  echo "Run preprocessing first."
fi