#!/bin/bash
if [[ ! ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi

source "$PWD/config"

process_vuamc=0
process_semcor=0
process_wimcor=0

while getopts ':vwshnu' OPTION; do
  case "$OPTION" in
    v)
      process_vuamc=1
      ;;
    s)
      process_semcor=1
      ;;
    w)
      process_wimcor=1
      ;;
    u)
      conda env update --name ChangeSim --file simulation_env.yml --prune
      conda_path=$(conda info --base)
      sed -i '/raise StopIteration/d' "$conda_path/envs/ChangeSim/lib/python3.1*/site-packages/pattern/text/__init__.py"
      ;;
    n)
      conda env create -f simulation_env.yml
      conda_path=$(conda info --base)
      sed -i '/raise StopIteration/d' "$conda_path/envs/ChangeSim/lib/python3.1*/site-packages/pattern/text/__init__.py"
      ;;
    h)
      printf "Script to download and pre-process all the data, and set up the environment. \n
      bash preprocessing.sh [-u] [-n] [-vsw]"
      ;;
    ?)
      echo "script usage: bash preprocessing.sh [-u] [-n] [-vsw]" >&2
      exit 1
      ;;
  esac
done

conda_path=$(conda info --base)
source "$conda_path/etc/profile.d/conda.sh"
conda activate ChangeSim

if [[ ! -f $vuamc_path/VUAMC.xml ]]; then
  echo "Downloading VUAMC corpus..."
  wget -O "$vuamc_path/VUAMC.xml" "https://ota.bodleian.ox.ac.uk/repository/xmlui/bitstream/handle/20.500.12024/2541/VUAMC.xml?sequence=7&isAllowed=y"
fi
if [[ ! -d $wimcor_path ]]; then
  echo "Downloading wimcor corpus..."
  wget https://kevinalexmathews.github.io/files/wimcor-v1.1.tar.gz
  tar -xf wimcor-v1.1.tar.gz -C data/
  rm wimcor-v1.1.tar.gz
fi

if [[ $nltk_path == "" ]]; then
  nltk_path="$HOME/nltk_data"
else
  export NLTK_DATA="$nltk_path"
  mkdir -p "$nltk_path"
  echo "Downloading nltk to $nltk_path"
fi

python -m nltk.downloader semcor wordnet universal_tagset punkt averaged_perceptron_tagger
if [[ ! -f $nltk_path/taggers/universal_tagset/en-vuamc.map ]]; then
  cp data/VUAMC/en-vuamc.map "$nltk_path/taggers/universal_tagset/en-vuamc.map"
fi

if [[ $process_wimcor -eq 1 ]]; then
  python source/preprocessing/reformat_wimcor.py "$wimcor_path"
  python source/preprocessing/process_wimcor.py "$wimcor_path" --process
fi
if [[ $process_semcor -eq 1 ]]; then
  mkdir -p "$semcor_path"
  python source/preprocessing/process_semcor.py "$semcor_path" --process
fi
if [[ $process_vuamc -eq 1 ]]; then
  python source/preprocessing/process_vuamc.py "$vuamc_path" --process
fi
