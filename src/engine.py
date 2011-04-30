import nltk
import cfg_parser
import drt.drs
import drt.rules
import drt.resolve
import logic
import tokenizer
import utterance


CONDITION_TRIGGERS = set(['if', 'when', 'whenever', 'given', 'as', 'assuming',
                          'provided', 'proposing', 'since', 'supposing'])


def GetInformativeCopy(drs):
  copy = drs.Copy()
  for d in copy.Walk():
    d._conditions = [i for i in d._conditions if i.informative]
  return copy


def AnswerQuestion(question_drs, context_drs):
  result = None
  if isinstance(question_drs, drt.drs.BooleanQuestionDRS):
    informative_question_drs = GetInformativeCopy(question_drs)
    positive = logic.IsProvable(context_drs, informative_question_drs)
    inverse_drs = drt.drs.DRS([], [drt.drs.NegationCondition(question_drs)])
    negative = logic.IsProvable(context_drs, inverse_drs)
    if positive and negative:
      raise Exception('This is madness!')
    elif positive:
      result = True
    elif negative:
      result = False
  else:
    answers = []
    target = question_drs.target
    for possible in context_drs.referents:
      cond = drt.drs.EqualityCondition(target, possible)
      question_drs.AddCondition(cond)
      informative_question_drs = GetInformativeCopy(question_drs)
      if logic.IsProvable(context_drs, informative_question_drs):
        answers.append(possible)
      question_drs.RemoveCondition(cond)
    result = answers

  return result


def GetDRSFromTrees(trees, tokens, old_drs):
  strict_mode_values = [True]
  if CONDITION_TRIGGERS.intersection(tokens):
    strict_mode_values.append(False)

  for strict_mode in strict_mode_values:
    drt.rules._strict_mode = strict_mode
    
    for tree in trees:
      try:
        drs = drt.rules.Evaluate(tree)
      except drt.rules.EvaluatorError:
        continue
      
      is_question = isinstance(drs, drt.drs.QuestionDRS)
      try:
        drs = drt.resolve.Resolve(drs, old_drs, is_question)
      except drt.resolve.ConsistencyError:
        continue

      if logic.IsConsistent(drs):
        yield tree, drs


def ProcessString(input, context_drs, queue):
  queue.put(('post', input, 'input'))

  # Get trees.
  try:
    tokens = tokenizer.Tokenize(input)
  except:
    queue.put(('post', 'Could not tokenize the input.', 'problem'))
    return

  try:
    trees = cfg_parser.Parse(tokens)
  except:
    trees = []

  trees_count = len(trees)
  if trees_count == 0:
    message = 'Could not find any parse trees for the input.'
    queue.put(('post', message, 'problem'))
    return
  if trees_count == cfg_parser.MAX_TREES:
    trees_count = '%d+' % trees_count
  queue.put(('post', 'Found %s parse trees.' % trees_count, 'comment'))

  # Order trees.
  trees.sort(key=cfg_parser.GradeTree, reverse=True)

  # Evaluate trees and find the best valid tree.
  if not context_drs:
    context_drs = drt.drs.DRS()
  best_tree = None
  state = None
  interpretations = 0
  for tree, drs in GetDRSFromTrees(trees, tokens, context_drs):
    interpretations += 1
    if isinstance(drs, drt.drs.QuestionDRS):
      result = AnswerQuestion(drs, context_drs)
      
      if result not in (None, []):
        best_tree = tree
        state = 'question'
        break
      elif not best_tree:
        state = 'question'
        best_tree = tree
    else:
      best_tree = tree
      result = drs
      state = 'statement'
      break

  # Post results.
  if interpretations == 1:
    message = 'Evaluated 1 interpretation.'
  else:
    message = 'Evaluated %d interpretations.' % interpretations
  queue.put(('post', message, 'comment'))

  if not best_tree:
    best_tree = trees[0]
  #queue.put(('post', str(best_tree), 'comment'))
  queue.put(('post', GetTerminalDefinitions(best_tree), 'comment'))
  
  if state == 'question':
    result = utterance.DescribeResult(result, drs, context_drs)
    queue.put(('post', result, 'result'))
  elif state == 'statement':
    queue.put(('post', 'Statement understood and added to context.', 'result'))
    queue.put(('update_context', result, None))
  else:
    message = 'Could not find any consistent interpretation of the input.'
    queue.put(('post', message, 'problem'))


def GetTerminalDefinitions(tree):
  stack = [tree]
  buffer = ['Inferred word senses:']
  while stack:
    subtree = stack.pop()
    if isinstance(subtree, basestring):
      continue
    stack += list(reversed(subtree))
    if ('SNS' in subtree.node and
        all(isinstance(i, basestring) for i in subtree)):
      definition = nltk.corpus.wordnet.synset(subtree.node['SNS']).definition
      buffer.append('  %s: %s.' % (' '.join(subtree), definition))

  return '\n'.join(buffer)

