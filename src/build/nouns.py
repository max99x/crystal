import itertools
import nltk.corpus
import ext.plural
import base


IGNORE_UNCOMMON = False
IGNORE_PROPER_MULTIWORD = False
IGNORE_NON_PROPER_MULTIWORD = True
IGNORE_ALL_MULTIWORD = IGNORE_PROPER_MULTIWORD and IGNORE_NON_PROPER_MULTIWORD

UNCOUNTABLE_SYNSETS = set([
    nltk.corpus.wordnet.synset('substance.n.01'),
    nltk.corpus.wordnet.synset('substance.n.04'),
    nltk.corpus.wordnet.synset('substance.n.07'),
    nltk.corpus.wordnet.synset('data.n.01'),
    nltk.corpus.wordnet.synset('information.n.01'),
    nltk.corpus.wordnet.synset('system_of_measurement.n.01'),
    nltk.corpus.wordnet.synset('feeling.n.01'),
    nltk.corpus.wordnet.synset('quality.n.01'),
    nltk.corpus.wordnet.synset('event.n.01'),
    nltk.corpus.wordnet.synset('state.n.02'),
])
AMBIGUOUS_COUNTABILITY_SYNSETS = set([
    nltk.corpus.wordnet.synset('food.n.01'),
    nltk.corpus.wordnet.synset('food.n.02'),
    nltk.corpus.wordnet.synset('event.n.01'),
    nltk.corpus.wordnet.synset('state.n.02'),
])
MALE_SYNSETS = set([
    nltk.corpus.wordnet.synset('male.n.02'),
    nltk.corpus.wordnet.synset('actor.n.01'),
    nltk.corpus.wordnet.synset('husband.n.01'),
    nltk.corpus.wordnet.synset('father.n.01'),
    nltk.corpus.wordnet.synset('brother.n.01'),
    nltk.corpus.wordnet.synset('son.n.01'),
    nltk.corpus.wordnet.synset('king.n.01'),
    nltk.corpus.wordnet.synset('prince.n.01'),
])
FEMALE_SYNSETS = set([
    nltk.corpus.wordnet.synset('female.n.02'),
    nltk.corpus.wordnet.synset('woman.n.01'),
    nltk.corpus.wordnet.synset('wife.n.01'),
    nltk.corpus.wordnet.synset('actress.n.01'),
    nltk.corpus.wordnet.synset('female_aristocrat.n.01'),
    nltk.corpus.wordnet.synset('mother.n.01'),
    nltk.corpus.wordnet.synset('sister.n.01'),
    nltk.corpus.wordnet.synset('daughter.n.01'),
    nltk.corpus.wordnet.synset('queen.n.01'),
    nltk.corpus.wordnet.synset('princess.n.01'),
])
NONPERSON_SYNSETS = set([
    nltk.corpus.wordnet.synset('animal.n.01'),
    nltk.corpus.wordnet.synset('artifact.n.01'),
    nltk.corpus.wordnet.synset('abstraction.n.06'),
])
PERSON_SYNSET = nltk.corpus.wordnet.synset('person.n.01')
EXCEPTIONS = set(['he', 'be', 'an', 'no'])


def WriteRules(outfile):
  for synset in nltk.corpus.wordnet.all_synsets(nltk.corpus.wordnet.NOUN):
    if IGNORE_ALL_MULTIWORD and all('_' in i for i in synset.lemma_names):
      continue
    WriteSynset(outfile, synset)


def WriteSynset(outfile, synset):
  hypernyms = GetAllHypernyms(synset)
  if IsProperNoun(synset, hypernyms):
    gender = GetProperNounGender(synset)
    for lemma in synset.lemmas:
      WriteProperNoun(outfile, lemma, gender)
  else:
    uncountable = IsUncountable(synset, hypernyms)
    if uncountable in (True, None):
      for lemma in synset.lemmas:
        WriteNoun(outfile, lemma, 'n', 'ms')
    if uncountable in (False, None):
      gender = GetNounGender(hypernyms)
      for lemma in synset.lemmas:
        WriteNoun(outfile, lemma, gender, 'sg')
        for plural in Pluralize(lemma.name):
          WriteNoun(outfile, lemma, gender, 'pl', plural)


def Pluralize(noun):
  return set([ext.plural.noun_plural(noun, classical=True),
              ext.plural.noun_plural(noun, classical=False)])


def ShouldBeIgnored(lemma):
  return ((IGNORE_PROPER_MULTIWORD and '_' in lemma.name) or
          (IGNORE_UNCOMMON and not base.GetCompoundCount(lemma)) or
          lemma.name in EXCEPTIONS or
          len(lemma.name) == 1)


def WriteProperNoun(outfile, lemma, gender):
  if ShouldBeIgnored(lemma): return
  
  noun = base.LemmaToTerminals(lemma.name)
  count = base.GetCompoundCount(lemma) - 1
  if gender:
    outfile.write('PrpN[NUM=sg,SNS="%s",SEX=%s,FRQ=%d] -> %s\n' %
                  (lemma.synset.name, gender, count, noun))
  else:
    outfile.write('PrpN[NUM=sg,SNS="%s",FRQ=%d] -> %s\n' %
                  (lemma.synset.name, count, noun))


def WriteNoun(outfile, lemma, gender, number, name_override=None):
  if ShouldBeIgnored(name_override or lemma): return
  
  noun = base.LemmaToTerminals(name_override or lemma.name)
  count = base.GetCompoundCount(lemma)
  if gender:
    outfile.write('Noun[NUM=%s,SNS="%s",SEX=%s,FRQ=%s] -> %s\n' %
                  (number, lemma.synset.name, gender, count, noun))
  else:
    outfile.write('Noun[NUM=%s,SNS="%s",FRQ=%s] -> %s\n' %
                  (number, lemma.synset.name, count, noun))


def GetAllHypernyms(synset):
  return set(itertools.chain(*synset.hypernym_paths()))


def IsUncountable(synset, hypernyms):
  uncountable = bool(UNCOUNTABLE_SYNSETS.intersection(hypernyms) or
                     any(i.endswith('ness') for i in synset.lemma_names))
  if uncountable and AMBIGUOUS_COUNTABILITY_SYNSETS.intersection(hypernyms):
    return None
  else:
    return uncountable


def IsProperNoun(synset, hypernyms):
  if not synset.hyponyms():
    return bool(len(hypernyms) == 1 and synset.instance_hypernyms())


def GetProperNounGender(synset):
  cls = synset.instance_hypernyms()[0]
  cls_hypernyms = GetAllHypernyms(cls)
  if PERSON_SYNSET in cls_hypernyms:
    if cls_hypernyms.intersection(MALE_SYNSETS):
      return 'm'
    elif cls_hypernyms.intersection(FEMALE_SYNSETS):
      return 'f'
    else:
      return None
  else:
    return 'n'


def GetNounGender(hypernyms):
  if NONPERSON_SYNSETS.intersection(hypernyms):
    return 'n'
  elif MALE_SYNSETS.intersection(hypernyms):
    return 'm'
  elif FEMALE_SYNSETS.intersection(hypernyms):
    return 'f'
