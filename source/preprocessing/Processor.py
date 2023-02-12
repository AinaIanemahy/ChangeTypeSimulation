from abc import ABC, abstractmethod
from xml.etree import ElementTree
from nltk.tag import mapping
import pandas as pd


class Processor(ABC):
    """

    Parameters
    ----------
    file_path: str
        The `path/to/the.xml`.
    process_data: bool, default=True
        Is the file path the path to a xml that should be processed (True),
         or is in a csv that should only be loaded (False).
    """

    def __init__(self, file_path: str | None, process_data: bool = False):
        if process_data:
            if file_path is not None:
                self._file_path: str = file_path
                self._element_tree: ElementTree = self.read_xml()
            self.corpus: pd.DataFrame = pd.DataFrame(self.iterate_element_tree())
        else:
            self.corpus = pd.read_csv(file_path)

    def read_xml(self) -> ElementTree:
        """
        Calls etree parse() on the given path.

        Returns
        -------
        xml.etree.ElementTree
            The xml parsed as an element tree.
        """
        return ElementTree.parse(self._file_path)

    def df_to_csv(self, path: str):
        """
        Saves the processor's data table to csv.

        Parameters
        ----------
        path
            Like `path/to/wimcor_preprocessed.csv`
        """
        print(f"Saving to {path}.")
        self.corpus.to_csv(path)

    @staticmethod
    def map_pos_tag(tag: str, mapper: str) -> str | None:
        """
        Maps the PTB part-of-speech tag to the corresponding universal tag. Double annotations are kept as is.

        Parameters
        ----------
        mapper
        tag: str
            The tag.

        Returns
        -------
        str
            The mapped universal tag. If the original tag is undecided between two classes (like VVD-AJ0) this is 'UND'.
        """
        universal_tag = mapping.map_tag(mapper, 'universal', tag)
        # all tags not in the dict are assigned 'X' in mapping, this filters some 'X'
        if universal_tag == 'X' and tag not in ['ITJ', 'UNC']:
            if tag is not None and '-' in tag:
                return 'UND'  # tag undecided for words with combined tags like VVD-AJ0
            return tag
        return universal_tag

    @abstractmethod
    def iterate_element_tree(self):
        pass

    @abstractmethod
    def retrieve_possible_targets(self, no_base: int, no_other: int, no_max: int = None, pos: list = None) \
            -> pd.DataFrame:
        pass

