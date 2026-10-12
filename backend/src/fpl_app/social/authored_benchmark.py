"""240 predeclared authored labels; no platform posts or human-review claim."""

from fpl_app.social.benchmark import BenchmarkExample


def authored_benchmark():
    templates = [
        ("Buy {name} for {gw}.", "buy", "strategy", None, False, None),
        ("Sell {name} before {gw}.", "sell", "strategy", None, False, None),
        ("Hold {name} through {gw}.", "hold", "strategy", None, False, None),
        ("Captain {name} in {gw}.", "captain", "captaincy", None, False, None),
        ("Avoid {name} in {gw}.", "avoid", "strategy", None, False, None),
        ("Bench {name} for {gw}.", "bench", "strategy", None, False, None),
        ("Do not buy {name} for {gw}.", "buy", "strategy", None, False, "negated_action"),
        ("Should I sell {name} for {gw}?", "sell", "strategy", None, True, "question"),
        (
            "Captain {name} in {gw} only if he starts.",
            "captain",
            "captaincy",
            "only if he starts",
            False,
            None,
        ),
        ("Is {name} worth a hit for {gw}?", "unclear", "strategy", None, True, "question"),
        (
            "{name} looks great but I would sell him for {gw}.",
            "sell",
            "strategy",
            None,
            False,
            None,
        ),
        (
            "{name} made a nice cameo in {gw}, clearly captain material.",
            "unclear",
            "captaincy",
            None,
            False,
            "unsupported_sarcasm",
        ),
    ]
    examples = []
    for family, (template, action, topic, condition, question, abstention) in enumerate(templates):
        partition = "development" if family < 8 else "validation" if family < 10 else "test"
        day = {"development": 1, "validation": 2, "test": 3}[partition]
        for name in ("Salah", "Saka", "Haaland", "Palmer"):
            for event in range(10, 15):
                text = template.format(name=name, gw=f"GW {event}")
                expected = {
                    "player_id": name.casefold(),
                    "action": action,
                    "topic": topic,
                    "horizon": f"GW {event}",
                    "condition": condition,
                    "question": question,
                    "abstention": abstention,
                    "kind": "opinion",
                    "span_start": 0,
                    "span_end": len(text),
                    "evidence_span": text,
                }
                examples.append(
                    BenchmarkExample(
                        f"authored-{family}-{name}-{event}",
                        text,
                        f"authored-author-{family}-{name}",
                        f"authored-family-{family}",
                        f"2026-10-{day:02d}T00:00:00Z",
                        partition,
                        (expected,),
                    )
                )
    return examples
