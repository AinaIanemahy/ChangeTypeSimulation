# /bin/env python3
# coding: utf-8

import pandas as pd
import argparse
import os
import conllu
from pattern.text import en


def replace(sentence, replacement):
    mapping = {
        '1': '1sg',
        '2': '2sg',
        '3': '3sg'
    }

    def verb_map(value):
        try:
            return mapping[value]
        except KeyError:
            return None

    def replace_form():
        if word['upos'] == 'NOUN':
            if word['feats']['Number'] == 'Plur':
                return en.pluralize(replacement["new_lemma"])
        elif word['upos'] == 'VERB':
            if word['feats']['VerbForm'] == 'Inf':
                return en.verbs.conjugate(replacement["new_lemma"], 'inf')
            if word['feats']['VerbForm'] == 'Part' or word['feats']['VerbForm'] == 'Ger':
                if len(word['feats']) > 1 and word['feats']['Tense'] == 'Past':
                    return en.verbs.conjugate(replacement["new_lemma"], 'ppart')
                return en.verbs.conjugate(replacement["new_lemma"], 'part')
            if 'Person' not in word['feats'] or ('Number' in word['feats'] and word['feats']['Number'] == 'Plur')\
                    or ('Tense' in word['feats'] and word['feats']['Tense'] == 'Past'):
                if 'Tense' in word['feats'] and word['feats']['Tense'] == 'Past':
                    return en.verbs.conjugate(replacement["new_lemma"], 'past')
                return en.verbs.conjugate(replacement["new_lemma"], 'pl')
            new_form = en.verbs.conjugate(replacement["new_lemma"], verb_map(word['feats']['Person']))
            if new_form:
                return new_form
        elif word['upos'] == 'ADJ':
            if word['feats']['Degree'] == 'Cmp':
                return en.comparative(replacement["new_lemma"])
            elif word['feats']['Degree'] == 'Sup':
                return en.superlative(replacement["new_lemma"])
        return replacement["new_lemma"]

    try:
        word = sentence.filter(lemma=replacement["old_lemma"])[0]
    except IndexError:
        try:
            word = sentence.filter(id=int(replacement["word_id"])+1)[0]
        except IndexError:
            return sentence
    word["lemma"] = replacement["new_lemma"]
    new_form = replace_form()
    sentence.metadata['text'] = sentence.metadata['text'].replace(word["form"], new_form)
    word["form"] = new_form
    return sentence


def generate_corpus(sen_ids, conll, replace_ids):
    for sentence in conll:
        conll_id = sentence.metadata["sent_id"]
        if sen_ids["sentence_id"].isin([conll_id]).any():
            if replace_ids["sentence_id"].isin([conll_id]).any():
                yield replace(sentence, replace_ids[replace_ids["sentence_id"] == conll_id].iloc[0])
            yield sentence


def main():
    parser = argparse.ArgumentParser(prog="Realize the simulation using the corpus conll files and some simulations.")
    parser.add_argument("corpus", type=str, help="path/to/the/corpus_file.conll")
    parser.add_argument("-s", dest="simulations", type=str, help="path/to/simulations")

    args = parser.parse_args()
    try:
        conll = conllu.parse(open(args.corpus).read())
    except FileNotFoundError as er:
        print(er)
        exit(f"{args.corpus} could not be loaded.")
    for filename in os.listdir(args.simulations):
        file = os.path.join(args.simulations, filename)
        if os.path.isfile(file) and "sentences" in filename:
            sen_ids = pd.read_csv(file, dtype=str, index_col=False)
            replace_ids = sen_ids[~ sen_ids['word_id'].isna()]
            with open(f"{args.simulations}/conll/{filename.replace('sentences', 'corpus')[:-4]}.conll", 'w') as conll_file, \
                    open(f"{args.simulations}/token/{filename.replace('sentences', 'corpus')[:-4]}_token.txt", 'w') as token,\
                    open(f"{args.simulations}/lemma/{filename.replace('sentences', 'corpus')[:-4]}_lemma.txt", 'w') as lemma:
                print(filename)
                for sentence in generate_corpus(sen_ids, conll, replace_ids):
                    conll_file.writelines(sentence.serialize())
                    token.write(f"{sentence.metadata['text']}\n")
                    lemma.write(f"{' '.join([token['lemma'] for token in sentence])}\n")
        else:
            print(f"Did not load {filename}.")


if __name__ == "__main__":
    main()
