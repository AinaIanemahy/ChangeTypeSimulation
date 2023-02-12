"""
This module is part of the preprocessing. It imports SemCor from NLTK and saves it as a pre-processed csv.
The function retrieve_possible_targets gives a list of possible target words and saves them to csv.
"""

import numpy as np
import pandas as pd
from abc import ABC
from Processor import Processor
from nltk.corpus.reader import wordnet
from nltk.corpus import semcor as sc
from nltk.corpus import wordnet as wn
import argparse
from tqdm import tqdm


class SemcorProcessor(Processor, ABC):

    def __init__(self, file_path: str | None = None, process_data: bool = True):
        # because SemCor is imported from NLTK I do not need input data, therefore no path should be given if
        # process_data is True---and vice versa
        if (file_path is not None) == process_data:
            raise ValueError("Either give a file_path or set process_data to True, not both.")
        print("Loading data...")
        super().__init__(file_path, process_data=process_data)
        if process_data:
            print("Adding lemmas, POS, and synsets.")
            self.corpus = self.add_punct_pos()
            self.corpus = self.add_lemma_to_closed()
            self.corpus = self.add_lemma_to_open()
            self.corpus = self.retrieve_synsets()
            self.corpus = self.retrieve_hypernyms()
            self.corpus = self.retrieve_hyponyms()
            del self.corpus["synset"]

    def iterate_element_tree(self):
        print("Processing NLTK...")
        # "both" to include both POS tags and sem annotations
        for sentence_id, sentence in enumerate(tqdm(sc.tagged_sents(tag="both"))):
            i = 0
            for chunk in sentence:
                row = self.convert_chunk(chunk)
                row["sentence_id"] = "_".join(["semcor", str(sentence_id)])
                row["word_id"] = i
                i += 1
                if row["isNE"]:
                    row["sense"] = np.NaN  #
                yield row

    def convert_chunk(self, chunk) -> dict:
        # the left-hand side of the tree element
        label = chunk.label()
        # the right-hand side: either a list (1) or another tree element (2)
        children = chunk[:]

        # 1. leaf-level: children is a list of words, the label will be the POS
        if isinstance(children[0], str):
            return {
                "POS": label,
                "isNE": False,
                "text": " ".join(children),
                "universalPOS": self.map_pos_tag(label, 'en-ptb')
            }

        # 2. not leaf-level
        # only contains binary trees, therefore this exception shouldn't be raised
        if len(children) != 1:
            raise RecursionError(f"Can't handle multiple recursion: {chunk}")

        # 2a. handle right-hand side tree element, recursion to leaf level
        converted = self.convert_chunk(children[0])
        # 2b. handle left-hand side label
        if type(label) is wordnet.Lemma:
            converted["sense"] = label
        elif type(label) is str:
            # named entity
            if label == "NE":
                converted["isNE"] = True
            # 'more.a.1;2' could be either of two senses ('more.a.1' or 'more.a.2'); I just pick the first
            if ';' in label:
                label = label.split(';')[0]
            # In the nltk version, there are wrongly annotated labels. There aren't that many (663) so I ignore them
            # for now. I also ignore labels of named entities.
            else:
                label = np.NaN
            converted["sense"] = label
        else:
            raise TypeError(f"Cannot handle {chunk}.")
        return converted

    def add_lemma_to_open(self, df: pd.DataFrame = None) -> pd.DataFrame:
        # The lemma of open class words (anything that isn't a named entity but does have a sense)
        # is extracted from the sense
        if df is None:
            df = self.corpus
        open_class = self.get_open_class(df=df)
        # Lemmas have names. If the sense is just a string, it is of the form word.a.0, therefore I take split('.')[0].
        df.loc[open_class, "lemma"] = \
            df[open_class].sense.map(lambda x: x.name() if type(x) is wordnet.Lemma else x.split('.')[0])
        df.loc[open_class, "sense"] = \
            df[open_class].sense.map(lambda x: x.synset().name() if type(x) is wordnet.Lemma else x)
        return df

    def add_lemma_to_closed(self, df: pd.DataFrame = None) -> pd.DataFrame:
        # The lemma of closed class words (words that aren't a named entity, don't have a sense but do have a POS)
        # is the word itself.
        if df is None:
            df = self.corpus
        closed_class = self.get_closed_class(df=df)
        df.loc[closed_class, "lemma"] = self.corpus[closed_class].text
        return df

    def add_punct_pos(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Adds a PUNCT pos tag to all closed class words without POS tag.
        """
        if df is None:
            df = self.corpus
        # punctuation does not have a POS tag in Semcor
        punctuation = self.get_closed_class(df) & df.POS.isna()
        df.loc[punctuation, "POS"] = "PUNCT"
        df.loc[punctuation, "universalPOS"] = "."
        return df

    def retrieve_synsets(self, df: pd.DataFrame = None) -> pd.DataFrame:
        def syn(sense):
            try:
                return wn.synset(sense)
            except Exception as e:
                problems[sense] = e
                return np.NaN

        if df is None:
            df = self.corpus
        problems = {}
        selection = self.get_open_class()
        df.loc[selection, "synset"] = df.sense.map(syn)
        print(problems)
        print(len(problems))
        return df

    def retrieve_hypernyms(self, df: pd.DataFrame = None) -> pd.DataFrame:
        def safe_name(hypernyms):
            if len(hypernyms):
                return hypernyms[0].name()

        if df is None:
            df = self.corpus
        df.loc[~df.synset.isna(), "hypernym"] = \
            df[~df.synset.isna()].synset.map(lambda synset: safe_name(synset.hypernyms())
                                                            if type(synset) is not str else print(synset))
        return df

    def retrieve_hyponyms(self, df: pd.DataFrame = None) -> pd.DataFrame:
        if df is None:
            df = self.corpus
        df.loc[~df.synset.isna(), "hyponyms"] = \
            df[~df.synset.isna()].synset.map(
                lambda synset: list(map(wordnet.Synset.name, synset.hyponyms())) if type(synset) is not str else print(
                    synset))
        return df

    def get_closed_class(self, df: pd.DataFrame = None) -> pd.Series:
        """
        Gives all the words that are not named entities and do not have a sense annotation.
        """
        if df is None:
            df = self.corpus
        return ~df.isNE & df.sense.isna()

    def get_open_class(self, df: pd.DataFrame = None) -> pd.Series:
        """
        Gives all the words that are not named entities and do not have a sense annotation.
        """
        if df is None:
            df = self.corpus
        return ~df.isNE & ~df.sense.isna()

    def retrieve_possible_targets(self, no_base: int, no_other: int, pos: list = None,
                                  no_max: int = 10000, select_hypernym=True) -> pd.DataFrame:
        """
        Retrieves all lemmas from the given data frame that fulfill the parameters (case1, no_other, classes) and
        exports them to a csv-file `'{output_path}/possible_targets_{case1}-{no_other}_{classes}.csv'` Multiwords are
        excluded.

        Parameters
        ----------
        select_hypernym
        no_max: int
            The maximum number of times a lemma should appear. Meant to filter out frequent verbs such as do and have.
        no_base: int
            The minimum number of occurrences ot the base sense (e.g. non-metaphorical).
        no_other: int
            The minimum number of target of the "transformed" sense (e.g. metaphorical).
        pos: list[str], default=['NOUN', 'VERB', 'ADJ']
            The universalPOS classes that should be included as possible targets.
        """
        if pos is None:
            pos = ['NOUN', 'VERB', 'ADJ']

        # Only words with selected pos
        possible_targets = self.corpus.loc[self.corpus['universalPOS'].isin(pos)]
        if select_hypernym:
            target = 'hypernym'
            other_counts = self.corpus.pivot_table(index=['sense'], aggfunc='size').reset_index()
        else:
            target = 'hyponyms'
            other_counts = self.corpus.pivot_table(index=['sense', 'hypernym'], aggfunc='size').reset_index()
        # Determine proportion of base_sense with respect to all other senses
        # Only keep those that make up more than 60% of all occurrences
        sum_all_senses = possible_targets.pivot_table(index=['universalPOS', 'lemma'], aggfunc='size').reset_index()
        base_counts = possible_targets.pivot_table(index=['universalPOS', 'lemma', 'sense', target],
                                                   aggfunc='size').reset_index()
        base_counts = base_counts.merge(sum_all_senses, how='left', on=['lemma', 'universalPOS'])
        base_counts = base_counts.loc[base_counts['0_x'] > base_counts['0_y'] * 0.6]
        del base_counts['0_y']
        base_counts = base_counts.loc[base_counts['0_x'] > no_base]
        other_counts = other_counts.loc[(other_counts[0] > no_other)]
        if select_hypernym:
            both_senses = base_counts.merge(other_counts, left_on='hypernym', right_on='sense')
        else:
            both_senses = base_counts.merge(other_counts, left_on='sense', right_on='hypernym')
        both_senses.rename(columns={'sense_x': 'base_sense', '0_x': 'base_count',
                                    'sense_y': 'other_sense', 0: 'other_count'}, inplace=True)
        del both_senses['hypernym']
        both_senses = both_senses[(both_senses.base_count + both_senses.other_count) < no_max].reset_index(drop=True)
        print(both_senses)
        return both_senses


def main():
    parser = argparse.ArgumentParser(prog="Semcor preprocessing.")
    parser.add_argument('path', type=str, help='path/to/SEMCOR')
    parser.add_argument('--process', action='store_true',
                        help='Should the data be processed or do you wish to load a preprocessed file? Default False.')
    parser.add_argument("--min", dest="minima", nargs=2, type=int, help="The minimum number of occ for s1 and s2.")
    parser.add_argument("--max", dest="maxima", default=10000, type=int, help="The maximum number of occ of a target.")
    parser.add_argument("--pos", dest="pos", default=['NOUN', 'VERB', 'ADJ'], type=str, nargs="+",
                        help="The universal POS classes to consider.")

    args = parser.parse_args()

    if args.process:
        processor = SemcorProcessor()
        print(processor.corpus)
        processor.df_to_csv(f'{args.path}/semcor_preprocessed_new.csv')
    else:
        processor = SemcorProcessor(f'{args.path}/semcor_preprocessed_new.csv', process_data=False)
    if args.minima:
        processor.retrieve_possible_targets(args.minima[0], args.minima[1], args.pos, args.maxima). \
            to_csv(f'{args.path}/possible_targets_taxonomy-hypernym_{args.minima[0]}-{args.minima[1]}_{args.pos}.csv')
        processor.retrieve_possible_targets(args.minima[0], args.minima[1], args.pos, args.maxima,
                                            select_hypernym=False). \
            to_csv(f'{args.path}/possible_targets_taxonomy-hyponym_{args.minima[0]}-{args.minima[1]}_{args.pos}.csv')


if __name__ == "__main__":
    main()
