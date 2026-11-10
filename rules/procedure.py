"""The procedure order as a precedence graph (D-120, D-123). Loaded with the catalogue (rules/config.py).

configs/rule_engine/procedure_order.yaml lists the steps, "X before Y" chains, the pairs the proposal
is silent on (unknown), interchangeable groups and the owner of each relation. The loader:
  - checks every step's events against the vocabulary, one modality per step;
  - takes the transitive closure of the chains and refuses a cycle, naming it;
  - drops the pairs inside an interchangeable group;
  - refuses an "unknown" pair the chains order anyway;
  - gives every pair exactly one owner: explicit pairs first, then A7's audio scope, then the default
    owner (S1). A pair claimed twice, or an owned pair the chains don't give, is an error.
No rule reads it yet: S1 and A7 do (Increments 26-27). Not clinically approved (OQ-062).
"""
from dataclasses import dataclass
import re

from rules.errors import ConfigError

DERIVED = ("earliest_take", "later_take", "earliest_placement")   # from the paddle order (D-118)
SCOPES = ("audio",)
RULE_ID = re.compile(r"^[A-Z]\d+$")
TOP_KEYS = {"schema_version", "approval", "steps", "chains", "unknown", "interchangeable", "owners", "default_owner"}


@dataclass(frozen=True)
class Step:
    id: str
    events: tuple[str, ...]
    modality: str
    description: str
    derived: str | None = None


@dataclass(frozen=True)
class Relation:
    """X (before) must come before Y (after); owner judges it (D-123)."""
    before: str
    after: str
    owner: str
    direct: bool          # given by a chain, not only by transitivity
    source: str = ""
    confirm: bool = False   # proposed, waiting for the supervisor's confirmation


@dataclass(frozen=True)
class ProcedureOrder:
    steps: tuple[Step, ...]
    relations: tuple[Relation, ...]
    unknown: tuple[tuple[str, str], ...]
    interchangeable: tuple[tuple[str, ...], ...]
    default_owner: str
    approved_by: str | None
    source: str
    note: str

    @property
    def approved(self):
        return self.approved_by is not None

    def step(self, step_id):
        return next(s for s in self.steps if s.id == step_id)

    def relation(self, a, b):
        """The relation ordering a and b (either way), or None when they are unordered."""
        return next((r for r in self.relations if {r.before, r.after} == {a, b}), None)

    def owned_by(self, rule_id):
        return tuple(r for r in self.relations if r.owner == rule_id)


def load_procedure_order(data, vocabulary, where="procedure_order"):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ConfigError(f"{where}: expected a mapping with schema_version: 1")
    if set(data) != TOP_KEYS:
        raise ConfigError(f"{where}: expected exactly the keys {sorted(TOP_KEYS)}")
    approval = data["approval"]
    if not isinstance(approval, dict) or set(approval) != {"approved_by", "approved_on", "source", "note"}:
        raise ConfigError(f"{where} approval: expected approved_by, approved_on, source and note")
    steps = _steps(data["steps"], vocabulary, where)
    pairs = _closure(_chains(data["chains"], steps, where), steps, where)
    groups = _groups(data["interchangeable"], steps, where)
    for group in groups:
        pairs = {p: v for p, v in pairs.items() if not (p[0] in group and p[1] in group)}
    unknown = _unknown(data["unknown"], steps, pairs, where)
    default = data["default_owner"]
    if not isinstance(default, str) or not RULE_ID.match(default):
        raise ConfigError(f"{where} default_owner: expected a rule ID")
    owners = _owners(data["owners"], steps, pairs, default, where)
    relations = tuple(Relation(a, b, owners[(a, b)], direct, source, confirm)
                      for (a, b), (direct, source, confirm) in sorted(pairs.items(), key=lambda kv: _rank(kv[0], steps)))
    return ProcedureOrder(tuple(steps.values()), relations, unknown, groups, default, approval["approved_by"],
                          str(approval["source"] or ""), str(approval["note"] or ""))


def _rank(pair, steps):
    order = list(steps)
    return order.index(pair[0]), order.index(pair[1])


def _steps(raw, vocabulary, where):
    if not isinstance(raw, dict) or not raw:
        raise ConfigError(f"{where} steps: expected a mapping of step ID -> {{events, description}}")
    steps = {}
    for step_id, entry in raw.items():
        at = f"{where} steps.{step_id}"
        if not isinstance(entry, dict) or not {"events", "description"} <= set(entry) \
                or set(entry) - {"events", "description", "derived"}:
            raise ConfigError(f"{at}: expected events, description and optionally derived")
        events = entry["events"]
        if not isinstance(events, list) or not events or [e for e in events if e not in vocabulary.events]:
            raise ConfigError(f"{at}.events: expected canonical events from the vocabulary, got {events!r}")
        modalities = {vocabulary.modality(e) for e in events}
        if len(modalities) != 1:
            raise ConfigError(f"{at}.events: a step's events must share one modality")
        derived = entry.get("derived")
        if derived is not None and derived not in DERIVED:
            raise ConfigError(f"{at}.derived: expected one of {list(DERIVED)}")
        steps[step_id] = Step(step_id, tuple(events), modalities.pop(), str(entry["description"]), derived)
    return steps


def _chains(raw, steps, where):
    if not isinstance(raw, list) or not raw:
        raise ConfigError(f"{where} chains: expected a list of {{chain, source}}")
    direct = {}
    for number, entry in enumerate(raw, start=1):
        at = f"{where} chains[{number}]"
        if not isinstance(entry, dict) or not {"chain", "source"} <= set(entry) or set(entry) - {"chain", "source", "confirm"}:
            raise ConfigError(f"{at}: expected chain, source and optionally confirm")
        chain = entry["chain"]
        if not isinstance(chain, list) or len(chain) < 2 or [s for s in chain if s not in steps]:
            raise ConfigError(f"{at}.chain: expected two or more known steps, got {chain!r}")
        for a, b in zip(chain, chain[1:]):
            direct[(a, b)] = (str(entry["source"]), bool(entry.get("confirm", False)))
    return direct


def _closure(direct, steps, where):
    """Every ordered pair implied by the chains; a cycle is an error naming it."""
    successors = {s: {b for (a, b) in direct if a == s} for s in steps}
    _refuse_cycle(successors, where)
    pairs = {}
    for start in steps:
        stack, seen = list(successors[start]), set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            source, confirm = direct.get((start, node), ("", False))
            pairs[(start, node)] = ((start, node) in direct, source, confirm)
            stack.extend(successors[node])
    return pairs


def _refuse_cycle(successors, where):
    state = {}

    def visit(node, path):
        state[node] = "open"
        for nxt in sorted(successors[node]):
            if state.get(nxt) == "open":
                loop = path[path.index(nxt):] + [nxt]
                raise ConfigError(f"{where} chains: circular order: {' -> '.join(loop)}")
            if nxt not in state:
                visit(nxt, path + [nxt])
        state[node] = "done"

    for node in successors:
        if node not in state:
            visit(node, [node])


def _groups(raw, steps, where):
    if not isinstance(raw, list):
        raise ConfigError(f"{where} interchangeable: expected a list of step groups")
    groups = []
    for group in raw:
        if not isinstance(group, list) or len(group) < 2 or [s for s in group if s not in steps]:
            raise ConfigError(f"{where} interchangeable: expected groups of two or more known steps, got {group!r}")
        groups.append(tuple(group))
    return tuple(groups)


def _unknown(raw, steps, pairs, where):
    if not isinstance(raw, list):
        raise ConfigError(f"{where} unknown: expected a list of {{steps, relative_to, question}}")
    unknown = []
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"steps", "relative_to", "question"} or \
                [s for s in [*entry["steps"], *entry["relative_to"]] if s not in steps]:
            raise ConfigError(f"{where} unknown: expected {{steps, relative_to, question}} of known steps, got {entry!r}")
        for a in entry["steps"]:
            for b in entry["relative_to"]:
                if (a, b) in pairs or (b, a) in pairs:
                    raise ConfigError(f"{where} unknown: {a} and {b} are marked unknown ({entry['question']}), but the "
                                      "chains order them")
                unknown.append((a, b))
    return tuple(unknown)


def _owners(raw, steps, pairs, default, where):
    if not isinstance(raw, dict):
        raise ConfigError(f"{where} owners: expected a mapping of rule ID -> pairs or {{scope}}")
    owners, scoped = {}, []
    for rule_id, claim in raw.items():
        at = f"{where} owners.{rule_id}"
        if not isinstance(rule_id, str) or not RULE_ID.match(rule_id):   # existence: checked against rules.yaml by a test
            raise ConfigError(f"{at}: expected a rule ID such as R4 or A7")
        if isinstance(claim, dict):
            if set(claim) != {"scope"} or claim["scope"] not in SCOPES:
                raise ConfigError(f"{at}: expected {{scope: one of {list(SCOPES)}}}")
            scoped.append((rule_id, claim["scope"]))
            continue
        if not isinstance(claim, list) or not claim:
            raise ConfigError(f"{at}: expected a list of [before, after] pairs")
        for pair in claim:
            if not isinstance(pair, list) or len(pair) != 2 or tuple(pair) not in pairs:
                raise ConfigError(f"{at}: {pair!r} is not a relation of the procedure order")
            if tuple(pair) in owners:
                raise ConfigError(f"{at}: {pair[0]} -> {pair[1]} is already owned by {owners[tuple(pair)]}; "
                                  "one owner per relation (D-123)")
            owners[tuple(pair)] = rule_id
    for rule_id, scope in scoped:
        for pair in pairs:
            if pair not in owners and all(steps[s].modality == scope for s in pair):
                owners[pair] = rule_id
    for pair in pairs:
        owners.setdefault(pair, default)
    return owners
