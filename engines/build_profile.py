
import json
import os
import re
from datetime import datetime, timezone
from typing import Literal

TIME_PRECISION = Literal["exact", "hour", "unknown"]

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "..", "profiles")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "input.schema.json")
_schema_cache = None

def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache

def _minimal_validate(data: dict, schema: dict) -> list:
    errors = []
    props = schema.get("properties", {})
    for req in schema.get("required", []):
        if data.get(req) in (None, ""):
            errors.append(f"缺必填字段 `{req}`")
    _types = {"number": (int, float), "integer": int, "string": str, "boolean": bool}
    for key, val in data.items():
        spec = props.get(key)
        if not spec or val is None:
            continue
        t = spec.get("type")
        if t in _types and not isinstance(val, _types[t]):
            errors.append(f"`{key}` 类型须为 {t}，实得 {type(val).__name__}")
            continue
        if "enum" in spec and val not in spec["enum"]:
            errors.append(f"`{key}` 须为 {spec['enum']} 之一，实得 {val!r}")
        if "minimum" in spec and val < spec["minimum"]:
            errors.append(f"`{key}` 不得小于 {spec['minimum']}，实得 {val}")
        if "maximum" in spec and val > spec["maximum"]:
            errors.append(f"`{key}` 不得大于 {spec['maximum']}，实得 {val}")
        if "pattern" in spec and not re.match(spec["pattern"], str(val)):
            errors.append(f"`{key}` 格式不符（应形如 1995-03-12T08:30:00），实得 {val!r}")
        if "minLength" in spec and len(str(val)) < spec["minLength"]:
            errors.append(f"`{key}` 不可为空")
    return errors

def validate_build_input(**kwargs) -> list:
    schema = _load_schema()
    data = {k: v for k, v in kwargs.items() if v is not None}
    try:
        import jsonschema
        return [e.message for e in jsonschema.Draft7Validator(schema).iter_errors(data)]
    except ImportError:
        return _minimal_validate(data, schema)

def build_profile(
    name: str,
    solar_birth: str,
    gender: str,
    lat: float = 31.23,
    lon: float = 121.47,
    tz: int = 8,
    birth_place_name: str = "未知",
    time_precision: TIME_PRECISION = "exact",
    label: str = "",
    save: bool = True,
    use_true_solar: bool = True,
) -> dict:
    errs = validate_build_input(
        name=name, gender=gender, solar_birth=solar_birth, lat=lat, lon=lon,
        tz=tz, birth_place_name=birth_place_name, time_precision=time_precision,
        label=label, save=save, use_true_solar=use_true_solar,
    )
    if errs:
        raise ValueError("建档入参不合法：" + "；".join(errs))

    try:
        datetime.fromisoformat(solar_birth)
    except ValueError:
        raise ValueError(f"建档入参不合法：`solar_birth` 不是合法日期（{solar_birth}）")

    from engines.bazi    import build as bazi_build
    from engines.ziwei   import build as ziwei_build
    from engines.vedic   import build as vedic_build
    from engines.western import build as western_build

    bazi    = bazi_build(solar_birth, gender, time_precision, lon=lon, tz=tz,
                         use_true_solar=use_true_solar)
    ziwei   = ziwei_build(solar_birth, gender, time_precision)
    vedic   = vedic_build(solar_birth, gender, time_precision, lat=lat, lon=lon, tz=tz)
    western = western_build(solar_birth, gender, lat, lon, time_precision, tz=tz)

    profile = {
        "meta": {
            "name":           name,
            "gender":         gender,
            "solar_birth":    solar_birth,
            "birth_place":    {"name": birth_place_name, "lat": lat, "lon": lon, "tz": tz},
            "time_precision": time_precision,
            "use_true_solar": use_true_solar,
            "label":          label,
            "created_at":     datetime.now(timezone.utc).isoformat(),
        },
        "bazi":    bazi,
        "ziwei":   ziwei,
        "vedic":   vedic,
        "western": western,
        "degraded": time_precision == "unknown",
    }

    if save:
        os.makedirs(PROFILES_DIR, exist_ok=True)
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    return profile

def load_profile(name: str) -> dict:
    path = os.path.join(PROFILES_DIR, f"{name}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _context_path(name: str) -> str:
    return os.path.join(PROFILES_DIR, f"{name}.context.json")

def load_user_context(name: str) -> dict:
    path = _context_path(name)
    if not os.path.exists(path):
        return {"profession": "", "concerns": [], "life_events": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_user_context(name: str, *, profession: str = None,
                      concerns: list = None, life_events: list = None) -> dict:
    ctx = load_user_context(name)
    if profession is not None:
        ctx["profession"] = profession
    if concerns is not None:
        ctx["concerns"] = concerns
    if life_events is not None:
        ctx["life_events"] = life_events
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with open(_context_path(name), "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
    return ctx

