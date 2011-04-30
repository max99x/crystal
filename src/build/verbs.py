# NOTE: As of writing, this requires VerbNet 3.1 while the NLTK repository
# uses 2.1. The new version has to be downloaded and replaced manually.

import collections
import cPickle as pickle
import nltk.corpus
import base


VERBS_LIST = 'data/verbs.pickle'
VERB_TEMPLATE = 'Verb[FORM=%s,PTRN=%d,CLS="%s",SNS="%s",FRQ=%d] -> %s'
CV_TEMPLATE = 'CV[PTRN=%d,NUM=?n,PER=?p,TENS=?t]'
VP_TEMPLATE = 'VP[NUM=?n,PER=?p,TENS=?t] -> %s'
VPQ_TEMPLATE = 'VPQ[NUM=?n,PER=?p,TENS=?t,TRGT=%d,PTCL=%s] -> %s'
PREP_TEMPLATE = 'Prep[TYP=spatial,%s]'
VERB_FORMS = ('inf', 'tps', 'ger', 'pret', 'pp')


class VerbNetError(Exception): pass


def HandleLex(node, *_):
  value = node.attrib['value'].replace('[+be]', '').strip()
  if value:
    return [base.LemmaToTerminals(i) for i in value.split()]
  else:
    return []


def HandlePrep(node, *_):
  if 'value' in node.attrib:
    return HandleLex(node)
  elif node.findall('.//SELRESTR'):
    restrictions = node.findall('.//SELRESTR')
    args = [r.attrib['Value'] + r.attrib['type'] for r in restrictions]
    if len(args) == 1:
      return PREP_TEMPLATE % args[0]
    elif node.find('.//SELRESTRS').attrib.get('logic') == 'or':
      return [PREP_TEMPLATE % i for i in args]
    else:
      return PREP_TEMPLATE % ','.join(args)
  else:
    raise VerbNetError('Unexpected generic preposition.')


def HandleNp(node, *_):
  # TODO: Deal with syntactic restrictions (inc. and/or), e.g. get-13.5.1.
  #       See HandlePrep.
  return 'NP'


def FlattenRule(rule):
  for i, node in enumerate(rule):
    if not isinstance(node, basestring):
      if node:
        for choice in node:
          for product in FlattenRule(rule[:i] + (choice,) + rule[i + 1:]):
            yield product
      else:
        for product in FlattenRule(rule[:i] + rule[i + 1:]):
          yield product
      return
  yield rule


def GetBasicSentenceRules():
  for cls in nltk.corpus.verbnet.classids():
    frames = nltk.corpus.verbnet.vnclass(cls).findall('FRAMES/FRAME')
    for index, frame in enumerate(frames):
      syntax = frame.find('SYNTAX')
      rule = tuple(HANDLERS[node.tag](node, cls)
                   for node in syntax.getchildren())
      for r in FlattenRule(rule):
        yield cls, index, r, frame.find('.//EXAMPLE').text


def GetFramePatterns():
  patterns = collections.defaultdict(lambda: collections.defaultdict(set))
  for cls, frame_index, rule, example in GetBasicSentenceRules():
    # TODO: Stop ignoring adverbs.
    if 'Adv' in rule: continue
    # TODO: Deal with patterns not starting with "NP".
    if not (rule[0].startswith('NP') and rule[1].startswith('CV')): continue
    for index, node in enumerate(rule):
      if node.startswith('CV'):
        generic_rule = rule[:index] + ('CV',) + rule[index + 1:]
        patterns[generic_rule][cls].add(frame_index)
        break

  return [(i, j, dict(k)) for i, (j, k) in enumerate(patterns.items())]


def PrepareVPRule(rule, index):
  return ' '.join(rule[1:]).replace('CV', CV_TEMPLATE % index)


def MakeQuestionRule(index, rule, node_index, preposition=None):
  rule = list(rule)
  if preposition:
    del rule[node_index - 1:node_index + 1]
    if preposition.startswith("Prep"):
      preposition = 'PREP,' + preposition[17:-1]
    else:
      preposition = preposition.replace('"', '')
      preposition = preposition.replace(' ', '_').replace("'", '_')
  else:
    del rule[node_index:node_index + 1]
    preposition = 'NONE'

  return VPQ_TEMPLATE % (node_index, preposition, PrepareVPRule(rule, index))


def GetQuestionRules(patterns):
  rules = []
  
  # Verb phrase rules for object questions.
  for index, rule, _ in patterns:
    for node_index, node in enumerate(rule[1:]):
      node_index += 1
      if node.startswith('NP'):
        rules.append(MakeQuestionRule(index, rule, node_index))

        previous = rule[node_index - 1]
        if previous.startswith('"') or previous.startswith('Prep'):
          rules.append(MakeQuestionRule(index, rule, node_index, previous))

  return rules


def GetSentenceRules(patterns):
  rules = []
  
  # Verb phrase rules.
  for index, rule, _ in patterns:
    rules.append(VP_TEMPLATE % PrepareVPRule(rule, index))

  return rules  


def GetVerbRules(patterns):
  conjugation = pickle.load(open(VERBS_LIST))
  rules = []

  with_children = collections.defaultdict(set)
  for cls in nltk.corpus.verbnet.classids():
    if cls.count('-') > 1:
      name, number, suffix = cls.split('-', 2)
      base_class = name + '-' + number
      
      for number in suffix.split('-'):
        with_children[base_class].add(cls)
        base_class += '-' + number
      with_children[base_class].add(cls)
    else:
      with_children[cls].add(cls)
  
  for index, pattern, classes in patterns:
    for cls in classes:
      for frame_cls in with_children[cls]:
        frame_cls = nltk.corpus.verbnet.vnclass(frame_cls)
        for member in frame_cls.findall('MEMBERS/MEMBER'):
          verb = member.attrib['name']
          lemmas = member.attrib['wn'].replace('?', '').split()
          if lemmas:
            lemmas = [nltk.corpus.wordnet.lemma_from_key(i + '::')
                      for i in lemmas]
          else:
            lemmas = nltk.corpus.wordnet.lemmas(verb, 'v')
            if len(lemmas) > 1:
              lemmas = []
          for lemma in lemmas:
            synset = lemma.synset.name
            count = base.GetCompoundCount(lemma)
            if verb not in conjugation: continue
            for form, conjugated_verb in zip(VERB_FORMS, conjugation[verb]):
              conjugated_verb = base.LemmaToTerminals(conjugated_verb)
              args = (form, index, cls, synset, count, conjugated_verb)
              rules.append(VERB_TEMPLATE % args)

  return rules


def WriteRules(rules_file, patterns_file):
  patterns = GetFramePatterns()
  sentence_rules = GetSentenceRules(patterns)
  question_rules = GetQuestionRules(patterns)
  verb_rules = GetVerbRules(patterns)

  pickle.dump(patterns, patterns_file)

  for ruleset in (sentence_rules, question_rules, verb_rules):
    for rule in ruleset:
      rules_file.write(rule)
      rules_file.write('\n')
    rules_file.write('\n')


HANDLERS = {
  'LEX': HandleLex,
  'PREP': HandlePrep,
  'NP': HandleNp,
  'VERB': lambda _, cls: 'CV[CLS="%s"]' % cls,
  'ADV': lambda *_: 'Adv',
  'ADJ': lambda *_: 'AJP'
}
