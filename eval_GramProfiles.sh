#! /bin/bash
# modeled after the full profiling pipeline of semchange-profiling to loop over multiple simulations

if [[ ! ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi

source "$PWD/config"

conda_path=$(conda info --base)
source "$conda_path/etc/profile.d/conda.sh"
conda activate CDSystems

for time in "${times[@]}"; do
  # First, we read a CONLL file and dumps frequencies
  # for morphological and syntax properties
  # of the target words into JSON files
  echo "$time"
  prefix="$date-$time"
  TARGET="$simulations"/"$prefix"_targets.csv  # List of target words, one per line
  CONLL0="$simulations"/conll/"$prefix"_corpust1.conll  # Earlier corpus, processed into CONLL format
  CONLL1="$simulations"/conll/"$prefix"_corpust2.conll  # Later corpus, processed into CONLL format

  OUTJSONS="$simulations"/conll/output/jsons
  mkdir -p ${OUTJSONS}

  OUTSEPARATE="$simulations"/conll/output
  mkdir -p ${OUTSEPARATE}

  echo "Extracting grammatical profiles..."
  python3 "$simulations"/detection_systems/semchange-profiling/collect_ling_stats.py -i ${CONLL0} -t ${TARGET} -o ${OUTJSONS}/"$prefix"_corpust1 &
  python3 "$simulations"/detection_systems/semchange-profiling/collect_ling_stats.py -i ${CONLL1} -t ${TARGET} -o ${OUTJSONS}/"$prefix"_corpust2
  echo "Done extracting grammatical profiles"

  # Now, we produce separate change predictions based on morphological and syntactic profiles

  echo "Producing morphological predictions..."
  python3 "$simulations"/detection_systems/semchange-profiling/compare_ling.py --input1 ${OUTJSONS}/"$prefix"_corpust1_morph.json --input2 ${OUTJSONS}/"$prefix"_corpust2_morph.json --output ${OUTSEPARATE}/"$prefix"_morph --filtering 5 --separation 2step

  echo "Producing syntactic predictions..."
  python3 "$simulations"/detection_systems/semchange-profiling/compare_ling.py --input1 ${OUTJSONS}/"$prefix"_corpust1_synt.json --input2 ${OUTJSONS}/"$prefix"_corpust2_synt.json --output ${OUTSEPARATE}/"$prefix"_synt --filtering 5 --separation yes
  echo "Separate morphological and syntactic predictions produced"

  # Finally, we merge them into averaged predictions
  # (for binary and graded change detection tasks)

  for task in binary graded
  do
      echo "Producing averaged predictions for ${task}..."
      python3 detection_systems/semchange-profiling/merge.py -i1 ${OUTSEPARATE}/"$prefix"_morph_${task}.tsv -i2 ${OUTSEPARATE}/"$prefix"_synt_${task}.tsv > ${OUTSEPARATE}/"$prefix"_combined_${task}.tsv
  done

done
