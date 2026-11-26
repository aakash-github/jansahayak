"""JSON schema for the intake step, used in two layers.

1. Constrained decoding (light): the server is told the reply must be an object with an `intent` from the
   3 allowed values and a `profile` object (`response_format: json_schema`). Without it the 8B model
   sometimes invents values, e.g. intent "inquiry".
2. Validation (strict): the profile is then checked with pydantic, field by field. A bad field
   (age 500, income -1, unknown category, unknown key) is dropped and logged; the good fields are kept.

Why not constrain every profile field at decode time? We tried (FULL_INTAKE_SCHEMA below). With all 17
optional fields in the schema, Qwen3-8B filled unstated yes/no facts with false, dropped facts it found
without the schema (income, state, occupation) and put values in the wrong field
(business_type: "entrepreneur"). End-to-end accuracy fell from 90% to 85%. So decoding only fixes the
shape, and the field rules are checked afterwards.
"""
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from . import trace


# one validator per profile field: type + sensible limits
FIELD_TYPES = {
    "occupation": Literal["farmer", "student", "entrepreneur"],
    "state": str,
    "age": int,
    "annual_income": float,
    "gender": Literal["male", "female"],
    "category": Literal["general", "obc", "ebc", "dnt", "sc", "st", "ews"],
    "disability": bool,
    "land_acres": float,
    "course": str,
    "business_type": str,
    "shg_member": bool, "class12_top20": bool, "class12_top1": bool, "top_institution": bool,
    "school_student": bool, "swanath_category": bool, "dpiit_recognised": bool,
}
LIMITS = {"age": (0, 120), "annual_income": (0, 1e9), "land_acres": (0, 100000)}
_ADAPTERS = {k: TypeAdapter(t) for k, t in FIELD_TYPES.items()}


class Intake(BaseModel):
    intent: Literal["find_schemes", "scheme_question", "out_of_scope"] = "find_schemes"
    profile: dict = Field(default_factory=dict)


def _json_type(t) -> dict:
    if t is str:
        return {"type": "string", "maxLength": 60}
    if t is int:
        return {"type": "integer"}
    if t is float:
        return {"type": "number"}
    if t is bool:
        return {"type": "boolean"}
    return {"type": "string", "enum": list(t.__args__)}  # Literal


INTAKE_SCHEMA = {  # used for constrained decoding
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["find_schemes", "scheme_question", "out_of_scope"]},
        "profile": {"type": "object"},
    },
    "required": ["intent", "profile"],
}

FULL_INTAKE_SCHEMA = {  # every field typed: tried and rejected (see the note at the top)
    "type": "object",
    "properties": {
        "intent": INTAKE_SCHEMA["properties"]["intent"],
        "profile": {"type": "object", "properties": {k: _json_type(t) for k, t in FIELD_TYPES.items()},
                    "additionalProperties": False},
    },
    "required": ["intent", "profile"],
}


def validate_intake(raw: dict) -> dict:
    """Return {"intent", "profile"} with only valid fields; log every field we had to drop."""
    try:
        out = Intake.model_validate(raw or {})
    except ValidationError:
        trace.error("schema_invalid", "intent")
        out = Intake(profile=(raw or {}).get("profile") if isinstance((raw or {}).get("profile"), dict) else {})
    profile = {}
    for k, v in out.profile.items():
        if k not in _ADAPTERS or v is None or v == "":
            continue
        if isinstance(v, str) and k in ("occupation", "gender", "category"):
            v = v.strip().lower()
        try:
            v = _ADAPTERS[k].validate_python(v)
        except ValidationError:
            trace.error("schema_invalid", k)
            continue
        lo, hi = LIMITS.get(k, (None, None))
        if lo is not None and not lo <= v <= hi:
            trace.error("schema_invalid", f"{k} out of range")
            continue
        profile[k] = v
    return {"intent": out.intent, "profile": profile}
