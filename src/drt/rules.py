import collections
import cPickle as pickle
import os
import nltk.corpus
import cfg_parser
import logic
import drt.resolve
from drs import *


PATTERNS_PATH = 'data/patterns.pickle'


_PERSON_SYNSET = 'person.n.01'
_MALE_SYNSETS = [
  'male.n.02',
  'man.n.01',
  'guy.n.01',
  'chap.n.01',
]
_FEMALE_SYNSETS = [
  'female.n.02',
  'woman.n.01',
  'girl.n.01',
  'girl.n.05',
  'lady.n.01',
]
_RESTRICTION_SYNSETS = {
  'abstract': ( ['abstraction.n.06'],
                ['physical_entity.n.01']),
  'animal': ( ['animal.n.01'],
              ['person.n.01',
               'natural_object.n.01',
               'item.n.03',
               'assembly.n.05',
               'artifact.n.01']),
  'animate': ( ['living_thing.n.01'],
               ['abstraction.n.06',
                'natural_object.n.01',
                'item.n.03',
                'assembly.n.05',
                'artifact.n.01']),
  'body_part': ( ['body_part.n.01'],
                 ['abstraction.n.06',
                  'living_thing.n.01']),
  'comestible': ( ['food.n.01'],
                  ['abstraction.n.06',
                   'person.n.01',
                   'artifact.n.01']),
  'communication': ( ['communication.n.02'],
                     ['physical_entity.n.01']),
  'concrete': ( ['physical_entity.n.01'],
                ['abstraction.n.06']),
  'currency': ( ['monetary_unit.n.01'],
                ['physical_entity.n.01']),
  'elongated': ( [],
                 ['abstraction.n.06',
                  'living_thing.n.01']),
  'force': ( ['force.n.02'],
             ['living_thing.n.01']),
  'garment': ( ['garment.n.01'],
               ['abstraction.n.06',
                'living_thing.n.01']),
  'human': ( ['person.n.01'],
             ['abstraction.n.06',
              'animal.n.01',
              'natural_object.n.01',
              'item.n.03',
              'assembly.n.05',
              'artifact.n.01']),
  'int_control': ( ['living_thing.n.01',
                    'instrumentality.n.03',
                    'force.n.02'],
                   []),
  'machine': ( ['instrumentality.n.03'],
               ['abstraction.n.06',
                'living_thing.n.01']),
  'nonrigid': ( [],
                ['abstraction.n.06',
                 'living_thing.n.01']),
  'organization': ( ['organization.n.01'],
                    ['physical_entity.n.01',
                     'communication.n.02',
                     'otherworld.n.01',
                     'psychological_feature.n.01',
                     'attribute.n.02',
                     'set.n.02',
                     'measure.n.02']),
  'pointy': ( [],
              ['abstraction.n.06',
               'living_thing.n.01']),
  'shape': ( [],
             ['abstraction.n.06',
              'living_thing.n.01']),
  'solid': ( [],
             ['abstraction.n.06',
              'living_thing.n.01']),
  'sound': ( ['auditory_communication.n.01',
              'sound.n.04'],
             ['physical_entity.n.01',
              'otherworld.n.01',
              'group.n.01',
              'attribute.n.02',
              'set.n.02',
              'measure.n.02']),
  'state': ( ['state.n.02'],
             ['physical_entity.n.01']),
  'substance': ( ['substance.n.01'],
                 ['abstraction.n.06',
                  'living_thing.n.01']),
  'time': ( ['time_period.n.01',
             'clock_time.n.01'],
            ['physical_entity.n.01',
             'otherworld.n.01',
             'group.n.01',
             'attribute.n.02',
             'set.n.02',
             'communication.n.02']),
  'vehicle': ( ['vehicle.n.01'],
               ['abstraction.n.06',
                'living_thing.n.01'])
}


_patterns = None
_strict_mode = False


class EvaluatorError(Exception): pass


def ReloadPatterns(path=PATTERNS_PATH):
  global _patterns
  _patterns = pickle.load(open(path))


def Evaluate(tree):
  key = tree.node.get('RUL', tree.node.get(cfg_parser._TYPE_FEATURE))
  return _RULE_HANDLERS[key](tree)


def Unimplemented(tree):
  raise NotImplementedError('Handler not implemented for %s' % tree)


def Passthrough(tree):
  return Evaluate(tree[0])


def CreateImplicator(noun_application, verb_application, ref=None):
  ref = ref or Referent()
  antecedent = DRS([ref]) + noun_application(ref)
  return DRS([], [ImplicationCondition(antecedent, verb_application(ref))])


def ReferentTypeFromNumber(number):
  if number == 'pl':
    return PLURAL_TYPE
  elif number == 'ms':
    return MASS_TYPE
  else:
    return SINGULAR_TYPE


def MergeLiterals(tree):
  index = 1
  while index < len(tree):
    if (isinstance(tree[index - 1], basestring) and
        isinstance(tree[index], basestring)):
      tree.pop(index)
    else:
      index += 1


def MakeRestrictionDRS(restriction, ref, negated):
  drs = DRS()
  if restriction in _RESTRICTION_SYNSETS:
    pos_preds, neg_preds = _RESTRICTION_SYNSETS[restriction]

    for predicate in pos_preds:
      cond = PredicateCondition(predicate, ref, informative=False)
      cond.informative = False
      if drs.conditions:
        drs = DRS([], [AlternationCondition(drs, cond, informative=False)])
      else:
        drs.AddCondition(cond)

    if negated:
      if drs:
        drs = DRS([], [NegationCondition(drs, informative=False)])
    else:
      for predicate in neg_preds:
        cond = PredicateCondition(predicate, ref, informative=False)
        cond.informative = False
        drs.AddCondition(NegationCondition(cond, informative=False))

  return drs


def GetGenderConditions(tree, ref):
  sex = tree.node.get('SEX')
  if isinstance(sex, basestring):
    assert sex in ('n', 'm', 'f'), sex
    if sex == 'n':
      person_cond = PredicateCondition(_PERSON_SYNSET, ref, informative=False)
      conds = [NegationCondition(person_cond, informative=False)]
    else:
      conds = GetHypernymConditions(_PERSON_SYNSET, ref)
      # TODO: Multiple synsets for gender are a hack. Switch to something more
      # semantically sound.
      if sex == 'm':
        matching = _MALE_SYNSETS
        nonmatching = _FEMALE_SYNSETS
      else:
        matching = _FEMALE_SYNSETS
        nonmatching = _MALE_SYNSETS
        
      for name in matching:
        conds += GetHypernymConditions(name, ref)
        
      for name in nonmatching:
        predicate = PredicateCondition(name, ref, informative=False)
        conds.append(NegationCondition(predicate, informative=False))
  else:
    conds = []

  return conds


def GetHypernymConditions(synset, ref):
  alternatives = []
  synset = nltk.corpus.wordnet.synset(synset)
  #for path in [sum(synset.hypernym_paths(), [])]:
  for path in synset.hypernym_paths():
    hypernyms = set(i.name for i in path)
    conds = [PredicateCondition(i, ref, informative=False) for i in hypernyms]

    negatives = []

    # TODO: Switch to something more generic.
    if 'abstraction.n.06' in hypernyms:
      negatives += ['physical_entity.n.01']
    elif 'physical_entity.n.01' in hypernyms:
      negatives += ['abstraction.n.06']

    if 'living_thing.n.01' in hypernyms:
      negatives += ['natural_object.n.01', 'artifact.n.01', 'matter.n.03']
    elif 'natural_object.n.01' in hypernyms:
      negatives += ['living_thing.n.01', 'artifact.n.01', 'matter.n.03']
    elif 'artifact.n.01' in hypernyms:
      negatives += ['living_thing.n.01', 'natural_object.n.01', 'matter.n.03']
    elif 'matter.n.03' in hypernyms:
      negatives += ['living_thing.n.01', 'natural_object.n.01', 'artifact.n.01']

    if 'animal.n.01' in hypernyms:
      negatives += ['person.n.01']
    elif 'person.n.01' in hypernyms:
      negatives += ['animal.n.01']

    if 'male.n.02' in hypernyms:
      negatives += ['female.n.02']
    elif 'female.n.02' in hypernyms:
      negatives += ['male.n.02']

    if 'male.n.01' in hypernyms:
      negatives += ['female.n.01']
    elif 'female.n.01' in hypernyms:
      negatives += ['male.n.01']

    if synset.max_depth() > 4:
      if 'living_thing.n.01' not in hypernyms:
        negatives += ['living_thing.n.01', 'person.n.01', 'animal.n.01']
      else:
        if 'person.n.01' not in hypernyms:
          negatives += ['person.n.01']
        if 'animal.n.01' not in hypernyms:
          negatives += ['animal.n.01']

    for negative_synset in set(negatives):
      pred = PredicateCondition(negative_synset, ref, informative=False)
      cond = NegationCondition(pred, informative=False)
      conds.append(cond)

    alternatives.append(conds)

  while len(alternatives) > 1:
    cond = AlternationCondition(DRS([], alternatives[0]),
                                DRS([], alternatives[1]),
                                informative=False)
    alternatives[:2] = [[cond]]

  return alternatives[0]


def GetPossessionConditions(owner, owned):
  possession = PredicateCondition('_possess', owner, owned)
  equality = EqualityCondition(owner, owned, informative=False)
  inequality = NegationCondition(equality, informative=False)
  return [possession, inequality]
  #return [possession]


def IsFragmentConsistent(drs, context=None):
  try:
    if context:
      context = drt.resolve.ResolveStatement(context, None)
    drs = drt.resolve.ResolveStatement(drs, context)
  except drt.resolve.ConsistencyError:
    return False
  
  return logic.IsConsistent(drs)


def MakeConjunctionApplication(left_lambda, conjunction, right_lambda):
  semantics = conjunction.node['SEM']
  def ApplyConjunction(*args):
    left = left_lambda(*args)
    right = right_lambda(*args)

    # TODO: Check whether intermediary resolution for strict mode makes sense.
    
    if semantics == '*cause':
      raise NotImplementedError('Cause understanding is not yet implemented.')
    elif semantics in ('*a&b', 'a&b'):
      # TODO: Implement special handling for temporal semantics (*a&b).
      return left + right
    elif semantics == 'a':
      return left
    elif semantics == 'a&-b':
      return left + DRS([], [NegationCondition(right)])
    elif semantics == 'a|b':
      return DRS([], [AlternationCondition(left, right)])
    elif semantics == '!(a|b)':
      return DRS([], [NegationCondition(AlternationCondition(left, right))])
    elif semantics == '(-a)->b':
      return DRS([], [ImplicationCondition(NegationCondition(left), right)])
    elif semantics == '(-b)->a':
      return DRS([], [ImplicationCondition(NegationCondition(right), left)])
    else:
      raise EvaluatorError('Unknown conjunction semantics: %s' % semantics)

  return ApplyConjunction


def MakeQuestionDeterminer(noun_application):
  def MakeQuestion(verb_application):
    ref = Referent()
    drs = noun_application(ref) + verb_application(ref)
    drs.referents.add(ref)
    return SubjectQuestionDRS(drs, target=ref)
  return MakeQuestion


def EvaluateConjunction(tree):
  left = Evaluate(tree[0])
  right = Evaluate(tree[2])
  conjuncted = MakeConjunctionApplication(left, tree[1], right)
  return conjuncted


def EvaluateCompoundConjunction(tree):
  return EvaluateConjunction(tree[1:])


def EvaluateLambdaConjunction(tree):
  left = Evaluate(tree[0])
  right = Evaluate(tree[2])
  def Conjunct(*args):
    return MakeConjunctionApplication(left(*args), tree[1], right(*args))
  return Conjunct


def EvaluateCompoundLambdaConjunction(tree):
  return EvaluateLambdaConjunction(tree[1:])


def GetVerbnetRestrictions(vnclass):
  role_restrictions = {}
  
  while True:
    for role in vnclass.findall('THEMROLES/THEMROLE'):
      restrictions = role.find('SELRESTRS')
      if restrictions:
        restriction_set = set()
        for restriction in restrictions.findall('SELRESTR'):
          predicate = restriction.attrib
          restriction_set.add((predicate['Value'], predicate['type']))
          
        total = (restrictions.get('logic', 'and'), list(restriction_set))
        role_restrictions[role.attrib['type']] = total

    if vnclass.tag == 'VNCLASS':
      break
    else:
      parent_class = vnclass.attrib['ID'].rsplit('-', 1)[0]
      vnclass = nltk.corpus.verbnet.vnclass(parent_class)

  return role_restrictions


def MakeApplyThemeRole(verb_ref, role, restrictions):
  def ApplyThemeRole(ref):
    role_predicate = '_' + role.rstrip('1234567890')
    conditions = [PredicateCondition(role_predicate, verb_ref, ref)]
    role_drs = DRS([], conditions)

    if restrictions:
      logic, predicates = restrictions
      
      restriction_boxes = []
      for positivity, predicate in predicates:
        restriction_drs = MakeRestrictionDRS(predicate, ref, positivity == '-')
        restriction_boxes.append(restriction_drs)
            
      if logic == 'and':
        total_restriction_drs = sum(restriction_boxes, DRS())
      else:
        total_restriction_drs = restriction_boxes[0]
        for box in restriction_boxes[1:]:
          cond = AlternationCondition(total_restriction_drs, box,
                                      informative=False)
          total_restriction_drs = DRS([], [cond])
    else:
      total_restriction_drs = DRS()

    return role_drs + total_restriction_drs
  return ApplyThemeRole


def MakeVerbnetVerbEvaluator(classname, verb_synset, pattern):
  def EvaluateVerbnetVerb(object_trees):
    MergeLiterals(object_trees)
    
    # Setup main variables.
    vnclass = nltk.corpus.verbnet.vnclass(classname)
    frame_id = min(_patterns[pattern][2][classname])
    frame = vnclass.findall('FRAMES/FRAME')[frame_id]
    verb_ref = Referent(VERB_TYPE)
    restrictions = GetVerbnetRestrictions(vnclass)
    syntax_nodes = frame.findall('SYNTAX/*')
    
    # Define subject.
    subject_role = syntax_nodes[0].attrib['value']
    subject_role_functor = MakeApplyThemeRole(
        verb_ref, 'Agent', restrictions.get(subject_role))
    
    # Collect objects.
    objects_boxes = []
    for role_node, parsed_node in zip(syntax_nodes[2:], object_trees):
      if role_node.tag == 'NP':
        assert 'value' in role_node.attrib
        role = role_node.attrib['value']
        restriction = restrictions.get(role)
        role_functor = MakeApplyThemeRole(verb_ref, role, restriction)
        object = Evaluate(parsed_node)
        objects_boxes.append(object(role_functor))
    
    # Put the object DRSs into the whole of the subject DRS.
    def ApplyVPToSubject(subject):
      verb_conds = [PredicateCondition(verb_synset, verb_ref)]
      verb_conds += GetHypernymConditions(verb_synset, verb_ref)
      verb_drs = DRS([verb_ref], verb_conds)
      subject_drs = subject_role_functor(subject)
      return verb_drs + subject_drs + sum(objects_boxes, DRS())

    return ApplyVPToSubject
  return EvaluateVerbnetVerb


def EvaluateVerbToBe(objects_trees):
  objects_trees = objects_trees[0]
  
  if len(objects_trees) == 1:
    object = objects_trees[0]
    predicate = Evaluate(object)
    object_type = object.node[cfg_parser._TYPE_FEATURE]
    if object_type == 'NP':
      def LinkPredicate(subject):
        return predicate(lambda ref: DRS([], [EqualityCondition(subject, ref)]))
      return LinkPredicate
    elif object_type in ('Adj', 'PP'):
      return predicate
    else:
      raise EvaluatorError('Invalid object for verb to be: %s' % object)
  elif len(objects_trees) == 3:
    adjective = Evaluate(objects_trees[0])
    object = Evaluate(objects_trees[2])
    
    def CompareToObject(subject_ref):
      return object(lambda object_ref: adjective(subject_ref, object_ref))

    return CompareToObject
  else:
    raise EvaluatorError('Invalid objects for verb to be: %s' % objects_trees)


def EvaluateVerbToHave(object_trees):
  assert len(object_trees) == 1
  object = Evaluate(object_trees[0])

  def ApplyPossessee(subject_ref):
    def ApplyPossessor(object_ref):
      return DRS([], GetPossessionConditions(subject_ref, object_ref))
    return object(ApplyPossessor)

  return ApplyPossessee


def EvaluateVerb(tree):
  pattern = int(tree.node[cfg_parser._TYPE_FEATURE].split('_')[1])
  
  if pattern == 991:
    verb_application = EvaluateVerbToBe
  else:
    cls = tree[-1].node['CLS']
    if cls == 'own-100':
      verb_application = EvaluateVerbToHave
    else:
      synset = tree[-1].node['SNS']
      verb_application = MakeVerbnetVerbEvaluator(cls, synset, pattern)

  if tree.node['SEM'] == 'neg':
    original_application = verb_application
    def ApplyNegative(objects):
      original = original_application(objects)
      return lambda ref: DRS([], [NegationCondition(original(ref))])
    verb_application = ApplyNegative

  return verb_application


def EvaluateVerbPhrase(tree):
  verb_functor = Evaluate(tree[0])
  return verb_functor(tree[1:])


def EvaluateSentence(tree):
  # S[TYP=dcl,RUL=1] ->
  #   NP[NUM=?n,CASE=sbj,PER=?p] VP[NUM=?n,PER=?p]
  subject = Evaluate(tree[0])
  vp = Evaluate(tree[1])
  return subject(vp)


def EvaluateSimpleProperName(tree):
  # PN[NUM=?n,SEX=?s,RUL=602] -> PrpN[NUM=?n,SEX=?s]
  name = ' '.join(tree[0]).replace('_', ' ').title().replace(' ', '_')
  ref = NamedReferent(name)
  conds = GetGenderConditions(tree, ref)
  return lambda f: DRS([ref], conds) + f(ref)


def EvaluateCompoundProperName(tree):
  # PN[NUM=?n,SEX=?s,RUL=601] -> Ttl[NUM=?n,SEX=?s] PrpN[NUM=?n,SEX=?s]
  tree = tree.copy(deep=True)
  tree[1][0] = tree[0][0] + ' ' + tree[1][0]
  tree.pop(0)
  return EvaluateSimpleProperName(tree)


def EvaluateArticle(tree):
  # DT[NUM=?n,RUL=401] -> Art[NUM=?n]
  if tree[0].node['definite']:
    return EvaluateDefiniteArticle(tree)
  else:
    return EvaluateIndefiniteArticle()


def EvaluateDefiniteArticle(unused_tree=None):
  def Presuppose(noun_application, verb_application):
    ref = Referent()
    requirements = noun_application(ref)
    cond = ResolutionCondition(ref, requirements, 'presuppose')
    return DRS([], [cond]) + verb_application(ref)
  return Presuppose


def EvaluateIndefiniteArticle(unused_tree=None):
  def CreateReferent(noun_application, verb_application):
    ref = Referent()
    return DRS([ref]) + noun_application(ref) + verb_application(ref)
  return CreateReferent


def EvaluateNegativeDeterminer(unused_tree=None):
  # DT[NUM=?n,RUL=406] -> Det[NUM=?n,TYP=neg]
  def CreateNegator(noun_application, verb_application):
    ref = Referent()
    antecedent = DRS([ref]) + noun_application(ref)
    consequent = DRS([], [NegationCondition(verb_application(ref))])
    return DRS([], [ImplicationCondition(antecedent, consequent)])
  return CreateNegator


def EvaluatePossessivePronounDeterminer(tree):
  # DT[NUM=?n,RUL=408] -> Pro[NUM=?n,CASE=poss_det]
  def PresupposeAndPossess(noun_application, verb_application):
    owner_ref = Referent(ReferentTypeFromNumber(tree.node['NUM']))
    owner_requirements = DRS([], GetGenderConditions(tree[0], owner_ref))
    type = 'pronoun-poss'
    owner_cond = ResolutionCondition(owner_ref, owner_requirements, type)

    owned_ref = Referent()
    possession = GetPossessionConditions(owner_ref, owned_ref)

    requirements = noun_application(owned_ref)
    for cond in possession:
      requirements.AddCondition(cond)
    requirements.AddCondition(owner_cond)
    
    cond = ResolutionCondition(owned_ref, requirements, 'presuppose')
    return DRS([], [cond]) + verb_application(owned_ref)
  return PresupposeAndPossess


def EvaluatePossessiveDeterminer(tree):
  # DT[NUM=?n,RUL=409] -> NP "'s" NP[NUM=?n]
  # DT[NUM=?n,RUL=409] -> NP "'" NP[NUM=?n]
  
  owner_application = Evaluate(tree[0])
  def ApplyPossessee(noun_application, verb_application):
    owned_ref = Referent()
    def ApplyPossessor(owner_ref):
      return DRS([], GetPossessionConditions(owner_ref, owned_ref))
    requirements = noun_application(owned_ref)
    requirements += owner_application(ApplyPossessor)
    cond = ResolutionCondition(owned_ref, requirements, 'presuppose')
    return DRS([], [cond]) + verb_application(owned_ref)
  return ApplyPossessee


def EvaluateAdjectiveChain(tree):
  # AJP[RUL=501] -> Adj AJP
  first = Evaluate(tree[0])
  rest = Evaluate(tree[1])
  return lambda ref, other=None: first(ref, other) + rest(ref, other)


def EvaluateAdjective(tree):
  def ApplyAdjective(ref, other=None):
    pred = tree.node['SNS']
    conds = [PredicateCondition(pred, ref)]
    if tree.node['DEG'] == 'sup':
      conds.append(PredicateCondition(pred + '/sup', ref))
    elif other and tree.node['DEG'] == 'cmp':
      predicate = pred + '/cmp'
      comparison = PredicateCondition(predicate, ref, other)
      reverse = PredicateCondition(predicate, other, ref)
      conds += [comparison, NegationCondition(reverse)]
    return DRS([], conds)
  return ApplyAdjective


def EvaluateUndeterminedNoun(tree):
  # NP[NUM=pl,PER=3,RUL=306] -> Noun[NUM=pl]
  # NP[NUM=ms,PER=3,RUL=307] -> Noun[NUM=ms]
  ref_generator = EvaluateIndefiniteArticle()
  noun_application = Evaluate(tree[0])
  def ApplyVerb(verb_application):
    return ref_generator(noun_application, verb_application)
  return ApplyVerb


def EvaluateNounPhraseWithNounModifier(tree):
  # Noun -> Noun Noun
  modifier_noun = Evaluate(tree[0])
  main_noun = Evaluate(tree[1])
  def ApplyModifier(ref):
    modifier_ref = Referent()
    modification_condition = PredicateCondition('_modify', modifier_ref, ref)
    modification_drs = DRS([modifier_ref], [modification_condition])
    return modification_drs + main_noun(ref) + modifier_noun(modifier_ref)
  return ApplyModifier


def EvaluateUndeterminedNounWithAdjective(tree):
  # NP[NUM=ms,PER=3,RUL=319] -> AJP Noun[NUM=pl]
  # NP[NUM=ms,PER=3,RUL=320] -> AJP Noun[NUM=ms]
  ref_generator = EvaluateIndefiniteArticle()
  adjective_application = Evaluate(tree[0])
  noun_application = Evaluate(tree[1])
  compound_application = lambda ref: (adjective_application(ref) +
                                      noun_application(ref))
  def ApplyVerb(verb_application):
    return ref_generator(compound_application, verb_application)
  return ApplyVerb


def EvaluateDeterminedNoun(tree):
  # NP[NUM=?n,PER=3,RUL=308] -> DT[NUM=?n] Noun[NUM=?n]
  ref_generator = Evaluate(tree[0])
  noun_application = Evaluate(tree[1])
  def ApplyVerb(verb_application):
    return ref_generator(noun_application, verb_application)
  return ApplyVerb


def EvaluateDeterminedNounWithAdjective(tree):
  # NP[NUM=?n,PER=3,RUL=310] -> DT[NUM=?n] AJP Noun[NUM=?n]
  ref_generator = Evaluate(tree[0])
  adjective_application = Evaluate(tree[1])
  noun_application = Evaluate(tree[2])
  compound_application = lambda ref: (adjective_application(ref) +
                                      noun_application(ref))
  def ApplyVerb(verb_application):
    return ref_generator(compound_application, verb_application)
  return ApplyVerb


def EvaluateNounPhraseWithPreposionalPhrase(tree):
  # NP[NUM=?n,CASE=?c,PER=?p,RUL=301] -> NP[NUM=?n,CASE=?c,PER=?p] PP
  noun_phrase = Evaluate(tree[0]) # (x -> d) -> d
  prep_phrase = Evaluate(tree[1]) # x -> d
  
  def ApplyVerb(verb_phrase):
    return noun_phrase(lambda ref: verb_phrase(ref) +prep_phrase(ref))
  
  return ApplyVerb


def EvaluateNoun(tree):
  synset = tree.node['SNS']
  number = tree.node.get('NUM')
  def AddNounCondition(ref):
    ref.type = ReferentTypeFromNumber(number)
    conds = [PredicateCondition(synset, ref)]
    conds += GetGenderConditions(tree, ref)
    conds += GetHypernymConditions(synset, ref)
    return DRS([], conds)
  return AddNounCondition


def EvaluateConditionalSentence(tree):
  # S[TYP=dcl,RUL=2] -> Cond S[TYP=dcl] Pnct[TYP=com] S[TYP=dcl]
  # S[TYP=dcl,RUL=3] -> Cond S[TYP=dcl] Then S[TYP=dcl]
  antecedent = Evaluate(tree[1])
  if _strict_mode and not IsFragmentConsistent(antecedent):
    raise EvaluatorError('An antecedent failed consistency check.')

  consequent = Evaluate(tree[3])
  if _strict_mode and not IsFragmentConsistent(consequent, antecedent):
    raise EvaluatorError('A consequent failed consistency check.')

  return DRS([], [ImplicationCondition(antecedent, consequent)])


def EvaluateAlternativeConditionalSentence(tree):
  # S[TYP=dcl,RUL=4] -> S[TYP=dcl] Cond S[TYP=dcl]
  consequent, cond, antecedent = tree
  return EvaluateConditionalSentence([cond, antecedent, None, consequent])


def EvaluateDeterminedProperNameWithAdjective(tree):
  # NP[NUM=sg,PER=3,RUL=311] -> DT[NUM=sg] AJP PN[NUM=sg]
  adjective_application = Evaluate(tree[1])
  proper_noun_application = Evaluate(tree[2])
  def ApplyAdjectiveAndVerb(verb_application):
    return proper_noun_application(
      lambda ref: adjective_application(ref) + verb_application(ref))
  return ApplyAdjectiveAndVerb


def EvaluateDeterminedProperName(tree):
  # NP[NUM=sg,PER=3,RUL=321] -> DT[NUM=sg] PN[NUM=sg,SEX=n]
  return Evaluate(tree[1])


def EvaluateDeterminedSuperlative(tree):
  # NP[PER=3,RUL=312] -> Art[+definite] Adj[DEG=sup]
  ref_generator = EvaluateDefiniteArticle()
  adjective_application = Evaluate(tree[1])
  def ApplyVerb(verb_application):
    return ref_generator(adjective_application, verb_application)
  return ApplyVerb


def EvaluatePronoun(tree):
  # NP[NUM=?n,CASE=sbj,PER=?p,RUL=305] -> Pro[NUM=?n,CASE=sbj,PER=?p]
  # NP[NUM=?n,CASE=obj,PER=?p,RUL=316] -> Pro[NUM=?n,CASE=obj,PER=?p]
  # NP[NUM=?n,PER=3,RUL=317] -> Pro[NUM=?n,CASE=rflx]
  def PresupposePronoun(verb_application):
    ref = Referent(ReferentTypeFromNumber(tree.node['NUM']))
    requirements = DRS([], GetGenderConditions(tree[0], ref))
    type = 'pronoun-' + tree[0].node['CASE']
    cond = ResolutionCondition(ref, requirements, type)
    return DRS([], [cond]) + verb_application(ref)
  return PresupposePronoun


def EvaluatePossessivePredicatePronoun(tree):
  # NP[NUM=?n,CASE=obj,PER=?p,RUL=318] -> Pro[NUM=?n,CASE=poss_pred,PER=?p]
  presuppose_pronoun = EvaluatePronoun(tree)
  def PresupposeOwnedObject(verb_application):
    owned_ref = Referent()
    def ApplyOwnage(owner_ref):
      return DRS([], [GetPossessionConditions(owner_ref, owned_ref)])
    type = 'pronoun-poss_main'
    cond = ResolutionCondition(owned_ref, presuppose_pronoun(ApplyOwnage), type)
    return DRS([], [cond]) + verb_application(owned_ref)
  return PresupposeOwnedObject


def EvaluatePrepositionalPhrase(tree):
  # PP[TYP=?t,RUL=201] -> Prep[TYP=?t] NP[CASE=obj]
  preposition = '_'.join(tree[0])
  noun_application = Evaluate(tree[1])
  def MakeApplyPreposition(subject_ref):
    def ApplyPreposition(object_ref):
      if tree.node['TYP'] == 'special':
        assert preposition == 'of'
        conds = GetPossessionConditions(object_ref, subject_ref)
      else:
        conds = [PredicateCondition(preposition, subject_ref, object_ref)]
      return DRS([], conds)
    return ApplyPreposition
  return lambda ref: noun_application(MakeApplyPreposition(ref))


def EvaluateNegatedPrepositionalPhrase(tree):
  # PP[TYP=?t,RUL=202,+negated] -> 'not' PP[TYP=?t,-negated]
  predicate = Evaluate(tree[1])
  return lambda ref: DRS([], [NegationCondition(predicate(ref))])


def EvaluateConjunctedSentence(tree):
  # S[TYP=dcl,RUL=11] ->
  #   S[TYP=dcl,-sealed] Conj[+s,-compound] S[TYP=dcl,-sealed]
  left = lambda: Evaluate(tree[0])
  right = lambda: Evaluate(tree[2])
  conjuncted = MakeConjunctionApplication(left, tree[1], right)
  return conjuncted()


def ConvertToQuestion(tree):
  # S[TYP=ynq,RUL=7,+sealed] -> S[TYP=dcl,-sealed] Pnct[TYP=qst]
  sentence = Evaluate(tree[0])
  if not isinstance(sentence, QuestionDRS):
    sentence = BooleanQuestionDRS(sentence)
  return sentence


def EvaluatePredicateYesNoQuestion(tree):
  # S[TYP=ynq,RUL=8] -> AuxV[...,TYP=be] NP[...] PRED
  tree = tree.copy(deep=True)
  
  tree[0].node = tree[0].node.copy()
  tree[0].node[cfg_parser._TYPE_FEATURE] = 'CV_991'
  
  vp_node = nltk.grammar.FeatStructNonterminal(tree[0].node)
  vp_node[cfg_parser._TYPE_FEATURE] = 'VP'
  
  tree[2:3] = [nltk.tree.Tree(vp_node, [tree[0], tree[2]])]
  del tree[:1]
  
  return BooleanQuestionDRS(EvaluateSentence(tree))


def EvaluateNegatedPredicateYesNoQuestion(tree):
  # S[TYP=ynq,RUL=9] -> AuxV[...,TYP=be] NP[...] 'not' PRED
  tree = tree.copy()
  del tree[2:3]
  positive = EvaluatePredicateYesNoQuestion(tree)
  return BooleanQuestionDRS([], [NegationCondition(DRS(positive))])


def EvaluateGenericYesNoQuestion(tree):
  # S[TYP=ynq,RUL=10] -> AuxV[...,TYP=do] NP[...] VP[TENS=i]
  tree = tree.copy()
  del tree[:1]
  return BooleanQuestionDRS(EvaluateSentence(tree))


def EvaluateProform(unused_tree=None):
  # Q[+sbj,RUL=901] -> 'what'
  return MakeQuestionDeterminer(lambda _: DRS())


def EvaluateProformWithNoun(tree=None):
  # Q[+sbj,RUL=902] -> 'what' Noun
  noun_application = Evaluate(tree[1])
  return MakeQuestionDeterminer(noun_application)


def EvaluateProformWithNounAndAdjective(tree=None):
  # Q[+sbj,RUL=903] -> 'what' AJP Noun
  adjective_application = Evaluate(tree[1])
  noun_application = Evaluate(tree[2])
  def ApplyAdjectiveAndNound(ref):
    return adjective_application(ref) + noun_application(ref)
  return MakeQuestionDeterminer(ApplyAdjectiveAndNound)


def EvaluatePossessiveProformWithNoun(tree=None):
  # Q[+sbj,RUL=904] -> 'whose' Noun
  noun_application = Evaluate(tree[1])
  def AssignOwner(verb_application):
    owner_ref = Referent()
    owned_ref = Referent()
    own_conds = GetPossessionConditions(owner_ref, owned_ref)
    
    drs = noun_application(owned_ref) + verb_application(owned_ref)
    drs += DRS([owned_ref, owner_ref], own_conds)
    return SubjectQuestionDRS(drs, owner_ref)
  return AssignOwner


def EvaluatePossessiveProformWithNounAndAdjective(tree=None):
  # Q[+sbj,RUL=905] -> 'whose' AJP Noun
  adjective_application = Evaluate(tree[1])
  noun_application = Evaluate(tree[2])
  def AssignOwner(verb_application):
    owner_ref = Referent()
    owned_ref = Referent()
    own_conds = GetPossessionConditions(owner_ref, owned_ref)
    
    drs = noun_application(owned_ref)
    drs += adjective_application(owned_ref)
    drs += verb_application(owned_ref)
    drs += DRS([owned_ref, owner_ref], own_conds)
    return SubjectQuestionDRS(drs, owner_ref)
  return AssignOwner


def EvaluateObjectQuestion(tree):
  # S[TYP=whq,RUL=12] -> Q AuxV[...] NP[...] VPQ[...]
  tree = tree.copy(deep=False)
  tree[0] = [tree[0]]
  return EvaluateParticledObjectQuestion(tree)


def EvaluateParticledObjectQuestion(tree):
  # S[TYP=whq,RUL=13] -> QM[...] AuxV[...] NP[...] VPQ[...]

  tree = tree.copy(deep=True)
  object_tree = tree[0]
  subject_tree = tree[2]
  vp_tree = tree[3]
  
  target_index = vp_tree.node['TRGT'] - 1
  vp_tree[target_index:target_index] = object_tree
  
  subject = Evaluate(subject_tree)
  vp = Evaluate(vp_tree)

  drs = subject(vp)
  if not isinstance(drs, SubjectQuestionDRS):
    target_ref = None
    for child in drs.Walk():
      if isinstance(child, SubjectQuestionDRS):
        if target_ref:
          raise EvaluatorError('Multiple questions in a single sentence.')
        else:
          target_ref = child.target
    if not target_ref:
      raise EvaluatorError('Question lost during VP construction.')
    drs = SubjectQuestionDRS(drs, target_ref)

  return drs


_RULE_HANDLERS = {
  1: EvaluateSentence,
  2: Passthrough,
  3: EvaluateConditionalSentence,
  4: EvaluateAlternativeConditionalSentence,
  5: EvaluateConjunctedSentence,
  6: lambda tree: EvaluateConjunctedSentence(tree[1:]),
  7: ConvertToQuestion,
  8: EvaluatePredicateYesNoQuestion,
  9: EvaluateNegatedPredicateYesNoQuestion,
  10: EvaluateGenericYesNoQuestion,
  11: EvaluateSentence,
  12: EvaluateObjectQuestion,
  13: EvaluateParticledObjectQuestion,
  201: EvaluatePrepositionalPhrase,
  202: EvaluateNegatedPrepositionalPhrase,
  203: EvaluateConjunction,
  204: EvaluateCompoundConjunction,
  301: EvaluatePronoun,
  302: EvaluatePronoun,
  303: EvaluatePronoun,
  304: EvaluatePossessivePredicatePronoun,
  305: EvaluateUndeterminedNoun,
  306: EvaluateUndeterminedNounWithAdjective,
  307: EvaluateUndeterminedNoun,
  308: EvaluateUndeterminedNounWithAdjective,
  309: EvaluateDeterminedNoun,
  310: Passthrough,
  311: EvaluateDeterminedNounWithAdjective,
  312: EvaluateDeterminedProperNameWithAdjective,
  313: EvaluateDeterminedProperName,
  314: EvaluateDeterminedSuperlative,
  315: EvaluateConjunction,
  316: EvaluateCompoundConjunction,
  317: EvaluateNounPhraseWithPreposionalPhrase,
  318: EvaluateNounPhraseWithNounModifier,
  401: EvaluateArticle,
  402: EvaluateDefiniteArticle,
  403: EvaluateIndefiniteArticle,
  404: EvaluateIndefiniteArticle,
  405: EvaluateIndefiniteArticle,
  406: lambda *_: CreateImplicator,
  407: EvaluateNegativeDeterminer,
  408: EvaluatePossessivePronounDeterminer,
  409: EvaluatePossessiveDeterminer,
  410: EvaluateConjunction,
  411: EvaluateCompoundConjunction,
  501: EvaluateAdjectiveChain,
  502: Passthrough,
  503: EvaluateConjunction,
  504: EvaluateCompoundConjunction,
  505: EvaluateConjunction,
  506: EvaluateCompoundConjunction,
  601: EvaluateCompoundProperName,
  602: EvaluateSimpleProperName,
  701: EvaluateLambdaConjunction,
  702: EvaluateCompoundLambdaConjunction,
  801: EvaluateConjunction,
  802: EvaluateCompoundConjunction,
  901: EvaluateProform,
  902: EvaluateProformWithNoun,
  903: EvaluateProformWithNounAndAdjective,
  904: EvaluatePossessiveProformWithNoun,
  905: EvaluatePossessiveProformWithNounAndAdjective,
  'Noun': EvaluateNoun,
  'Adj': EvaluateAdjective,
  'VP': EvaluateVerbPhrase,
  'VPQ': EvaluateVerbPhrase,
  # Unrolled rules produced in the manually optimized grammar.
  'CV_1': EvaluateVerb,
  'CV_2': EvaluateVerb,
  'CV_3': EvaluateVerb,
  'CV_4': EvaluateVerb,
  'CV_5': EvaluateVerb,
  'CV_6': EvaluateVerb,
  'CV_7': EvaluateVerb,
  'CV_8': EvaluateVerb,
  'CV_9': EvaluateVerb,
  'CV_10': EvaluateVerb,
  'CV_11': EvaluateVerb,
  'CV_12': EvaluateVerb,
  'CV_13': EvaluateVerb,
  'CV_14': EvaluateVerb,
  'CV_15': EvaluateVerb,
  'CV_16': EvaluateVerb,
  'CV_17': EvaluateVerb,
  'CV_18': EvaluateVerb,
  'CV_19': EvaluateVerb,
  'CV_20': EvaluateVerb,
  'CV_21': EvaluateVerb,
  'CV_22': EvaluateVerb,
  'CV_23': EvaluateVerb,
  'CV_24': EvaluateVerb,
  'CV_25': EvaluateVerb,
  'CV_26': EvaluateVerb,
  'CV_27': EvaluateVerb,
  'CV_28': EvaluateVerb,
  'CV_29': EvaluateVerb,
  'CV_30': EvaluateVerb,
  'CV_31': EvaluateVerb,
  'CV_32': EvaluateVerb,
  'CV_33': EvaluateVerb,
  'CV_34': EvaluateVerb,
  'CV_35': EvaluateVerb,
  'CV_36': EvaluateVerb,
  'CV_37': EvaluateVerb,
  'CV_38': EvaluateVerb,
  'CV_39': EvaluateVerb,
  'CV_40': EvaluateVerb,
  'CV_41': EvaluateVerb,
  'CV_42': EvaluateVerb,
  'CV_43': EvaluateVerb,
  'CV_44': EvaluateVerb,
  'CV_45': EvaluateVerb,
  'CV_46': EvaluateVerb,
  'CV_47': EvaluateVerb,
  'CV_48': EvaluateVerb,
  'CV_49': EvaluateVerb,
  'CV_50': EvaluateVerb,
  'CV_51': EvaluateVerb,
  'CV_52': EvaluateVerb,
  'CV_53': EvaluateVerb,
  'CV_54': EvaluateVerb,
  'CV_55': EvaluateVerb,
  'CV_56': EvaluateVerb,
  'CV_57': EvaluateVerb,
  'CV_58': EvaluateVerb,
  'CV_59': EvaluateVerb,
  'CV_60': EvaluateVerb,
  'CV_61': EvaluateVerb,
  'CV_62': EvaluateVerb,
  'CV_63': EvaluateVerb,
  'CV_64': EvaluateVerb,
  'CV_65': EvaluateVerb,
  'CV_66': EvaluateVerb,
  'CV_67': EvaluateVerb,
  'CV_68': EvaluateVerb,
  'CV_69': EvaluateVerb,
  'CV_70': EvaluateVerb,
  'CV_71': EvaluateVerb,
  'CV_72': EvaluateVerb,
  'CV_73': EvaluateVerb,
  'CV_74': EvaluateVerb,
  'CV_75': EvaluateVerb,
  'CV_76': EvaluateVerb,
  'CV_77': EvaluateVerb,
  'CV_78': EvaluateVerb,
  'CV_79': EvaluateVerb,
  'CV_80': EvaluateVerb,
  'CV_81': EvaluateVerb,
  'CV_82': EvaluateVerb,
  'CV_83': EvaluateVerb,
  'CV_84': EvaluateVerb,
  'CV_85': EvaluateVerb,
  'CV_86': EvaluateVerb,
  'CV_87': EvaluateVerb,
  'CV_88': EvaluateVerb,
  'CV_89': EvaluateVerb,
  'CV_90': EvaluateVerb,
  'CV_91': EvaluateVerb,
  'CV_92': EvaluateVerb,
  'CV_93': EvaluateVerb,
  'CV_94': EvaluateVerb,
  'CV_95': EvaluateVerb,
  'CV_96': EvaluateVerb,
  'CV_97': EvaluateVerb,
  'CV_98': EvaluateVerb,
  'CV_99': EvaluateVerb,
  'CV_100': EvaluateVerb,
  'CV_101': EvaluateVerb,
  'CV_102': EvaluateVerb,
  'CV_103': EvaluateVerb,
  'CV_104': EvaluateVerb,
  'CV_105': EvaluateVerb,
  'CV_106': EvaluateVerb,
  'CV_107': EvaluateVerb,
  'CV_108': EvaluateVerb,
  'CV_109': EvaluateVerb,
  'CV_110': EvaluateVerb,
  'CV_111': EvaluateVerb,
  'CV_112': EvaluateVerb,
  'CV_113': EvaluateVerb,
  'CV_114': EvaluateVerb,
  'CV_115': EvaluateVerb,
  'CV_116': EvaluateVerb,
  'CV_117': EvaluateVerb,
  'CV_118': EvaluateVerb,
  'CV_119': EvaluateVerb,
  'CV_120': EvaluateVerb,
  'CV_121': EvaluateVerb,
  'CV_122': EvaluateVerb,
  'CV_123': EvaluateVerb,
  'CV_124': EvaluateVerb,
  'CV_125': EvaluateVerb,
  'CV_126': EvaluateVerb,
  'CV_127': EvaluateVerb,
  'CV_128': EvaluateVerb,
  'CV_129': EvaluateVerb,
  'CV_130': EvaluateVerb,
  'CV_131': EvaluateVerb,
  'CV_132': EvaluateVerb,
  'CV_133': EvaluateVerb,
  'CV_134': EvaluateVerb,
  'CV_135': EvaluateVerb,
  'CV_136': EvaluateVerb,
  'CV_137': EvaluateVerb,
  'CV_138': EvaluateVerb,
  'CV_139': EvaluateVerb,
  'CV_140': EvaluateVerb,
  'CV_141': EvaluateVerb,
  'CV_142': EvaluateVerb,
  'CV_143': EvaluateVerb,
  'CV_144': EvaluateVerb,
  'CV_145': EvaluateVerb,
  'CV_146': EvaluateVerb,
  'CV_147': EvaluateVerb,
  'CV_148': EvaluateVerb,
  'CV_149': EvaluateVerb,
  'CV_150': EvaluateVerb,
  'CV_151': EvaluateVerb,
  'CV_152': EvaluateVerb,
  'CV_153': EvaluateVerb,
  'CV_154': EvaluateVerb,
  'CV_155': EvaluateVerb,
  'CV_156': EvaluateVerb,
  'CV_157': EvaluateVerb,
  'CV_991': EvaluateVerb,
  'CV_992': EvaluateVerb,
  'CV_993': EvaluateVerb,
}

ReloadPatterns()
