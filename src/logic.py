import subprocess
import platform


if platform.system() == 'Windows':
  MACE_PATH = r'prover\mace4.exe'
  PROVER_PATH = r'prover\prover9.exe'
else:
  MACE_PATH = r'prover/mace4'
  PROVER_PATH = r'prover/prover9'
MACE_FAILURE_MARKER = 'Exiting with failure.'
MACE_SUCCESS_MARKER = 'Exiting with 1 model.'
PROVER_FAILURE_MARKER = 'SEARCH FAILED'
PROVER_SUCCESS_MARKER = 'THEOREM PROVED'
MACE_TEMPLATE = """
formulas(assumptions).
  %s.
end_of_list.

assign(domain_size, %d).
clear(print_models).
"""
PROVER_TEMPLATE = """
formulas(assumptions).
  %s.
end_of_list.

formulas(goals).
  %s.
end_of_list.

assign(max_proofs, 1).
clear(auto_denials).
"""


class ProverError(Exception): pass


def IsConsistent(drs):
  model = MACE_TEMPLATE % (drs.Formulate(), max(len(drs.referents), 2))
  return Run(MACE_PATH, model, MACE_SUCCESS_MARKER, MACE_FAILURE_MARKER)


def IsProvable(assumption_drs, theorem_drs):
  assumptions = assumption_drs.FormulateConditions()
  theorem = theorem_drs.Formulate(enforce_unique=False)
  theorem = PROVER_TEMPLATE % (assumptions, theorem)
  return Run(PROVER_PATH, theorem, PROVER_SUCCESS_MARKER, PROVER_FAILURE_MARKER)


def Run(command, input, success_marker, failure_marker):
  p = subprocess.Popen(command,
                       shell=True,
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
  result = p.communicate(input)[0]
  if success_marker in result:
    return True
  elif failure_marker in result:
    return False
  else:
    raise ProverError('Could not understand mace/prover output:\n%s' % result)
