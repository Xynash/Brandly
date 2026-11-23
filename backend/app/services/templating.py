import re

_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class MissingVariables(Exception):
    def __init__(self, names: list[str]):
        super().__init__("Missing values for: " + ", ".join(names))
        self.names = names


def extract_variables(body: str) -> list[str]:
    """Variable names in order of first appearance, without duplicates."""
    seen: list[str] = []
    for m in _VAR.finditer(body):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def render(body: str, values: dict[str, str]) -> str:
    """Fill {{variables}}. Blank or absent values count as missing. Single pass, so a value
    that itself contains {{x}} is never expanded again."""
    missing = [n for n in extract_variables(body) if not str(values.get(n, "")).strip()]
    if missing:
        raise MissingVariables(missing)
    return _VAR.sub(lambda m: str(values[m.group(1)]).strip(), body)
