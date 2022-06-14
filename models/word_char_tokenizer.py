from abc import ABCMeta, abstractmethod
from typing import List

from tokenizers import Tokenizer
from tokenizers.normalizers import NFKC
from tokenizers.models import WordLevel
from tokenizers.trainers import WordLevelTrainer
from tokenizers.pre_tokenizers import WhitespaceSplit
from tokenizers.processors import TemplateProcessing
from nltk.tokenize import word_tokenize

from models.common import SpecialTokens, all_special_tokens


class CPreTokenizer(metaclass=ABCMeta):
    @abstractmethod
    def pre_tokenize(self, sequence: str) -> str:
        pass


class PreWordTokenizer(CPreTokenizer):
    def __init__(self):
        super().__init__()
        self.normalizer = NFKC()

    def pre_tokenize(self, sequence: str) -> List[str]:
        # strip() -> Normalize NFC -> nltk tokenizer
        sequence = sequence.strip()
        sequence = self.normalizer.normalize_str(sequence)

        # The word_tokenize func changes " into `` and '' by default
        tokens = word_tokenize(sequence)
        for i in range(len(tokens)):
            if tokens[i] == "``" or tokens[i] == "''" or \
                    tokens[i] == '”' or tokens[i] == '“':
                tokens[i] = '"'
        return tokens


class PreCharTokenizer(CPreTokenizer):
    def __init__(self):
        super().__init__()
        self.normalizer = NFKC()

    def pre_tokenize(self, sequence: str) -> List[str]:
        # strip() -> Normalize NFC -> nltk tokenizer
        sequence = sequence.strip()
        sequence = self.normalizer.normalize_str(sequence)

        if sequence in all_special_tokens:
            return [sequence]

        tokens = [c for c in sequence
                  if c != ' ' and c != '”' and c != '“']
        return tokens


def read_file_generator(corpus_path: str, pre_tokenizer: CPreTokenizer):
    with open(corpus_path) as fp:
        while True:
            line = fp.readline()
            if not line:
                break

            yield pre_tokenizer.pre_tokenize(line)


def create_tokenizer(corpus_path: str,
                     pre_tokenizer: CPreTokenizer,
                     vocab_size: int,
                     min_frequency: int,
                     save_path: str):
    corpus_generator = read_file_generator(corpus_path, pre_tokenizer)

    tokenizer = Tokenizer(WordLevel(unk_token="[UNK]"))
    tokenizer.enable_padding(
        direction="right",
        pad_id=0,
        pad_type_id=0,
        pad_token=SpecialTokens.pad
    )
    tokenizer.pre_tokenizer = WhitespaceSplit()
    tokenizer.post_processor = TemplateProcessing(
        single=f"{SpecialTokens.cls} $A {SpecialTokens.sep}",
        pair=f"{SpecialTokens.cls} $A {SpecialTokens.sep} $B:1 {SpecialTokens.sep}:1",
        # Special tokens at index 2 and 3
        special_tokens=[
            (SpecialTokens.cls, 2),
            (SpecialTokens.sep, 3),
        ],
    )
    trainer = WordLevelTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        show_progress=True,
        special_tokens=[SpecialTokens.pad, SpecialTokens.unk, SpecialTokens.cls, SpecialTokens.sep])
    tokenizer.train_from_iterator(corpus_generator, trainer=trainer)
    tokenizer.save(save_path)


if __name__ == '__main__':
    create_tokenizer("data/corpus_small.txt",
                     PreCharTokenizer(),
                     300, 10,
                     "spell_model/char_tokenizer.json")
    create_tokenizer("data/corpus_small.txt",
                     PreWordTokenizer(),
                     300, 3,
                     "spell_model/word_tokenizer.json")

    # # Load from transformers library as follows
    # from transformers import PreTrainedTokenizerFast
    # tokenizer = PreTrainedTokenizerFast(tokenizer_file="spell_model/word_tokenizer.json")
