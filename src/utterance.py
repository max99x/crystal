import drt.drs
import ext.plural
import nltk


MAX_ADJECTIVES = 3


def UtterancePlanningError(Exception): pass


def DescribeResult(result, question_drs, context_drs):
  if result is None:
    # TODO: Expand.
    return 'That is unknown.'
  elif result == True:
    # TODO: Expand.
    return 'Yes.'
  elif result == False:
    # TODO: Expand.
    return 'No.'
  elif result == []:
    # TODO: Expand.
    return 'No known entities match the query.'
  else:
    if len(result) > 1:
      described_refs = [DescribeReferent(i, context_drs, short=True)
                        for i in result]
      args =  (', '.join(described_refs[:-1]), described_refs[-1])
      result = '%s and %s' % args
    else:
      result = DescribeReferent(result[0], context_drs)
    return result[0].upper() + result[1:] + '.'


def DescribeReferent(ref, drs, definite=True, short=False):
  if isinstance(ref, drt.drs.NamedReferent):
    return ref.Pretty()
  else:
    nouns = []
    adjectives = []
    owner = None
    modifier = None
    prepositions = {}
    
    for cond in drs.conditions:
      if (isinstance(cond, drt.drs.PredicateCondition) and
          cond.informative and ref in cond.args):
        predicate = cond.predicate
        args = cond.args
        if len(args) == 1:
          synset = nltk.corpus.wordnet.synset(predicate)
          if '.n.' in predicate:
            nouns.append(synset)
          elif '.a.' in predicate or '.s.' in predicate:
            adjectives.append(synset)
          else:
            raise UtterancePlanningError('Unknown predicate: %s' % predicate)
        elif cond.predicate.startswith('_'):
          if cond.predicate == '_possess' and args[1] == ref:
            # TODO: Handle multiple owners.
            owner = cond.args[0]
          elif cond.predicate == '_modify' and args[1] == ref:
            # TODO: Handle multiple modifiers.
            modifier = cond.args[0]
        elif '/' not in predicate and args[0] == ref:
          prepositions[predicate] = args[1]

    assert nouns, 'A referent with no noun predicates found!'

    head_noun = max(nouns, key=lambda s: s.max_depth())
    head_noun = head_noun.lemmas[0].name.replace('_', ' ')
    if ref.type == drt.drs.PLURAL_TYPE:
      head_noun = ext.plural.noun_plural(head_noun)

    description = head_noun

    if modifier:
      description = DescribeReferent(modifier, drs, False) + ' ' + description

    # TODO: Select most relevant adjectives.
    adjectives = [i.lemmas[0].name.replace('_', ' ')
                  for i in adjectives][:MAX_ADJECTIVES]
    # TODO: Sort adjectives. E.g. "thin green book" not "green thin book".

    description = ' '.join(adjectives + [description])

    # TODO: Deal with prepositions.
  
    if definite:
      if owner and not short:
        owner_description = DescribeReferent(owner, drs)
        if owner_description.endswith('s'):
          owner_description += "' "
        else:
          owner_description += "'s "
        description = owner_description + description
      else:
        description = 'the ' + description

    return description
