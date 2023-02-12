#!/bin/bash
if [[ ! ${PWD##*/} == 'LSCDetection' ]]; then
    echo "Wrong working directory. Switch to LSCDetection/"
    exit 1
fi

source "$PWD/config"

conda_path=$(conda info --base)
source "$conda_path/etc/profile.d/conda.sh"
conda activate CDSystems

mkdir -p "$simulations"/lemma/OP
mkdir -p "$simulations"/lemma/results

for time in "${times[@]}"; do
    prefix="$date-$time"
    python representations/sgns.py "$simulations"/lemma/"$prefix"_corpust1_lemma.txt "$simulations"/lemma/"$prefix"_corpust1 10 300 1 None 15 5
    python representations/sgns.py "$simulations"/lemma/"$prefix"_corpust2_lemma.txt "$simulations"/lemma/"$prefix"_corpust2 10 300 1 None 15 5
    python alignment/map_embeddings.py --normalize unit center --init_identical --orthogonal "$simulations"/lemma/"$prefix"_corpust1 "$simulations"/lemma/"$prefix"_corpust2 "$simulations"/lemma/OP/"$prefix"_corpust1_OP "$simulations"/lemma/OP/"$prefix"_corpust2_OP # align matrices by Orthogonal Procrustes
    python measures/cd.py -s "$simulations"/"$prefix"_targets.csv "$simulations"/lemma/OP/"$prefix"_corpust1_OP "$simulations"/lemma/OP/"$prefix"_corpust2_OP "$simulations"/lemma/results/"$prefix"_CD.tsv
    python measures/lnd.py -s "$simulations"/lemma/"$prefix"_targets.csv "$simulations"/lemma/OP/"$prefix"_corpust1_OP "$simulations"/lemma/OP/"$prefix"_corpust2_OP "$simulations"/lemma/results/"$prefix"_LND.tsv 25
done

