import ast
from multiprocessing import Pool

import pandas as pd
from tqdm import tqdm


class DataLoader:
    """
    A data loader for all the files necessary for the simulation (i.e. the preprocessed corpora and the target lists),
    given the paths to the respective csv files.
    It also re-formats the data in such a way, that it can be handled uniformly by the :py:class:`Simulator`.

    Parameters
    ----------

    corpus_paths: list[str]
        A list with paths to the corpora to be loaded. The corpus files should be csv.
        Ex: ``['path/to/file1.csv','path/to/file2.csv']``. corpus_paths[i] should correspond to targets_paths[i].
    targets_paths: list[str]
        A list with paths to the lists of target words. The files should be csv.
        Ex: ``['path/to/file1.csv','path/to/file2.csv']``. corpus_paths[i] should correspond to targets_paths[i].

    Attributes
    ----------

    corpora: list[pandas.DataFrame]
        A list of pandas.DataFrame loaded from the files given in **corpus_paths**.
        corpora[i] belongs to possible_targets[i].
    possible_targets: list[pandas.DataFrame]
        A list of pandas.DataFrame loaded from the files given in **targets_paths**.
        corpora[i] belongs to possible_targets[i].
    """

    def __init__(self, corpus_paths: [str] = ("",), targets_paths: [str] = ("",)):
        self.corpora, self.possible_targets = [], []
        # This line constructs the lists of corpus and target dfs by first zipping the paths of a corpus-target
        # pair, and then loading them together. The outermost zip(*) unzips corpus-target pairs,
        # i.e. reconstructs the form of two separate lists for corpora and targets.
        for corpus_path in corpus_paths:
            try:
                self.corpora.append(pd.read_csv(corpus_path, index_col=False, dtype=str,
                                                usecols=['sentence_id', 'word_id', 'text',
                                                         'lemma', 'sense', 'universalPOS']))
            except FileNotFoundError as er:
                print(er)
                print(f"{corpus_path} could not be loaded. Skipping corpus and dropping corresponding target_path.")
        for target_path in targets_paths:
            try:
                self.possible_targets.append(pd.read_csv(target_path, index_col=0))
            except FileNotFoundError:
                print(f"{target_path} could not be loaded. Skipping target list and dropping corresponding corpus.")


class SimulatedChange:
    """
    A data type to denote a change to be simulated.

    Parameters
    ----------

    target: pandas.DataFrame
        A one row pandas dataframe with the entry of the target word.
    change_result: str, default="constant"
        The result of the change to be simulated. This should be something like "decrease" or "increase"
        (in the number of senses).
    change_type: str, default="NaN"
        The quality of the change to be simulated. This is mostly relevant in the later evaluation.

    Attributes
    ----------

    lemma: str
        The lemma of the word to be changed.
    pos: str
        The part of speech of the lemma. If no POS is given in target, this is NaN.
    change_result: str
        The result of the change to be simulated, e.g. "decrease" or "increase" (in the number of senses) or "constant".
    change_type: str
        The quality of the change to be simulated, e.g. "metaphor", "hypernym", "hyponym", "metonym", or "NaN".
    base_sense: str
    other_sense: str
    senses_before_change: dict
    senses_after_change: dict
    """

    def __init__(self, target: pd.Series, change_result: str = "constant", change_type="NaN"):
        if type(target) != pd.Series:
            print("Target should be a series.")
            raise AssertionError()
        self.lemma = target['lemma']
        try:
            self.pos = target['universalPOS']
        except KeyError:
            self.pos = "NaN"
        self.change_result = change_result
        self.base_sense = target['base_sense']
        self.other_sense = target['other_sense']
        # As of now, these are edited later. See decide_assortments which is commented out.
        self.senses_before_change, self.senses_after_change = [], []
        self.change_type = change_type

    def __repr__(self):
        return f"{self.lemma} ({self.pos}): {self.change_type}, {self.change_result}"

    def export_to_dict(self):
        return {
            "lemma": self.lemma,
            "pos" : self.pos,
            "change_type": self.change_type,
            "change_result": self.change_result,
            "base_sense": self.base_sense,
            "other_sense": self.other_sense,
            "counts_before": str(self.senses_before_change),
            "counts_after": str(self.senses_after_change)
        }
