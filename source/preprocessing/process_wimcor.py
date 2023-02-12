"""
This module is part of the preprocessing. It takes the full-corpus-reformatted.xml file and saves it as a pre-processed csv.
The function retrieve_possible_targets gives a list of possible target words and saves them to csv.
"""

from abc import ABC
from multiprocessing import Pool

import pandas as pd
import argparse
from xml.etree import ElementTree
from tqdm import tqdm
from Processor import Processor
from textblob import TextBlob


class WimcorProcessor(Processor, ABC):
    """
    A processor for the wimcor corpus. Implements processor.

    Attributes
    ----------
    corpus: pd.DataFrame
        The corpus as a table.
    """

    def __init__(self, file_path: str, process_data: bool = False):
        super().__init__(file_path, process_data=process_data)
        if process_data:
            print("Adding lemmas.")
            self.tag_dict = {"J": 'a',
                             "N": 'n',
                             "V": 'v',
                             "R": 'r'}
            pool = Pool(processes=8)
            self.corpus["lemmas"] = pool.map(self.lemmatize, tqdm(self.corpus.text))
            self.corpus = pd.DataFrame(self.split_sentences(self.corpus))
            # self.corpus["lemmas"] = pool.map(self.pos_tag, tqdm(self.corpus.lemmas))
            # self.corpus["universalPOS"] = pd.Series(["NOUN" for x in range(len(self.corpus))])
        # else:
        #    print("Parsing annotations to list.")
        #    pool = Pool(processes=8)
        #    self.corpus.lemmas = pool.map(ast.literal_eval, tqdm(self.corpus.lemmas))
        print("Finished processing.")

    def iterate_element_tree(self) -> pd.Series:
        """
        A generator that transforms the samples in the xml ElementTree to pd.Series.

        Yields
        ------
        pd.Series
            The preprocessed rows.
        """
        print("Processing corpus sample by sample:")
        for sample_id, sample in enumerate(tqdm(self._element_tree.getroot())):
            row = {"sentence_id": sample_id}
            for annotation in sample:
                row["text"] = str.join(" ", [annotation.text,
                                             ElementTree.tostring(annotation, encoding='unicode').split("</pmw>")[-1]])
                if type(sample.text) is str:
                    row["text"] = str.join(" ", [sample.text, row["text"]])
                row["lemma"] = annotation.text
                fine = annotation.get('fine').replace(" ", "").replace(",", ";")
                row["sense"] = str.join("_", [annotation.get('coarse'), annotation.get('medium'), fine])
            yield row

    def pos_tag(self, sentence):
        return [(lemma, self.map_pos_tag(pos, 'en-ptb')) for lemma, pos in sentence]

    @staticmethod
    def lemmatize(self, sentence):
        sent = TextBlob(sentence)
        return sent.tags

    def split_sentences(self, corpus):
        for i in range(len(tqdm(corpus))):
            sentence = corpus.iloc[i]
            word_id = 0
            for (word, pos) in sentence.lemmas:
                word_id += 1
                if word == sentence.lemma:
                    yield {"sentence_id": sentence.sentence_id, "sense": sentence.sense, "text": word,
                           "lemma": sentence.lemma, "universalPOS": "NOUN", "word_id": word_id}
                else:
                    yield {"sentence_id": sentence.sentence_id, "sense": None, "text": word,
                           "lemma": word.lemmatize(self.tag_dict.get(pos[0], 'n')),
                           "universalPOS": self.map_pos_tag(pos, 'en-ptb'), "word_id": word_id}

    def retrieve_possible_targets(self, no_base: int, no_other: int, pos: list = "", no_max: int = None):
        """
        A function to retrieve possible targets (lemmas of a specific sense) from a data frame. Will save the possible
        targets to a .csv file.

        Parameters
        ----------
        no_max
        pos
            The `path/to/the/output/folder/`.
        no_base: int
            The frequency of the no_base sense.
        no_other: int
            The frequency of the other sense.
        """
        counts = self.corpus.pivot_table(index=['lemma', 'sense'], aggfunc='size').reset_index()
        base_sense = counts.loc[(counts[0] > no_base) &
                                (counts.sense.map(lambda x: x.rpartition('_')[0]) == 'lit_LOCATION')]
        other_sense = counts.loc[(counts[0] > no_other) &
                                 (counts.sense.map(lambda x: x.rpartition('_')[0]) != 'lit_LOCATION')]
        both_senses = base_sense.merge(other_sense, on='lemma')
        both_senses.rename(columns={'sense_x': 'base_sense', '0_x': 'base_count',
                                    'sense_y': 'other_sense', '0_y': 'other_count'}, inplace=True)
        both_senses = both_senses.assign(universalPOS='NOUN')
        print(both_senses)
        return both_senses


def main():
    parser = argparse.ArgumentParser(prog="Wimcor preprocessing.")
    parser.add_argument('path', type=str, help='path/to/wimcor')
    parser.add_argument('--process', action='store_true',
                        help='Should the data be processed or do you wish to load a preprocessed file? Default False.')
    parser.add_argument("--min", dest="minima", nargs=2, type=int, help="The minimum number of occ for s1 and s2.")

    args = parser.parse_args()

    if args.process:
        processor = WimcorProcessor(f"{args.path}/full-corpus-reformatted.xml", process_data=True)
        print(processor.corpus)
        processor.df_to_csv(f'{args.path}/wimcor_preprocessed_new.csv')
    else:
        processor = WimcorProcessor(f'{args.path}/wimcor_preprocessed_new.csv')
    if args.minima:
        processor.retrieve_possible_targets(args.minima[0], args.minima[1]).\
            to_csv(f'{args.path}/possible_targets_metonymy_{args.minima[0]}-{args.minima[1]}.csv')


if __name__ == "__main__":
    main()
