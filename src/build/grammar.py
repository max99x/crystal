import os
import adjectives
import conjunctions
import names
import nouns
import verbs


PATTERNS_PATH = 'data/patterns.pickle'
GRAMMAR_FOLDER = 'grammar'
GRAMMAR_PATH = 'grammar.fcfg'


def BuildGrammar():
  outfile = open(GRAMMAR_PATH, 'w')
  patterns_file = open(PATTERNS_PATH, 'w')

  for filename in os.listdir(GRAMMAR_FOLDER):
    s = open(os.path.join(GRAMMAR_FOLDER, filename)).read()
    outfile.write('\n### %s ###\n' % filename)
    outfile.write(s)
  
  print '\tBuilding conjunctions...'
  outfile.write('\n### Conjunctions ###\n')
  conjunctions.WriteRules(outfile)

  print '\tBuilding verbs...'
  outfile.write('\n### VPs and Verbs ###\n')
  verbs.WriteRules(outfile, patterns_file)

  print '\tBuilding names...'
  outfile.write('\n### Proper Nouns ###\n')
  names.WriteRules(outfile)

  print '\tBuilding adjectives...'
  outfile.write('\n### Adjectives ###\n')
  adjectives.WriteRules(outfile)

  print '\tBuilding nouns...'
  outfile.write('\n### Nouns ###\n')
  nouns.WriteRules(outfile)

  outfile.close()
  patterns_file.close()

  print '\tDone.'
