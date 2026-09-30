"""Model selection is explicit and imports optional backends only when selected."""
from pipeline.config import ROOT, load_yaml, resolve_path
from pipeline.components import load_component


def create_model(kind, config, catalog=None):
    catalog = catalog if catalog is not None else load_yaml(ROOT / "configs/models.yaml")
    if catalog.get("schema_version") != 1:
        raise ValueError("Unsupported model catalog")
    name = config.get("model")
    available = catalog.get(kind, {})
    if name not in available:
        raise ValueError(f"Unknown {kind} model: {name!r}; available: {list(available)}")
    spec = available[name]
    if spec.get("status") == "pending":
        raise NotImplementedError(f"{kind} adapter {name!r} is pending implementation")
    options = {**spec.get("defaults", {}), **config.get("options", {})}
    for key in ("weights", "model_path"):
        if key in options:
            options[key] = resolve_path(options[key])
    model = load_component(spec["implementation"])(**options)
    method = "transcribe" if kind == "asr" else "detect"
    if not callable(getattr(model, method, None)):
        raise TypeError(f"{name} must implement {method}()")
    return model
