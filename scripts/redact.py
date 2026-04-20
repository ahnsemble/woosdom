import re
import yaml
import argparse
import sys
from pathlib import Path

REDACT_RULES = [
    (r'[0-9]{3}-[0-9]{3,4}-[0-9]{4}', '[PHONE]'),
    (r'[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}', '[EMAIL]'),
    (r'(?:GS|현대|한화|대우|DL|우미|자이)(?:건설|E&C|산업개발)?', '[COMPANY]'),
    (r'[0-9,]+만\s*원|[0-9.]+억|\$[0-9,]+', '[AMOUNT]'),
    (r'\b(?:SCHD|QQQM|TLT|GLDM|SMH|SPMO|JEPI|SVOL|VNQ|PFFD)\b', '[TICKER]'),
    (r'/Users/\w+/', '[PATH]/'),
    (r'(?:마통|카드값|할부|신용대출|portfolio\.json)', '[FINANCIAL]'),
    (r'기준서|252(?:개|건)?(?:\s*규칙)?|6개사\s*비교', '[INTERNAL]'),
]


def load_allow_list(path: Path) -> set:
    if not path.exists():
        return set()
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return {str(v) for vals in data.values() if isinstance(vals, list) for v in vals}


def process(text: str, allow_list: set) -> str:
    for pat, tag in REDACT_RULES:
        def rep(m, t=tag):
            return m.group(0) if m.group(0) in allow_list else t
        text = re.sub(pat, rep, text)
    return text


def test_assertions():
    txt = "연락처 010-1234-5678, GS건설, 자이 500만원, Blocs 제품, /Users/alice/docs"
    allow = {"Blocs"}
    res = process(txt, allow)
    assert "[PHONE]" in res, f"PHONE missing: {res}"
    assert "[COMPANY]" in res, f"COMPANY missing: {res}"
    assert "[AMOUNT]" in res, f"AMOUNT missing: {res}"
    assert "[PATH]/" in res, f"PATH missing: {res}"
    assert "Blocs" in res, f"Blocs allow-list failed: {res}"
    assert "010-1234-5678" not in res
    assert "GS건설" not in res
    assert "alice" not in res
    print("Tests passed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=False, help="Input directory")
    parser.add_argument('--output', required=False, help="Output directory")
    parser.add_argument('--allow', default='scripts/allow_list.yaml')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()

    if args.test:
        test_assertions()
        sys.exit(0)

    if not args.input or not args.output:
        parser.error("--input and --output are required unless --test is used")

    allow_set = load_allow_list(Path(args.allow))
    for src in Path(args.input).rglob("*.md"):
        dst = Path(args.output) / src.relative_to(args.input)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(process(src.read_text('utf-8'), allow_set), 'utf-8')
