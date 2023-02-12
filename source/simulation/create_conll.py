# /bin/env python3
# coding: utf-8

import stanza
from tqdm import tqdm
from stanza.utils.conll import CoNLL
import pandas as pd
import argparse


def main():
    parser = argparse.ArgumentParser(prog="Create conll files from corpus csv with 'text' and 'sen_id' column.")
    parser.add_argument("corpus", type=str, help="path/to/the/corpus_file.csv")
    parser.add_argument("-p", dest="stanza_path", default="package_data/stanza", type=str, help="path/to/stanza/dir")
    parser.add_argument("-l", dest="language", default="en", type=str, help="The language of the corpus (default en).")

    args = parser.parse_args()

    try:
        corpus = pd.read_csv(args.corpus, index_col=0)
    except FileNotFoundError as er:
        print(er)
        exit(f"{args.corpus} could not be loaded.")

    nlp = stanza.Pipeline(args.language, dir=args.stanza_path, processors="tokenize,mwt,pos,lemma,depparse")

    with open(f"{args.corpus[:-4]}.conll", 'w', encoding="utf-8") as output_file:
        for sen_id, sen_table in tqdm(corpus.groupby('sentence_id')):
            sen = [f"# sent_id = {sen_id}"]
            text = " ".join(sen_table["text"].astype(str))
            sen.append(f"# text = {text}")
            doc = nlp(text.strip())
            dicts = doc.to_dict()
            conll = CoNLL.convert_dict(dicts)
            for sentence in conll:
                for token in sentence:
                    sen.append("\t".join(token))
            sen.append("\n")
            output_file.writelines("\n".join(sen))


if __name__ == "__main__":
    main()
