import re
import nltk.corpus


def SplitLemma(lemma):
  if hasattr(lemma, 'name'):
    lemma = lemma.name
  lemma = lemma.lower()
  lemma = re.sub(r"(\'[-\w]+)", r'_\1_', lemma)
  return re.split('_+', lemma.strip('_'))


def LemmaToTerminals(lemma):
  return ' '.join('"%s"' % i for i in SplitLemma(lemma))


def GetCompoundCount(lemma):
  pieces = SplitLemma(lemma)
  if len(pieces) == 1:
    return lemma.count()
  else:
    get_lemmas = nltk.corpus.wordnet.lemmas
    pieces_counts = [max([0] + [i.count() for i in get_lemmas(piece)])
                     for piece in pieces]
    return lemma.count() + sum(pieces_counts)
