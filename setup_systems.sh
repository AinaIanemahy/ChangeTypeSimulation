#!/bin/bash
if [[ ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    THESIS=$PWD
    cd detection_systems/  || return
else
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi

while getopts ':un' OPTION; do
  case "$OPTION" in
    u)
      conda env update --name CDSystems --file detection_env.yml --prune
      ;;
    n)
      conda env create -f detection_env.yml
      ;;
    ?)
      echo "script usage: setup_systems.sh [-n] [-u]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d semchange-profiling ]]; then
  echo "Downloading semchange-profiling..."
  git clone https://github.com/glnmario/semchange-profiling
  cp changed_files/stanza_process.py semchange-profiling/stanza_process.py
fi
if [[ ! -d semeval2020 ]]; then
  echo "Downloading semeval2020..."
  git clone https://github.com/akutuzov/semeval2020
  mkdir -p semeval2020/models/elmo semeval2020/models/bert-base-uncased
  # get elmo
  cd semeval2020/models/elmo || exit
  wget http://vectors.nlpl.eu/repository/20/209.zip
  unzip 209.zip
  rm 209.zip
  # get bert
  cd .. || exit
  python $THESIS/source/download_bert.py "$THESIS/detection_systems/semeval2020/models/bert-base-uncased"
  echo "$PWD/bert-base-uncased 13 768" > config
  cd "$THESIS/detection_systems" || exit
fi
if [[ ! -d LSCDetection ]]; then
  echo "Downloading LSCDetection..."
  git clone https://github.com/Garrafao/LSCDetection
  cp detection_systems/cd.py detection_systems/LSCDetection/measures/cd.py
  cp detection_systems/lnd.py detection_systems/LSCDetection/measures/lnd.py
  cp detection_systems/sgns.py detection_systems/LSCDetection/representations/sgns.py
fi
