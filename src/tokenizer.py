import re


TOKEN_PATTERN = r'\.\.\.|\.|\?!|\?|!|,|;|\(|\)|\$|"|&|\d+|[-\w]+|\'[-\w]*'
TOKEN_REGEX = re.compile(TOKEN_PATTERN)
SENTENCE_REGEX = re.compile('^(?:(?:%s)|\s+)+$' % TOKEN_PATTERN)


class TokenizerError(Exception): pass


def Tokenize(sentence):
  if not SENTENCE_REGEX.match(sentence):
    raise TokenizerError('Could not parse sentence: %s' % sentence)
  else:
    return TOKEN_REGEX.findall(sentence.lower())
