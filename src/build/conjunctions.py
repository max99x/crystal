import cPickle as pickle
import base


CONJUNCTIONS_PATH = 'data/conjunctions.pickle'
SINGLE_TEMPLATE = 'Cnj[SEM="%s",%ss,%snp,%scv,%svp,%sadj,%sajp,%spp,%sdt,%sadv,%sseries,-compound] -> %s\n'
PAIR_TEMPLATE = 'Cnj[GRP="%s",SEM="%s",%ss,%snp,%scv,%svp,%sadj,%sajp,%spp,%sdt,%sadv,%sseries,%sinit,+compound] -> %s\n'


def WriteRules(outfile):
  conjunctions = pickle.load(open(CONJUNCTIONS_PATH))
  for conjunction in conjunctions:
    name = conjunction[0].replace(' ', '_')
    semantics = conjunction[-2]
    is_series = '-+'[conjunction[-1]]
    flags = tuple('-+'[i] for i in conjunction[1:-2])
    if '...' in name:
      group = name
      first, second = [i.strip() for i in name.split('...')]

      first_terminals = base.LemmaToTerminals(first)
      second_terminals = base.LemmaToTerminals(second)
      
      common_args = (group, semantics) + flags + (is_series,)
      
      outfile.write(PAIR_TEMPLATE % (common_args + ('+', first_terminals)))
      outfile.write(PAIR_TEMPLATE % (common_args + ('-', second_terminals)))
    else:
      terminals = base.LemmaToTerminals(name)
      args = (semantics,) + flags + (is_series, terminals)
      outfile.write(SINGLE_TEMPLATE % args)
