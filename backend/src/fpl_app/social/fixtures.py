"""Authored synthetic development examples; neither real posts nor held-out labels."""

ALIASES = {
    "Palmer": ("palmer",),
    "Salah": ("salah",),
    "Mo": ("salah",),
    "Saka": ("saka",),
    "Haaland": ("haaland",),
    "Smith": ("smith-a", "smith-b"),
}
# text, expected player/action, expected abstention
SYNTHETIC_CASES = (
    ("I wouldn't buy Salah.", "salah", "buy", "negated_action"),
    ("Should I buy Salah", "salah", "buy", "question"),
    ("Reporter: 'buy Salah'.", "salah", "buy", "quoted_attribution"),
    ("Buy Mo.", "salah", "buy", None),
    ("Do not sell Saka.", "saka", "sell", "negated_action"),
    ("Anyone selling Saka?", "saka", "unclear", "question"),
    ("I would captain Haaland only if he starts.", "haaland", "captain", None),
    ('The reporter says "buy Salah".', "salah", "buy", "quoted_attribution"),
    ("Buy Smith.", None, "buy", "ambiguous_entity"),
    ("Buy Haaland lol.", "haaland", "buy", "humour_or_sarcasm"),
    ("Saka: Great, another one point cameo.", "saka", "unclear", "humour_or_sarcasm"),
    ("Buy Salah and sell Saka.", "salah", "buy", "multiple_entities_unresolved"),
)
