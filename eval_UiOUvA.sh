#!/bin/bash
if [[ ! ${PWD##*/} == 'ChangeTypeSimulation' ]]; then
    echo "Wrong working directory. Switch to ChangeTypeSimulation/"
    exit 1
fi

source "$PWD/config"

conda_path=$(conda info --base)
source "$conda_path/etc/profile.d/conda.sh"
conda activate CDSystems

for time in "${times[@]}"; do
    prefix="$date-$time"
    python detection_systems/semeval2020/code/bert/collect.py detection_systems/semeval2020/bert/config "$simulations"/token/"$prefix"_corpust1_token.txt "$simulations"/"$prefix"_targets.csv "$simulations"/token/"$prefix"_corpust1_tokenb
    python detection_systems/semeval2020/code/bert/collect.py detection_systems/semeval2020/bert/config "$simulations"/token/"$prefix"_corpust2_token.txt "$simulations"/"$prefix"_targets.csv "$simulations"/token/"$prefix"_corpust2_tokenb
    python detection_systems/semeval2020/code/cosine.py -t "$simulations"/"$prefix"_targets.csv -i0 "$simulations"/token/"$prefix"_corpust1_tokenb.npz -i1 "$simulations"/token/"$prefix"_corpust2_tokenb.npz > "$simulations"/token/predictions/"$prefix"_cosine_change.txt
    python detection_systems/semeval2020/code/class.py "$simulations"/token/predictions/"$prefix"_cosine_change2.txt "$simulations"/token/predictions/"$prefix"_cosine_change2_class.txt 0.004
    python detection_systems/semeval2020/code/distance.py "$simulations"/"$prefix"_targets.csv "$simulations"/token/"$prefix"_corpust1_tokenb.npz "$simulations"/token/"$prefix"_corpust2_tokenb.npz "$simulations"/token/predictions/"$prefix"_apd2.txt
    python detection_systems/semeval2020/code/class.py "$simulations"/token/predictions/"$prefix"_apd2.txt "$simulations"/token/predictions/"$prefix"_apd2_class.txt 0.4
done

