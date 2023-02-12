#!/bin/bash
if [[ ! ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi

mkdir -p simulations

conda_path=$(conda info --base)
source "$conda_path/etc/profile.d/conda.sh"
conda activate ChangeSim

source "$PWD/config"

types=()
corpora=()
targets=()

while getopts ':vwshp:' OPTION; do
  case "$OPTION" in
    v)
      printf "\nVUAMC\n"
      python source/preprocessing/process_vuamc.py "$vuamc_path" --min "$min_base" "$min_other" --max "$max_all"
      types+=("metaphor")
      corpora+=("$vuamc_path/VUAMC_preprocessed_new.csv")
      targets+=("$vuamc_path/possible_targets_metaphor_$min_base-${min_other}_['NOUN', 'VERB', 'ADJ'].csv")
      ;;
    s)
      printf "\nsemcor\n"
      python source/preprocessing/process_semcor.py "$semcor_path" --min "$min_base" "$min_other" --max "$max_all"
      corpora+=("$semcor_path/semcor_preprocessed_new.csv")
      for ((j=0;j<"${#semcor_types[@]}";++j)); do
        types+=("${semcor_types[j]}")
        targets+=("$semcor_path/possible_targets_${semcor_types[j]}_$min_base-${min_other}_['NOUN', 'VERB', 'ADJ'].csv")
      done
      ;;
    w)
      printf "\nwimcor\n"
      python source/preprocessing/process_wimcor.py "$wimcor_path" --min "$min_base" "$min_other"
      types+=("metonymy")
      corpora+=("$wimcor_path/wimcor_preprocessed_new.csv")
      targets+=("$wimcor_path/possible_targets_metonymy_$min_base-$min_other.csv")
      ;;
    h)
      printf "Script for change simulation. \n
      bash simulation.sh [-v] [-s] [-w] \n
      other settings in config"
      ;;
    ?)
      echo "script usage: bash simulation.sh [-v] [-s] [-w]" >&2
      exit 1
      ;;
  esac
done

no_types=${#types[@]}

for ((j=0;j<"$no_types";++j)); do
  echo "${types[j]}"
  for ((i=0;i<"$rounds"; ++i)); do
      python source/simulation/simulator_copy.py "${types[j]}" -c "${corpora[@]}" -t "${targets[j]}" -n "$no_changes" -m "$mode"
  done
done
