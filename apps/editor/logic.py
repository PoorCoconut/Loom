"""Pure helpers for typed story variables. No DB access in here."""

from django.core.exceptions import ValidationError

REQUIREMENT_OPS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
}
ORDERED_OPS = {"gt", "gte", "lt", "lte"}


def coerce(raw, data_type):
    """Turn the stored string into a real int / bool / str."""
    raw = "" if raw is None else str(raw).strip()
    if data_type == "int":
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f"'{raw}' is not a whole number.")
    if data_type == "bool":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"'{raw}' is not true/false.")
    return raw


def check_requirement(current, op, raw_value, data_type):
    """Does `current` satisfy `op raw_value`?"""
    if op in ORDERED_OPS and data_type != "int":
        raise ValueError(f"'{op}' only works on integer variables.")
    return REQUIREMENT_OPS[op](current, coerce(raw_value, data_type))


def apply_modifier(current, op, raw_value, data_type):
    """Return the variable's new value after applying `op`."""
    if op == "set":
        return coerce(raw_value, data_type)
    if op in ("add", "subtract"):
        if data_type != "int":
            raise ValueError(f"'{op}' only works on integer variables.")
        amount = coerce(raw_value, "int")
        return current + amount if op == "add" else current - amount
    if op == "toggle":
        if data_type != "bool":
            raise ValueError("'toggle' only works on boolean variables.")
        return not current
    raise ValueError(f"Unknown modifier '{op}'.")


def _sample(data_type):
    return {"int": 0, "bool": False}.get(data_type, "")


def validate_condition(cond):
    """Model-level validation for PathCondition (used by clean())."""
    if not cond.requirement_type and not cond.modifier_type:
        raise ValidationError("Choose a requirement, a modifier, or both.")

    if cond.path_id and cond.variable_id:
        if cond.variable.story_id != cond.path.source_node.story_id:
            raise ValidationError("The variable must belong to the same story as the path.")

    if cond.variable_id:
        data_type = cond.variable.data_type
        sample = _sample(data_type)
        try:
            if cond.requirement_type:
                check_requirement(sample, cond.requirement_type, cond.value, data_type)
            if cond.modifier_type:
                apply_modifier(sample, cond.modifier_type, cond.value, data_type)
        except ValueError as exc:
            raise ValidationError(str(exc))
