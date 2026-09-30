from pathlib import Path
import yaml


def generate(results, templates=None):
    if templates is None:
        templates = yaml.safe_load(Path(__file__).with_name("templates.yaml").read_text(encoding="utf-8"))
    return [templates[result.status.value].format(rule_id=result.rule_id, reason=result.reason) for result in results]
