import os
import nltk


GRAMMAR = 'grammar.fcfg'
MAX_TREES = 10000


_TYPE_FEATURE = nltk.featstruct.Feature('type')
_KNOWN_WORDS = set([
  "'re", "'s", "'t", 'a', 'about', 'above', 'across', 'against', 'all', 'along',
  'alongside', 'am', 'ambassador', 'amid', 'among', 'amongst', 'an', 'and',
  'another', 'any', 'are', 'aren', 'around', 'assuming', 'astride', 'at',
  'athwart', 'been', 'being', 'before', 'behind', 'below', 'beneath', 'beside',
  'between', 'beyond', 'but', 'by', 'capt', 'captain', 'certain', 'cmdr',
  'coach', 'col', 'colonel', 'commander', 'corporal', 'cpl', 'did', 'didn',
  'do', 'doctor', 'does', 'doesn', 'don', 'down', 'dr', 'each', 'every', 'few',
  'for', 'from', 'front', 'gen', 'general', 'given', 'gov', 'governor', 'had',
  'have', 'haven', 'hasn', 'has', 'he', 'her', 'hers', 'herself', 'him',
  'himself', 'his', 'hon', 'honorable', 'i', 'if', 'in', 'inside', 'into',
  'is', 'isn', 'it', 'its', 'itself', 'judge', 'lieutenant', 'little', 'lot',
  'lt', 'maj', 'major', 'many', 'master', 'me', 'mine', 'miss', 'mister',
  'more', 'most', 'mr', 'mrs', 'ms', 'much', 'my', 'myself', 'near', 'next',
  'no', 'none', 'not', 'of', 'ofc', 'off', 'officer', 'on', 'one', 'oneself',
  'onto', 'opposite', 'or', 'our', 'ours', 'ourself', 'out', 'outside', 'over',
  'past', 'pres', 'president', 'private', 'prof', 'professor', 'pvt', 'rep',
  'representative', 'rev', 'reverend', 'round', 'sargent', 'sec', 'secretary',
  'sen', 'senator', 'several', 'sgt', 'she', 'sir', 'some', 'than', 'that',
  'the', 'their', 'them', 'themselves', 'then', 'these', 'they', 'this',
  'those', 'through', 'throughout', 'to', 'towards', 'under', 'underneath',
  'up', 'upon', 'us', 'was', 'wasn', 'we', 'were', 'weren', 'what', 'which',
  'when', 'whenever', 'where', 'who', 'whom', 'within', 'you', 'your', 'yours',
  'yourself'
])

_parser = None


class ParserError(Exception): pass


def ReloadGrammar(path=GRAMMAR, **kwds):
  global _parser
  nltk.data._resource_cache = {}
  _parser = nltk.load_parser('file:' + os.path.abspath(path), **kwds)


def Parse(tokens, max_trees=MAX_TREES):
  if _parser is None: ReloadGrammar()
  trees = _parser.nbest_parse(tokens, max_trees)
  if trees:
    return trees
  else:
    raise ParserError('No parse trees found for sentence: %s' % tokens)


def SelectTree(trees):
  return max(trees, key=GradeTree)


def GradeTree(tree):
  if isinstance(tree, basestring):
    return 0
  else:
    score = 0
    
    # Prefer Ss and VPs that directly contain prepositions. For matching
    # phrasal verbs like "switch _ on" and objects like "give _ to _".
    if tree.node[_TYPE_FEATURE] in ('S', 'VP'):
      score = (sum(2000 for i in tree if isinstance(i, basestring)) +
               sum(1000 for i in tree
                   if hasattr(i, 'node') and i.node[_TYPE_FEATURE] == 'Prep'))

    # Terminals used in the manual rules take precendence.
    if (len(tree) == 1 and
        isinstance(tree[0], basestring) and
        tree[0] in _KNOWN_WORDS and
        tree.node[_TYPE_FEATURE] in ('Noun', 'Adj', 'Verb')):
      score -= 500

    # Ambiguous names are less likely to come as proper nouns.
    # Nouns that have been observed by the wordnet frequency counter are better.
    if 'FRQ' in tree.node:
      score += tree.node['FRQ']

    return sum(GradeTree(i) for i in tree) + score
