"""Offline authored semantic benchmark; not independent human/live accuracy."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))


def main():
    from fpl_app.social.authored_benchmark import authored_benchmark
    from fpl_app.social.benchmark import evaluate_semantics
    from fpl_app.social.extraction import Extractor
    from fpl_app.social.records import Capability, SocialPost

    rows = authored_benchmark()
    capability = Capability(
        provider="synthetic",
        reference="authored",
        allow_inference=True,
        allow_derived_features=True,
    )
    extractor = Extractor(
        {name: (name.casefold(),) for name in ("Salah", "Saka", "Haaland", "Palmer")}
    )
    predictions = {
        row.example_id: extractor.extract(
            SocialPost(
                post_id=row.example_id,
                author_id=row.author_id,
                provider="synthetic",
                text=row.text,
                created_at=row.created_at,
                observed_at=row.created_at,
                evidence_family=row.family_id,
                query="authored benchmark",
                capability_reference="authored",
                synthetic=True,
            ),
            capability,
        )
        for row in rows
    }
    print(
        json.dumps(
            {
                "grammar_comparator": evaluate_semantics(rows, predictions),
                "structured_model": "not_configured",
                "independent_human_review": "unavailable",
                "live_sources": "disabled",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
