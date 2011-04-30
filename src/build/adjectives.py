import cPickle as pickle
import nltk.corpus
import verbs
import base


QUANTIFIERS = set([
  'all', 'any', 'both', 'each', 'every', 'few', 'less', 'many', 'most',
  'a lot of', 'some', 'several', 'a few', 'a couple of', 'no'
])
INCOMPARABLE_ADJECTIVES = set([
  'perfect', 'unique', 'fatal', 'universal', 'dead', 'wrong', 'straight',
  'blind', 'final', 'vertical', 'right', 'left', 'such'
])
IRREGULAR_ADJECTIVES = {
  'good': ('better', 'best'),
  'well': ('better', 'best'),
  'bad': ('worse', 'worst'),
  'ill': ('worse', 'worst'),
  'evil': ('worse', 'worst'),
  'little': (('less', 'lesser'), 'least'),
  'much': ('more', 'most'),
  'old': (('older', 'elder'), ('oldest', 'eldest')),
  'nigh': ('nigher', 'nighest'),
  'near': ('nearer', 'nearest'),
  'far': (('farther', 'further'), ('farthest', 'furthest')),
  'late': (('later', 'latter'), ('latest', 'last')),
  'hind': ('hinder', ('hindmost', 'hindermost')),
  'upper': ('upper', ('upmost', 'uppermost')),
  'inner': ('inner', ('inmost', 'innermost')),
  'outer': (('outer', 'utter'), ('outmost', 'outermost', 'utmost', 'uttermost')),
  'clever': (('cleverer', 'more clever'), ('cleverest', 'most clever')),
  'gentle': (('gentler', 'more gentle'), ('gentlest', 'most gentle')),
  'friendly': (('friendlier', 'more friendly'), ('friendliest', 'most friendly')),
  'quiet': (('quieter', 'more quiet'), ('quietest', 'most quiet')),
  'simple': (('simpler', 'more simple'), ('simpler', 'most simple')),
  'beat': ('more beat', 'most beat'),
}
CMU_DICTIONARY = nltk.corpus.cmudict.dict()
VOWELS = set('aeiou')
DOUBLEABLE = set('bdgfhkjmlnpsrtvz')
PAST_PARTICIPLES = set(
    i[-1] for i in pickle.load(open(verbs.VERBS_LIST)).values())


def WriteRules(outfile):
  for synset in nltk.corpus.wordnet.all_synsets(nltk.corpus.wordnet.ADJ):
    # Skip quantifiers.
    if QUANTIFIERS.intersection(synset.lemma_names): continue
    # Skip numbers.
    if any(i[0].isdigit() for i in synset.lemma_names): continue

    WriteRule(outfile, synset)


def WriteRule(outfile, synset):
  for lemma in synset.lemmas:
    adjective = lemma.name.replace('_', ' ')

    standard = True
    # Check for abbreviations.
    if '.' in adjective or adjective.isupper(): standard = False
    # Check for incomparable adjective.
    if adjective in INCOMPARABLE_ADJECTIVES: standard = False
    # Check for proper adjective.
    if adjective.title() in ' '.join(synset.examples).split(): standard = False

    # Generate comparative and superlative.
    comparatives = superlatives = ()
    if standard:
      if adjective in IRREGULAR_ADJECTIVES:
        comparatives, superlatives = IRREGULAR_ADJECTIVES[adjective]
        if isinstance(comparatives, basestring): comparatives = [comparatives]
        if isinstance(superlatives, basestring): superlatives = [superlatives]
        standard = False
      else:
        conjugated = Conjugate(adjective)
        if conjugated:
          comparatives, superlatives = [[i] for i in conjugated]
          standard = False

    # Write ordinary positive adjective.
    WriteAdjective(outfile, 'pos', lemma, adjective, standard)

    # Write comparative and superlative adjectives if any.
    for comparative in comparatives:
      WriteAdjective(outfile, 'cmp', lemma, comparative)
    for superlative in superlatives:
      WriteAdjective(outfile, 'sup', lemma, superlative)


def WriteAdjective(outfile, degree, lemma, adjective, standard=None):
  synset = lemma.synset.name
  count = base.GetCompoundCount(lemma)
  standard = '+' if standard else '-'
  terminals = base.LemmaToTerminals(adjective)
  outfile.write('Adj[DEG=%s,SNS="%s",FRQ=%d,%sstd] -> %s\n' %
                (degree, synset, count, standard, terminals))


def Conjugate(adjective):
  if (' ' in adjective or
      '-' in adjective or
      "'" in adjective or
      adjective in PAST_PARTICIPLES or
      adjective.endswith('ed')):
    return
  else:
    syllables = SyllableCount(adjective)
    assert syllables > 0, adjective
    if syllables == 1:
      if adjective.endswith('e'):
        comparative = adjective + 'r'
        superlative = adjective + 'st'
      elif (adjective[-1] in DOUBLEABLE and
            adjective[-2] in VOWELS and
            (len(adjective) < 3 or adjective[-3] not in VOWELS)):
        comparative = adjective + adjective[-1] + 'er'
        superlative = adjective + adjective[-1] + 'est'
      else:
        comparative = adjective + 'er'
        superlative = adjective + 'est'
    elif syllables == 2:
      if adjective.endswith('y') and adjective[-2] not in VOWELS:
        comparative = adjective[:-1] + 'ier'
        superlative = adjective[:-1] + 'iest'
      elif adjective[-2:] in ('er', 'le', 'ow'):
        comparative = adjective + 'er'
        superlative = adjective + 'est'
      else:
        return
    else:
      return

    return comparative, superlative


def SyllableCount(word):
  assert ' ' not in word, word
  if word in CMU_DICTIONARY:
    return max(len([phonem for phonem in pronunciation if phonem[-1].isdigit()])
               for pronunciation in CMU_DICTIONARY[word])
  else:
    vowels_count = len([c for c in word if c in VOWELS])
    if word.endswith('y') and word[-2] not in VOWELS:
      vowels_count += 1
    return vowels_count
