"""
The module contains all classes necessary for the change simulation: a DataLoader, a Simulator, and the data type
SimulatedChange.
TODO: how this can be executed/used
"""
import pandas as pd
import argparse
from tqdm import tqdm
import csv
from datetime import datetime
from helpers import DataLoader, SimulatedChange


def whole_corpus_as_text(corpus):
    for sen_id, sen_table in tqdm(corpus.groupby('sentence_id')):
        text = " ".join(sen_table["text"].astype(str))
        yield text


def drop_rows(data: pd.DataFrame, values: list[tuple] | pd.DataFrame, columns: list = None,
              drop_sentence: bool = True) -> pd.DataFrame:
    """
    Drops rows / sentences (see drop_rows) based on given values.
    If values is a df, it will simply drop all rows in the df from data.
    Values can be a list of values tuples [(t11, t12, ...), ]. The function then drops all rows for which
    `columns[0] == tx1 AND columns[1] == tx2 AND ... columns[y] == txy` for all x, 0 <= x < len(values).

    Parameters
    ----------
    drop_sentence: bool, default=True
        Drop the whole sentence or just the row.
    data: pd.DataFrame
    columns: list, default=None
        The name of the column to search. Only given if values is a list, len(columns).
    values: list or pd.DataFrame
        The values or rows to search for.

    Returns
    -------
    The changed dataframe, in which all the rows / sentences which contain certain values have been dropped.
    """
    if columns is None and type(values) is pd.DataFrame:
        rows_with_values = values
    elif columns is not None and type(values) == list:
        if type(values[0]) is not tuple:
            values = [(element,) for element in values]
        # create a new column that merges the 'columns' to a list
        data["unified_column"] = data.loc[:, columns].values.tolist()
        # then select all rows for which the unified_column tuple == one of the value tuples in values
        rows_with_values = data[data.unified_column.map(tuple).isin(values)]
        del data["unified_column"]
    else:
        raise ValueError("Values and columns types not right, didn't drop anything.")

    if drop_sentence:
        sen_with_value = list(rows_with_values['sentence_id'])
        rows_with_values = data[data['sentence_id'].isin(sen_with_value)]
    # merge the two tables with an indicator column (_merge), then only retain rows that were only in data (left_only)
    # then drop the _merge column again
    return data.merge(rows_with_values, how="outer", indicator=True). \
        query('_merge == "left_only"').drop(columns="_merge")


class Simulator:
    """
    Parameters
    ----------
    data: list[[str], [pandas.DateFrame], [pandas.DateFrame]]
        The data for the simulation: should contain a list of change names, a list of corpora, and a list of possible
        targets for the simulation.
    n: int, default=12
        The number of changes to be simulated per type.
    loss: bool, default=False
        Should the simulator also simulate sense loss or only sense gain.
    mode: str default="base_other"
        Mode of sense selection in the simulation. 'frequency based' for making the more frequent sense the original
        one, or 'base_other' for 'base_sense' as original sense and 'other_sense' as new sense.

    Attributes
    ----------
    change_types: list[str]
        The names of the change types.
    corpora: list[pandas.DateFrame]
    possible_target_words: [pandas.DateFrame]
    changes: list[list[SimulatedChange], ...]
        Contains the SimulatedChange objects created at initialization.
    simulated_corpora: list[pd.DataFrame]
        The simulated corpora.
    """

    def __init__(self, data: list, n: int = 12, loss: bool = False, mode: str = "base_other"):
        assert len(data) == 3, "Data does not have the right format. Should be [[type,corpus,targets],[...],...]"
        assert (n % 4) == 0, "The number of targets should be dividable by 4."

        self.change_types, self.corpora, self.possible_target_words = data
        self.corpus: pd.DataFrame = pd.concat(self.corpora)
        self.corpus = self.corpus.assign(status=pd.NA)
        self.no_of_targets_per_type: int = n
        self._loss: bool = loss
        self._mode: str = mode
        self._relative: bool = False
        self.size: int = 0
        self.changes: list[SimulatedChange] = []
        # For loop not list comprehension because self.changes ist used to detect duplicate targets (get_other_targets).
        for i in range(len(self.possible_target_words)):
            self.changes = self.changes + self.select_target_words(i)
        self.one_target_sentences: set = set()
        self.more_targets_sentences: set = set()
        self.simulated_corpora = [pd.DataFrame(), pd.DataFrame()]

    def select_target_words(self, i: int) -> [SimulatedChange] or []:
        """
        A function to select target words from a list of possible target words, then calls create_change for
        the selected targets.

        Parameters
        ----------
        i: int
            The index of the change type to be considered (corresponds to the ith item in self.change_types,
            self.corpora and self.possible_target_words).

        Returns
        -------
        list[SimulatedChanges] or []
            list[SimulatedChanges] for the selected target words.
            [] if the number of possible target words is too short and the change type is skipped.
        """

        def select_result(j: int) -> str:
            # function to determine which change results should be simulated with the selected targets
            if j < self.no_of_targets_per_type / 2:
                if self._relative:
                    return "relative"
                # if there shall be loss, the first 1/4 are generated as sense loss
                if self._loss and j < self.no_of_targets_per_type / 4:
                    return "loss"
                # other cases of the first 1/2 are generated as sense gain
                else:
                    return "gain"
            # 1/2 should remain constant
            else:
                return "constant"

        # Select n target words randomly from possible_target_words[i], the possible target of the ith type.
        try:
            targets_of_i = self.select_targets(i, self.no_of_targets_per_type)
        except ValueError:
            print("The number of targets is too high for the given list of possible target words.")
            return []  # the type is skipped

        return [SimulatedChange(targets_of_i.iloc[j], change_result=select_result(j), change_type=self.change_types[i])
                for j in range(len(targets_of_i))]

    def select_targets(self, i: int, n: int) -> pd.DataFrame:
        targets_of_i = self.possible_target_words[i] \
            .sample(n=n) \
            .reset_index(drop=True)
        # we need to reset the index because we loop over targets 1 to n later. we want to be able to
        # reference types by the index.
        # self.possible_target_words[i] = drop_rows(self.possible_target_words[i], targets_of_i, drop_sentence=False)
        d1 = targets_of_i[targets_of_i.other_sense.duplicated() | targets_of_i.base_sense.duplicated() |
                          targets_of_i.lemma.isin(self.get_targets())]
        try:
            assert d1.empty
        # duplicates are dropped from the list of possible target words, then we try again
        except AssertionError:
            print(f"Drew duplicate targets {[d for d in d1.lemma]}, retrying.")
            targets_of_i = drop_rows(targets_of_i, d1, drop_sentence=False)
            targets_of_i = pd.concat([targets_of_i, self.select_targets(i, len(d1))])
        return targets_of_i

    def split_corpora(self):

        def select_rows(data: pd.Series, freq: int, timestep: str) -> pd.Series:
            """
            Selects `freq` rows from the given `data`, removes them from `data` and adds them
            to the simulated corpus of `timestep` t.
            """
            if freq == 0:
                return data
            selected_sentences = data.sample(freq)
            update_status(selected_sentences, timestep, remove=False)
            return data.drop(data[data.isin(selected_sentences)].index)

        def update_status(sentence_ids, status="drop", remove=False):
            if remove:
                self.corpus.status.loc[((~ self.corpus.sentence_id.isin(sentence_ids))
                                        & (self.corpus.status == status))] = pd.NA
            self.corpus.status.loc[self.corpus.sentence_id.isin(sentence_ids)] = status

        def determine_sense_distribution() -> (dict, dict):
            """
            Determines how many occurrences of sense 1 and sense 2 there should be in timestep 1 and timestep 2.
            The _mode influences how the base sense is selected.

            Returns
            -------
            Two dicts with the sense frequencies in t1 and t2 each. E.g. {'lit': 30, 'met': 0}, {'lit': 25, 'met': 25}
            If the change result is 'gain' the relative frequency changes from 100% s1 to 50% s1 and 50% s2.
            For the result 'loss' this is the other way around.
            If the change result is 'constant' the relative frequency does not change.
            """
            if self._mode == "frequency":
                # should yield sth like 40 - 20-20; 30 - 20-20; 25 - 15-15
                s1, s2 = sense_counts.idxmax()[0], sense_counts.idxmin()[0]
            else:
                # the base sense is s1 (literal), other sense is s2 (metaphorical etc.)
                s1, s2 = target.base_sense, target.other_sense

            try:
                freq_s1, freq_s2 = sense_counts[s1], sense_counts[s2]
            except KeyError:
                raise ValueError(f"{target} does not have enough occurrences.")
            if freq_s1 < 38 or freq_s2 < 13:
                raise ValueError(f"{target} does not have enough occurrences.")

            if target.change_result == "constant":
                return {s1: freq_s1 // 2, s2: freq_s2 // 2}, {s1: freq_s1 // 2, s2: freq_s2 // 2}

            # if target.change_result == "relative":
            # TODO implement this
            #     pass

            # for this function to work I need to have at least 38 occ of sense 1
            freq_s1_in_tx = max(25, freq_s1 - freq_s2)
            freq_s1_in_ty = freq_s1 - freq_s1_in_tx
            freq_s2_in_ty = freq_s1_in_ty

            tx = {s1: freq_s1_in_tx, s2: 0}
            ty = {s1: freq_s1_in_ty, s2: freq_s2_in_ty}

            if target.change_result == "gain":
                return tx, ty
            elif target.change_result == "loss":
                return ty, tx
            else:
                raise ValueError("Encountered and unknown change result.")

        for target in self.changes:
            target_rows = self.corpus[(self.corpus.lemma == target.lemma) & (self.corpus.universalPOS == target.pos)
                                      & (self.corpus.sense != target.base_sense) & (
                                                  self.corpus.sense != target.other_sense)].sentence_id
            update_status(target_rows)
        for target in self.changes:
            try:
                target_rows = self.corpus.loc[
                    (((self.corpus.lemma == target.lemma) & (self.corpus.universalPOS == target.pos))
                     | (self.corpus.sense == target.other_sense)) & (self.corpus.status != 'drop')]
                # count the frequencies of the two senses of the target lemma
                sense_counts = target_rows.value_counts(subset=['sense'])
                try:
                    # determine which senses should occur how frequently in which time step
                    target.senses_before_change, target.senses_after_change = determine_sense_distribution()
                except ValueError or KeyError:
                    print(f"{target} does not have enough occurrences. Skipping.")
                    continue
                for sense in [target.base_sense, target.other_sense]:
                    # retrieve the rows of one sense
                    rows_with_sense = target_rows[target_rows['sense'] == sense]
                    corpus_counts = rows_with_sense.value_counts(subset=['status'])
                    try:
                        freq_before = max(target.senses_before_change[sense] - corpus_counts['t1'], 0)
                    except KeyError:
                        freq_before = target.senses_before_change[sense]
                    try:
                        freq_after = max(target.senses_after_change[sense] - corpus_counts['t2'], 0)
                    except KeyError:
                        freq_after = target.senses_after_change[sense]
                    # add the senses to either before or after change
                    rows_with_sense = select_rows(rows_with_sense.sentence_id, freq_before, 't1')
                    try:
                        select_rows(rows_with_sense, freq_after, 't2')
                    except ValueError:
                        update_status(rows_with_sense, 't2')
                target_rows = self.corpus.loc[
                    (((self.corpus.lemma == target.lemma) & (self.corpus.universalPOS == target.pos))
                     | (self.corpus.sense == target.other_sense)) & (self.corpus.status.isna())]
                update_status(target_rows.sentence_id, status="drop", remove=False)
            except AttributeError or KeyError or ValueError as err:
                print(err)
                print(f"There seems to be something wrong with target {target}. Skipping.")

        # 2.b randomly assort all sentences left in corpus
        remaining = pd.Series(pd.unique(self.corpus.sentence_id[self.corpus.status.isna()]))
        no_remaining = len(remaining)
        for j in ['t1', 't2']:
            remaining = select_rows(remaining, no_remaining // 2, j)
        print(len(self.corpus))

    def get_targets(self, pos: bool = False) -> list:
        """
        Get the lemmas (or (lemma, pos) tuples) of the targets of this change type.
        """
        return [(target.lemma, target.pos) if pos else target.lemma for target in self.changes]

    def mark_replacements(self, corpus, status):
        replacements = pd.DataFrame()
        for target in self.changes:
            if target.change_type == "taxonomy-hypernym" or target.change_type == "taxonomy-hyponym":
                target_replacements = self.corpus[
                    (self.corpus.sense == target.other_sense) & (self.corpus.status == status)].copy()
                target_replacements.rename(columns={'lemma': 'old_lemma'}, inplace=True)
                target_replacements = target_replacements.assign(new_lemma=target.lemma)
                target_replacements = target_replacements[["sentence_id", "word_id", "old_lemma", "new_lemma"]]
                replacements = pd.concat([replacements, target_replacements], axis=0)
        if replacements.empty:
            return corpus.reindex(columns=["sentence_id", "word_id", "old_lemma", "new_lemma"])
        return corpus.merge(replacements, how='left', on='sentence_id')


def main():
    parser = argparse.ArgumentParser(prog="Change simulator with data loader.")
    parser.add_argument('change_types', metavar='T', type=str, nargs='+',
                        help='The names of the change types to be simulated.')
    parser.add_argument("-c", "--corpora", dest="corpora", nargs="+", help="Paths to the corpus files (csv).")
    parser.add_argument("-t", "--targets", dest="possible_targets", nargs="+",
                        help="Paths to the lists of possible target words (csv or txt).")
    parser.add_argument("-n", dest="no_changes", type=int, default=12,
                        help="The number of changes to be simulated (has to be dividable by 4).")
    parser.add_argument("--loss", action='store_true', default=False, help="Should the system simulate loss?")
    parser.add_argument("-m", "--mode", dest="mode", type=str, default="base_other", help="The mode of operation.")

    args = parser.parse_args()
    print("Loading files.")
    data_loader = DataLoader(args.corpora, args.possible_targets)
    print("Determining changes.")
    simulator = Simulator([args.change_types, data_loader.corpora, data_loader.possible_targets],
                          n=args.no_changes, loss=args.loss, mode=args.mode)
    print("\nSimulation:")
    time = datetime.now().strftime("%Y%m%d-%H:%M")
    simulator.split_corpora()
    print(simulator.corpus.value_counts(subset=['status']))
    print("\nSplitting.")
    for corpus, t in zip(simulator.simulated_corpora, ['t1', 't2']):
        corpus = pd.DataFrame(pd.unique(simulator.corpus[simulator.corpus.status == t]["sentence_id"]))
        corpus.rename(columns={0: "sentence_id"}, inplace=True)
        corpus = simulator.mark_replacements(corpus, t)
        corpus.to_csv(f"simulations/{time}_sentences{t}.txt", index=False)
    print("Saving.")
    for file in ['data/all_text.txt', f'simulations/{time}_corpus_t1.txt', f'simulations/{time}_corpus_t2.txt']:
        with open(file, 'w') as f:
            for sentence in whole_corpus_as_text(simulator.corpus):
                f.write(f"{sentence}")
    simulator.corpus.to_csv(f"simulations/{time}_whole_corpus.csv")
    with open(f"simulations/{time}_changes.csv", "w") as f:
        new_val = ["lemma", "pos", "change_type", "change_result", "base_sense",
                   "other_sense", "counts_before", "counts_after"]
        j = csv.DictWriter(f, fieldnames=new_val)
        j.writeheader()
        for change in simulator.changes:
            cd = change.export_to_dict()
            j.writerow(cd)


if __name__ == "__main__":
    main()
