import collections
import copy
import re


class FormulationError(Exception): pass


VERB_TYPE = 'e'
SINGULAR_TYPE = 's'
PLURAL_TYPE = 'p'
MASS_TYPE = 'm'


class Referent(object):
  ref_index = 1
  
  def __init__(self, type=SINGULAR_TYPE):
    # Prover9 treats u-z as vars, not consts as we want them.
    assert type not in ('u', 'v', 'w', 'x', 'y', 'z')
    self.type = type
    self.index = self.__class__.ref_index
    self.__class__.ref_index += 1

  def __repr__(self):
    return self.id

  @property
  def id(self):
    return '%s%d' % (self.type, self.index)


class NamedReferent(Referent):

  def __init__(self, name):
    self.type = SINGULAR_TYPE
    self.name = name

  def __eq__(self, other):
    return self.id == other.id

  def __ne__(self, other):
    return self.id != other.id

  def __hash__(self):
    return hash((NamedReferent, self.id))

  def Pretty(self):
    return self.id[2:].replace('_', ' ')

  @property
  def id(self):
    return self.type + '_' + self.name


class Condition(object):
  def __ne__(self, other):
    return not (self == other)

  @property
  def summary(self):
    return repr(self)

  def Copy(self):
    return copy.copy(self)

  def GetChildDRSs(self):
    return ()

  def GetAccessibleReferents(self, _=None):
    return self.parent.GetAccessibleReferents()


class PredicateCondition(Condition):
  def __init__(self, predicate, *args, **kwds):
    self.predicate = predicate
    self.args = args
    self.parent = None
    self.informative = kwds.get('informative', True)

  def __repr__(self):
    args = ', '.join(str(i) for i in self.args)
    return '%s(%s)' % (self.predicate, args)

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self.predicate == other.predicate and
            self.args == other.args)

  def __hash__(self):
    return hash((PredicateCondition, self.predicate, self.args))

  def Formulate(self):
    return re.sub('[\'"/-]', '__', repr(self).replace('.', '_'))

  def ReplaceReferent(self, old, new, add_new):
    new_args = []
    for arg in self.args:
      new_args.append(new if arg == old else arg)
    self.args = tuple(new_args)
    return add_new


class EqualityCondition(Condition):
  def __init__(self, referent1, referent2, informative=True):
    self.ref1 = referent1
    self.ref2 = referent2
    self.parent = None
    self.informative = informative

  def __repr__(self):
    return '(%s = %s)' % (self.ref1, self.ref2)

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            ((self.ref1 == other.ref1 and self.ref2 == other.ref2) or
             (self.ref1 == other.ref2 and self.ref2 == other.ref1)))

  def __hash__(self):
    return hash((EqualityCondition, self.ref1, self.ref2))

  def Formulate(self):
    return str(self)

  def ReplaceReferent(self, old, new, add_new):
    if self.ref1 == old: self.ref1 = new
    if self.ref2 == old: self.ref2 = new
    return add_new


class NegationCondition(Condition):
  def __init__(self, drs_or_condition, informative=True):
    if isinstance(drs_or_condition, Condition):
      drs_or_condition = DRS([], [drs_or_condition])
    self.drs = drs_or_condition
    drs_or_condition.parent = self
    self.parent = None
    self.informative = informative

  def __repr__(self):
    return '-%s' % self.drs

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self.drs == other.drs)

  def __hash__(self):
    return hash((NegationCondition, self.drs))

  @property
  def summary(self):
    return '-%s' % self.drs.summary

  def Formulate(self):
    return '-(%s)' % self.drs.Formulate()

  def GetChildDRSs(self):
    return (self.drs,)

  def ReplaceReferent(self, old, new, add_new):
    return self.drs.ReplaceReferent(old, new, add_new)

  def Copy(self):
    return NegationCondition(self.drs.Copy(), informative=self.informative)


class AlternationCondition(Condition):
  def __init__(self, drs_or_condition1, drs_or_condition2, informative=True):
    if isinstance(drs_or_condition1, Condition):
      drs_or_condition1 = DRS([], [drs_or_condition1])
    if isinstance(drs_or_condition2, Condition):
      drs_or_condition2 = DRS([], [drs_or_condition2])
    self.drs1 = drs_or_condition1
    self.drs2 = drs_or_condition2
    self.drs1.parent = self
    self.drs2.parent = self
    self.parent = None
    self.informative = informative

  def __repr__(self):
    return '(%s or %s)' % (self.drs1, self.drs2)

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            ((self.drs1 == other.drs1 and self.drs2 == other.drs2) or
             (self.drs1 == other.drs2 and self.drs2 == other.drs1)))

  def __hash__(self):
    return hash((AlternationCondition, self.drs1, self.drs2))

  @property
  def summary(self):
    return '(%s or %s)' % (self.drs1.summary, self.drs2.summary)

  def Formulate(self):
    return '((%s) | (%s))' % (self.drs1.Formulate(),
                              self.drs2.Formulate())

  def GetChildDRSs(self):
    return (self.drs1, self.drs2)

  def ReplaceReferent(self, old, new, add_new):
    add_new = self.drs1.ReplaceReferent(old, new, add_new)
    add_new = self.drs2.ReplaceReferent(old, new, add_new)
    return add_new

  def Copy(self):
    return AlternationCondition(self.drs1.Copy(), self.drs2.Copy(),
                                informative=self.informative)


class ImplicationCondition(Condition):
  def __init__(self, drs_or_condition1, drs_or_condition2, informative=True):
    if isinstance(drs_or_condition1, Condition):
      drs_or_condition1 = DRS([], [drs_or_condition1])
    if isinstance(drs_or_condition2, Condition):
      drs_or_condition2 = DRS([], [drs_or_condition2])
    self.drs1 = drs_or_condition1
    self.drs2 = drs_or_condition2
    self.drs1.parent = self
    self.drs2.parent = self
    self.parent = None
    self.informative = informative

  def __repr__(self):
    return '(%s -> %s)' % (self.drs1, self.drs2)

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self.drs1 == other.drs1 and
            self.drs2 == other.drs2)

  def __hash__(self):
    return hash((ImplicationCondition, self.drs1, self.drs2))

  @property
  def summary(self):
    return '(%s -> %s)' % (self.drs1.summary, self.drs2.summary)

  def Formulate(self):
    return '(%s ((%s) -> (%s)))' % (self.drs1.FormulateDomain(forall=True),
                                    self.drs1.FormulateConditions(),
                                    self.drs2.Formulate())

  def GetChildDRSs(self):
    return (self.drs1, self.drs2)

  def ReplaceReferent(self, old, new, add_new):
    add_new = self.drs1.ReplaceReferent(old, new, add_new)
    add_new = self.drs2.ReplaceReferent(old, new, add_new)
    return add_new

  def Copy(self):
    return ImplicationCondition(self.drs1.Copy(), self.drs2.Copy(),
                                informative=self.informative)

  def GetAccessibleReferents(self, which):
    if which == self.drs2:
      return self.drs1.GetAccessibleReferents()
    else:
      return self.parent.GetAccessibleReferents()


class ResolutionCondition(Condition):
  def __init__(self, referent, requirements, type):
    self.ref = referent
    self.requirements = requirements
    requirements.parent = self
    self.type = type
    self.parent = None
    self.informative = True

  def __repr__(self):
    drs = str(self.requirements)
    if drs.startswith('['):
      drs = drs[1:-1]
    return '%s ? {{%s}}' % (self.ref, drs)

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.ref == other.ref

  def __hash__(self):
    return hash((ResolutionCondition, self.ref, self.requirements))

  @property
  def summary(self):
    drs_summary = self.requirements.summary
    if drs_summary.startswith('['):
      drs_summary = drs_summary[1:-1]
    return '%s ? {{%s}}' % (self.ref, drs_summary)

  def Copy(self):
    return ResolutionCondition(self.ref, self.requirements.Copy(), self.type)

  def Formulate(self):
    raise FormulationError('Cannot formulate unresolved condition.')

  def GetChildDRSs(self):
    return (self.requirements,)

  def ReplaceReferent(self, old, new, add_new):
    if self.ref == old:
      raise FormulationError('Cannot replace unresolved referents.')
    else:
      add_new = self.requirements.ReplaceReferent(old, new, add_new)
      return add_new


class DRS(object):
  def __init__(self, referents=(), conditions=(), parent=None):
    if isinstance(referents, DRS):
      DRS.__init__(self)
      self += referents
    else:
      self._conditions = []
      for cond in conditions:
        self.AddCondition(cond)
      self.referents = set(referents)
      self.parent = parent

  def __nonzero__(self):
    return bool(self.referents or self._conditions)

  def __add__(self, other):
    base = self.Copy()
    return base.__iadd__(other)

  def __iadd__(self, other):
    self.referents.update(other.referents)
    for cond in other._conditions:
      self.AddCondition(cond.Copy())
    if isinstance(other, SubjectQuestionDRS):
      self.__class__ = SubjectQuestionDRS
      self.target = other.target
    return self

  def __repr__(self):
    refs = ', '.join(str(i) for i in self.referents)
    conds = ', '.join(str(i) for i in self._conditions)
    if refs:
      result = '[%s | %s]' % (refs, conds)
    else:
      result = conds if len(self._conditions) == 1 else '[%s]' % conds
    return result

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self.referents == other.referents and
            self._conditions == other._conditions)

  def __ne__(self, other):
    return not (self == other)

  def __hash__(self):
    return hash((DRS,
                 frozenset(self.referents),
                 frozenset(self._conditions)))

  @property
  def summary(self):
    refs = ', '.join(str(i) for i in self.referents)
    informative_conds = [i for i in self._conditions if i.informative]
    conds = ', '.join(i.summary for i in informative_conds)
    if refs:
      result = '[%s | %s]' % (refs, conds)
    else:
      result = conds if len(self._conditions) == 1 else '[%s]' % conds
      result = conds if len(informative_conds) == 1 else '[%s]' % conds
    return result

  @property
  def conditions(self):
    return tuple(self._conditions)

  def AddCondition(self, cond):
    assert isinstance(cond, Condition)
    if cond in self._conditions:
      if cond.informative:
        self._conditions.remove(cond)
        self._conditions.append(cond)
    else:
      cond.parent = self
      self._conditions.append(cond)

  def RemoveCondition(self, cond):
    if cond in self._conditions:
      self._conditions.remove(cond)

  def Copy(self):
    return self.__class__(self.referents,
                          (i.Copy() for i in self._conditions),
                          self.parent)

  def GetChildDRSs(self):
    return sum((i.GetChildDRSs() for i in self._conditions), ())

  def Walk(self):
    yield self
    for cond in self._conditions:
      for drs in cond.GetChildDRSs():
        for drs2 in drs.Walk():
          yield drs2

  def Formulate(self, enforce_unique=True):
    return '%s (%s)' % (self.FormulateDomain(),
                        self.FormulateConditions(enforce_unique=enforce_unique))

  def FormulateDomain(self, forall=False):
    scope = 'all' if forall else 'exists'
    return ' '.join('%s %s' % (scope, i) for i in self.referents)

  def FormulateConditions(self, enforce_unique=True):
    conds = [i.Formulate() for i in self._conditions]
    uniqueness = []
    if enforce_unique:
      referents = list(self.referents)
      for i, r in enumerate(referents):
          for s in referents[i+1:]:
            uniqueness.append('%s != %s' % (r, s))
    joined = '(%s)' % ' & '.join(conds + uniqueness)
    if joined == '()':
      joined = '1=1'
    return joined

  def ReplaceReferent(self, old, new, add_new=False):
    assert not (isinstance(old, NamedReferent) and
                not isinstance(new, NamedReferent))
    if new in self.referents and not add_new:
      self.referents.remove(new)

    if old in self.referents:
      if old in self.referents: self.referents.remove(old)
      if add_new:
        self.referents.add(new)
        add_new = False

    add_new = all([cond.ReplaceReferent(old, new, add_new)
                   for cond in self._conditions])
    return add_new

  def GetAccessibleReferents(self):
    refs = collections.OrderedDict((i, self) for i in self.referents)
    if self.parent:
      ancestor_refs = self.parent.GetAccessibleReferents(self)
      ancestor_refs.update(refs)
      refs = ancestor_refs
    return refs

  def Simplify(self):
    boxes_to_resolve = [self]
    resolved_referents = {}
    while boxes_to_resolve:
      drs = boxes_to_resolve.pop()
      for cond in drs.conditions:
        if isinstance(cond, EqualityCondition):
          if cond.ref1 in resolved_referents:
            cond.ref1 = resolved_referents[cond.ref1]
          if cond.ref2 in resolved_referents:
            cond.ref2 = resolved_referents[cond.ref2]
          if cond.ref1 != cond.ref2:
            if isinstance(cond.ref1, NamedReferent):
              self.ReplaceReferent(cond.ref2, cond.ref1, add_new=True)
            else:
              self.ReplaceReferent(cond.ref1, cond.ref2, add_new=True)
            resolved_referents[cond.ref1] = cond.ref2
          drs.RemoveCondition(cond)
        if not isinstance(cond, NegationCondition):
          boxes_to_resolve += cond.GetChildDRSs()
    conditions = self._conditions
    self._conditions = []
    for cond in conditions:
      self.AddCondition(cond)

  def RaiseNamedRefs(self):
    named_refs = set()

    for drs in self.Walk():
      refs_to_keep = set()
      for ref in drs.referents:
        if isinstance(ref, NamedReferent):
          named_refs.add(ref)
        else:
          refs_to_keep.add(ref)
      drs.referents = refs_to_keep

    self.referents.update(named_refs)

  def EliminateResolutions(self):
    for drs in self.Walk():
      for cond in drs.conditions:
        if isinstance(cond, ResolutionCondition):
          drs.referents.add(cond.ref)
          drs.RemoveCondition(cond)


class QuestionDRS(DRS):
  pass


class BooleanQuestionDRS(QuestionDRS):
  def __repr__(self):
    return 'Yes/No Question: ' + DRS.__repr__(self)

  @property
  def summary(self):
    return 'Yes/No Question: ' + DRS.summary.fget(self)


class SubjectQuestionDRS(QuestionDRS):
  def __init__(self, drs, target):
    self.target = target
    DRS.__init__(self, drs)

  def __repr__(self):
    return 'Question(%s): %s' % (self.target, DRS.__repr__(self))

  @property
  def summary(self):
    return 'Question(%s): %s' % (self.target, DRS.summary.fget(self))

  def Copy(self):
    return SubjectQuestionDRS(self, self.target)
  
  def ReplaceReferent(self, old, new, add_new=False):
    if self.target == old:
      self.target = new
    DRS.ReplaceReferent(self, old, new, add_new)
