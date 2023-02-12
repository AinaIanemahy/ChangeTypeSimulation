"""
This module is part of the preprocessing. It takes the VUAMC.xml file and saves it as a pre-processed csv.
The function retrieve_possible_targets gives a list of possible target words and saves them to csv.
"""

import argparse
from xml.etree import ElementTree
import pandas as pd
from tqdm import tqdm

from abc import ABC
from Processor import Processor


class VuamcProcessor(Processor, ABC):
    """
    A parser for the VUAMC XML file (available under data). Could maybe be used for other versions of the BNC,
    but __remove_namespaces() would have to be replaced to do that.

    Parameters
    ---------
    file_path: str
        The file path of the file like `path/to/file.xml`.

    Attributes
    ----------
    sentence_elements: set
        A set of all possible elements (tags) contained in a VUAMC sentence.
        Most relevant are w = word, c = punctuation, seg = metaphor annotation.
    no_of_fragments: int
        The number of fragments parsed by the parser.
    no_of_sentences: int
        The number of sentences parsed by the parser.
    no_of_words: int
        The number of words parsed by the parser.
    """

    def __init__(self, file_path: str, process_data: bool = True):
        self.no_of_fragments: int = 0
        self.no_of_sentences: int = 0
        self.no_of_words: int = 0
        self.sentence_elements: set = set()
        # I used sentence_elements to identify all possible element tags in sentences. now I use it in the tests to
        # see if I still traverse the tree properly. Sentences can contain the following elements:
        # RELEVANT: 'c' = punctuation, 'w' = word, 'ptr' SKIP LEVEL: 'choice' = used with spelling mistakes, 'sic',
        # 'hi' = highlighting, 'seg' IGNORE: 'gap', 'pause', 'pb', 'shift', 'vocal', 'incident', 'corr'
        super().__init__(file_path, process_data=process_data)
        if process_data:
            self.format_df()

    def iterate_element_tree(self) -> pd.DataFrame:
        """
        Function to transfer the relevant information from self._element_tree to a pd.DataFrame.
        Only keeps information on fragment and sentence structure and words and their annotations.
        Calls descend_recursively on each fragment.

        Returns
        -------
        pd.DataFrame
        """

        def process_fragment():
            fragment_id = fragment.get('{http://www.w3.org/XML/1998/namespace}id')
            # From here I recursively descend into the tree to find all sentences. This cannot be done following
            # rules because the structure is irregular.
            try:
                self.no_of_fragments += 1
                corpus[fragment_id], error = self.descend_recursively(fragment)
                if error:
                    print(f"in fragment {fragment_id}")
            except AttributeError:
                print(fragment_id)

        def corpus_to_df():
            for fragment_id in tqdm(corpus):
                corpus[fragment_id] = {sentence_id: pd.DataFrame(corpus[fragment_id][sentence_id],
                                                                 columns=['lemma', 'POS', 'text', 'mrw', 'mFlag',
                                                                          'isMWHead', 'MWid'])
                                       for sentence_id in corpus[fragment_id]}
                corpus[fragment_id] = pd.concat(corpus[fragment_id].values(), keys=[str.join('_', [fragment_id, key])
                                                                                    for key in
                                                                                    corpus[fragment_id].keys()])

        corpus = {}
        root = self._element_tree.getroot()

        print("\nFinding fragments and sentences.")
        # This gives me a dict with all fragment names as keys. Each fragment contains a dict of sentences.
        for fragment in root.find('{http://www.tei-c.org/ns/1.0}text').find('{http://www.tei-c.org/ns/1.0}group'):
            process_fragment()

        print("\nCreating dataframe.")
        # Transform corpus dict to pd.DataFrame
        corpus_to_df()
        print("Finished processing.")
        return pd.concat(corpus.values())

    def descend_recursively(self, parent: ElementTree.Element) -> (dict, bool):
        """
        This function allows me to recursively run through the tree (depth first search, stops when a sentence is found)
        to find all s tags (sentences), skipping all other structural tags.
        This is necessary as there are different structuring levels in the different types of documents.
        If a sentence is found which cannot be processed (attribute error of process_sentence), the fragment and
        sentence ids are printed to the commandline.

        Parameters
        ----------
        parent: xml.etree.ElementTree.Element
            The current parent element of the tree.

        Returns
        -------
        dict
            The changed fragment_dict.
        bool
            Did an error occur in this fragment?
        """
        fragment_dict = {}
        error = False
        for child in parent.findall('*'):
            # sentence level found, add a new sentence (ElementTree.Element) to the corpus dict some n appear twice
            # so only the combination fragment_id and sentence n identifies the sentence unambiguously
            if self.__remove_vuamc_namespace(child.tag) == 's':
                sentence_id = child.get('n')
                # Process the sentence into a nicer format.
                try:
                    fragment_dict[sentence_id] = self.process_sentence(child)
                    self.no_of_sentences += 1
                except AttributeError as er:
                    print(f"Error {er}")
                    print(f"in sentence {sentence_id}")
                    error = True
            # not on sentence level, search on next level with current child as parent
            else:
                child_dict, child_error = self.descend_recursively(child)
                # this merges the dictionary returned from the upper level back with the dictionary at this level
                fragment_dict = fragment_dict | child_dict
                # python 3.9 introduces | as merge operator, for earlier python versions the following is equivalent:
                # fragment_dict = {**fragment_dict, **self.descend_recursively(child)}
                if child_error:
                    error = True
        return fragment_dict, error

    def process_sentence(self, s: ElementTree.Element) -> list:
        """
        Processes each sentence to be a list of words (and punctuation).

        Parameters
        ----------
        s: xml.etree.ElementTree.Element
            The sentence to be processed.
        Returns
        -------
        list[list]
            The processed sentence as a list of lists.
        Raises
        ------
        AttributeError
            if an element cannot be processed correctly because it does not have the required attributes.
        """

        def identify_multi_words(cur_child: ElementTree.Element) -> tuple:
            """
            VUAMC has to deal with multi-words (compounds, particle verbs etc.). These are linked to each other
            through cur_word id and corresp annotations.

            Parameters
            ----------
            cur_child: xml.etree.ElementTree.Element
                The cur_word to be checked for a multi-cur_word annotation.
            Returns
            -------
            tuple
                (True, id) for main part of a multi-cur_word, (False, id) for other parts, else (False, None).
            """
            # TODO: for multi-words it might make sense to change the lemma. If I achieve that, I do not need this
            #  annotation any more. As long as I don't I have to keep this.
            if 'corresp' in cur_child.attrib.keys():
                return False, cur_child.get('corresp')
            elif '{http://www.w3.org/XML/1998/namespace}id' in cur_child.attrib.keys():
                return True, cur_child.get('{http://www.w3.org/XML/1998/namespace}id')
            else:
                return False, None

        def process_metaphor(cur_child: ElementTree.Element):
            """
            Changes the default values of mrw, mFlag, multi_words and cur_word if the cur_word is a metaphor.

            Parameters
            ----------
            cur_child: xml.etree.ElementTree.Element
                The metaphorical word to be processed.
            Returns
            -------
            The adapted values for mrw (bool), mFlag (bool), cur_word, is_mw_head, mw_id.
            """
            cur_word = cur_child.text.strip()

            if cur_child.get('function') == "mrw":
                return True, False, cur_word, identify_multi_words(cur_child)
            elif cur_child.get('function') == "mFlag":
                return False, True, cur_word, identify_multi_words(cur_child)
            else:
                raise AttributeError

        def append_element():
            sentence.append([lemma, pos, word, mrw, m_flag, is_mw_head, mw_id])
            self.no_of_words += 1

        sentence = []
        for element in s:

            element_tag = self.__remove_vuamc_namespace(element.tag)
            self.sentence_elements.add(element_tag)

            # Setting the default values for all annotations.
            lemma = element.get('lemma')
            word = None  # I don't use this. It is just in case I call append() outside the conditions listed below.
            mrw = False
            m_flag = False
            pos = element.get('type')
            is_mw_head, mw_id = identify_multi_words(element)

            # The following conditions are based on an analysis of the XML structure:
            # 1. sic is sometimes used for misspelled words - these are not annotated at all
            if element_tag == 'sic' and len(element.findall('*')) == 0:
                word = element.text.strip()
                append_element()

            # 2. For intermediate-layer elements I proceed recursively to the deeper levels.
            elif element_tag == 'sic' or element_tag == 'hi' or element_tag == 'seg' or element_tag == 'choice':
                # Because process_sentence() returns a list of words, I can just loop through what is returned and
                # append it to the real sentence.
                for item in self.process_sentence(element):
                    sentence.append(item)

            # 3. Only target-layer elements are processed.
            elif element_tag == 'w' or element_tag == 'c':
                # Check if the cur_word has children, i.e. if it has metaphor annotations
                children = element.findall('*')
                # a. Metaphors have to be processed before appending the cur_word.
                if len(children) >= 1:
                    # len(children) is 1 for simple metaphors
                    # len(children) is 2 for two-parters like canyon-like and up to -> therefore for-loop
                    for child in children:
                        mrw, m_flag, word, (is_mw_head, mw_id) = process_metaphor(child)
                        append_element()
                # b. All non-metaphorical words keep the default values. Only the cur_word text still has to be added.
                else:
                    word = element.text.strip()
                    append_element()
                # c. Catching cases where processing might have gone wrong.
                if word is None or pos is None:
                    print(lemma)
                    raise AttributeError

            # 4. All other elements can be ignored.

        return sentence

    def format_df(self):
        """
        Formatting the dataframe for the simulation, adding universalPOS, resetting the index and renaming mrw to sense.
        """
        # universal POS
        self.corpus['universalPOS'] = self.corpus['POS'].map(lambda x: self.map_pos_tag(x, 'en-vuamc'))
        # index
        self.corpus = self.corpus.reset_index(names=['sentence_id', 'word_id'])
        self.corpus.rename(columns={'mrw': 'sense'}, inplace=True)
        self.corpus['sense'] = self.corpus['sense'].replace([True, False], ['met', 'lit'])
        self.corpus.sense = self.corpus.apply(lambda row: "_".join([str(row['sense']), str(row['lemma'])]), axis=1)

    @staticmethod
    def __remove_vuamc_namespace(tag: str) -> str:
        """
        Function takes a tag or attribute of the XMLtree and removes the namespace if it contains one. Mainly allows
        to keep the longer namespaces out of the code.

        Parameters
        ----------
        tag: str
            Either the tag or attribute str as given in the tree.

        Returns
        -------
        str
            Tag or attribute string with the namespace removed.
        """
        if "{http://www.w3.org/XML/1998/namespace}" in tag:
            return tag.replace("{http://www.w3.org/XML/1998/namespace}", "")
        elif "{http://www.tei-c.org/ns/1.0}" in tag:
            return tag.replace("{http://www.tei-c.org/ns/1.0}", "")
        else:
            return tag

    def corpus_size_tests(self):
        """
        A method to test whether the dataframe fulfills all the expected stats. If one of the assertions is not
        fulfilled there is a problem with the data or the code.
        """
        assert (self.no_of_fragments == 117)
        try:
            assert (self.no_of_sentences == 16202)
            assert (self.no_of_words == 238317)
        except AssertionError:
            print(self.no_of_sentences)
            print(self.no_of_words)
        try:
            assert (self.sentence_elements == {'gap', 'ptr', 'choice', 'incident', 'w', 'seg', 'shift', 'pb', 'hi',
                                               'pause', 'vocal', 'c', 'sic', 'corr'})
            # universal POS tag set + UND for words which belong to two classes + None for misspelled, unannotated words
            assert (set(self.corpus['universalPOS'])) == {'UND', 'PRT', '.', 'ADP', 'DET', 'ADV', 'CONJ', 'ADJ',
                                                          'NUM', 'NOUN', 'PRON', 'X', None, 'VERB'}
        except AssertionError:
            print(self.sentence_elements)
            print(set(self.corpus['universalPOS']))

        words = len(self.corpus)
        sentences = len(set(self.corpus.sentence_id))
        try:
            assert (sentences == self.no_of_sentences)
            assert (words == self.no_of_words)
        except AssertionError:
            print(sentences)
            print(words)

    def retrieve_possible_targets(self, no_base: int, no_other: int,
                                  pos: list = None, max_no: int = 10000, output_path: str = ""):
        """
        Retrieves all lemmas from the given data frame that fulfill the parameters (case1, no_other, classes) and
        exports them to a csv-file `'{output_path}/possible_targets_{case1}-{no_other}_{classes}.csv'` Multiwords are
        excluded.

        Parameters
        ----------
        max_no: int
            The maximum number of times a lemma should appear. Meant to filter out frequent verbs such as do and have.
        output_path: str
            The path to the folder in which to save the list of possible targets.
        no_base: int
            The minimum number of occurrences ot the base sense (e.g. non-metaphorical).
        no_other: int
            The minimum number of target of the "transformed" sense (e.g. metaphorical).
        pos: list[str], default=['NOUN', 'VERB', 'ADJ']
            The universalPOS classes that should be included as possible targets.
        """
        if pos is None:
            pos = ['NOUN', 'VERB', 'ADJ']
        # I do not want multiwords as targets
        possible_targets = self.corpus[self.corpus['MWid'].isna()]
        # Only words with selected pos
        possible_targets = possible_targets.loc[possible_targets['universalPOS'].isin(pos)]

        counts = possible_targets.pivot_table(index=['universalPOS', 'lemma', 'sense'], aggfunc='size').reset_index()
        base_sense = counts.loc[(counts[0] >= no_base) & (counts.sense.map(lambda x: x.rpartition('_')[0]) == 'lit')]
        other_sense = counts.loc[(counts[0] >= no_other) & (counts.sense.map(lambda x: x.rpartition('_')[0]) == 'met')]
        both_senses = base_sense.merge(other_sense, on=['lemma', 'universalPOS'])
        both_senses.rename(columns={'sense_x': 'base_sense', '0_x': 'base_count',
                                    'sense_y': 'other_sense', '0_y': 'other_count'}, inplace=True)
        both_senses = both_senses[(both_senses.base_count+both_senses.other_count) < max_no].reset_index(drop=True)
        print(both_senses)
        return both_senses


def main():
    parser = argparse.ArgumentParser(prog="VUAMC preprocessing.")
    parser.add_argument('path', type=str, help='path/to/VUAMC')
    parser.add_argument('--process', action='store_true',
                        help='Should the data be processed or do you wish to load a preprocessed file? Default False.')
    parser.add_argument("--min", dest="minima", nargs=2, type=int, help="The minimum number of occ for s1 and s2.")
    parser.add_argument("--max", dest="maxima", default=10000, type=int, help="The maximal number of occ of a target.")
    parser.add_argument("--pos", dest="pos", default=['NOUN', 'VERB', 'ADJ'], type=str, nargs="+",
                        help="The universal POS classes to consider.")

    args = parser.parse_args()

    if args.process:
        processor = VuamcProcessor(f'{args.path}/VUAMC.xml')
        processor.corpus_size_tests()
        print(processor.corpus)
        processor.df_to_csv(f'{args.path}/VUAMC_preprocessed_new.csv')
    else:
        processor = VuamcProcessor(f'{args.path}/VUAMC_preprocessed_new.csv', process_data=False)
    if args.minima:
        processor.retrieve_possible_targets(args.minima[0], args.minima[1], args.pos, max_no=args.maxima). \
            to_csv(f'{args.path}/possible_targets_metaphor_{args.minima[0]}-{args.minima[1]}_{args.pos}.csv')


if __name__ == "__main__":
    main()
