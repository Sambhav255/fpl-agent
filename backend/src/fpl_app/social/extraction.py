"""Conservative explicit-grammar baseline, not a trained semantic model."""

import re
from hashlib import sha256

from .records import Action, Capability, Claim, SocialPost, Topic


class Extractor:
    def __init__(self, aliases: dict[str, tuple[str, ...]]) -> None:
        self.aliases = {k.casefold(): v for k, v in aliases.items()}
        self.pattern = (
            re.compile(
                r"(?<!\w)("
                + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
                + r")(?!\w)",
                re.IGNORECASE,
            )
            if aliases
            else None
        )

    def extract(self, post: SocialPost, capability: Capability) -> list[Claim]:
        if (
            capability.provider != post.provider
            or capability.reference != post.capability_reference
            or not capability.allow_inference
            or not capability.allow_derived_features
        ):
            raise PermissionError("Local inference and derived claims require explicit rights")
        if post.provider == "synthetic" and not post.synthetic:
            raise ValueError("Synthetic text must be labelled")
        if post.language != "en" or self.pattern is None:
            return []
        claims: list[Claim] = []
        # Each clause has its own action. Pronouns resolve only to one preceding entity.
        previous: str | None = None
        for segment in re.finditer(r"[^.!;\n]+[.!;]?", post.text):
            span = segment.group()
            mentions = list(self.pattern.finditer(span))
            players = {p for m in mentions for p in self.aliases[m.group().casefold()]}
            ambiguous = any(len(self.aliases[m.group().casefold()]) != 1 for m in mentions)
            if not players and previous and re.search(r"\b(him|he)\b", span, re.IGNORECASE):
                players = {previous}
            if not players:
                continue
            question = "?" in span or bool(
                re.search(r"^\s*(should|can|could|would|anyone|who|is|are)\b", span, re.IGNORECASE)
            )
            joke = bool(
                re.search(
                    r"\b(lol|lmao|joking|joke|yeah right)\b|one point cameo", span, re.IGNORECASE
                )
            )
            quoted = bool(
                re.search(
                    r"[\"“”]|(?<!\w)'|'(?!\w)|\b(says|said|according to)\b",
                    span,
                    re.IGNORECASE,
                )
            )
            attribution_match = re.search(r"([\w ]+)\s+(?:says|said)\b", span, re.IGNORECASE)
            attribution = attribution_match.group(1).strip() if attribution_match else None
            condition_match = re.search(r"\b(if|unless|only when)\b(.+)", span, re.IGNORECASE)
            condition = condition_match.group().strip() if condition_match else None
            horizon_match = re.search(
                r"\bGW\s*\d+\b|this match|after the break", span, re.IGNORECASE
            )
            horizon = horizon_match.group() if horizon_match else "unspecified"
            funding = re.search(
                r"\b(?:sell)\s+(\w+|him)\s+to\s+fund\s+(\w+)\b", span, re.IGNORECASE
            )
            funding_target: str | None = None
            funding_seller: str | None = None
            if funding:
                antecedents = {
                    p
                    for m in mentions
                    if m.start() < funding.start()
                    for p in self.aliases[m.group().casefold()]
                }
                local_previous = next(iter(antecedents)) if len(antecedents) == 1 else previous
                targets = self.aliases.get(funding.group(2).casefold(), ())
                sellers = self.aliases.get(funding.group(1).casefold(), ())
                funding_target = targets[0] if len(targets) == 1 else None
                funding_seller = (
                    local_previous
                    if funding.group(1).casefold() == "him"
                    else (sellers[0] if len(sellers) == 1 else None)
                )
                if funding_target and funding_seller:
                    players.update((funding_target, funding_seller))
            for player in sorted(players):
                action: Action = "unclear"
                topic: Topic = "strategy"
                negated = False
                abstention = None
                if funding_target and funding_seller:
                    action = "buy" if player == funding_target else "sell"
                    negated = bool(
                        re.search(
                            r"\b(no|not|never|don't|do not|wouldn't|shouldn't|can't|cannot|won't)\s*$",
                            (span[: funding.start()] if funding else "").replace("’", "'"),
                            re.IGNORECASE,
                        )
                    )
                else:
                    # Action immediately preceding a named player, or singular pronoun.
                    for match in re.finditer(
                        r"\b(buy|sell|hold|captain|avoid|bench)\s+([\w -]+)", span, re.IGNORECASE
                    ):
                        target_text = match.group(2)
                        target = self.pattern.match(target_text)
                        ids = self.aliases[target.group().casefold()] if target else ()
                        if player in ids or (
                            len(players) == 1
                            and re.match(r"(him|he)\b", target_text, re.IGNORECASE)
                        ):
                            action = match.group(1).lower()  # type: ignore[assignment]
                            prefix = span[: match.start()]
                            negated = bool(
                                re.search(
                                    r"\b(no|not|never|don't|do not|wouldn't|shouldn't|can't|cannot|won't)\s*$",
                                    prefix.replace("’", "'"),
                                    re.IGNORECASE,
                                )
                            )
                            break
                if action == "captain":
                    topic = "captaincy"
                if (
                    re.search(r"\b(trained|starts|out for|return|injured)\b", span, re.IGNORECASE)
                    and action == "unclear"
                ):
                    topic = "availability"
                if ambiguous:
                    abstention = "ambiguous_entity"
                elif joke:
                    abstention = "humour_or_sarcasm"
                elif question:
                    abstention = "question"
                elif quoted:
                    abstention = "quoted_attribution"
                elif negated:
                    abstention = "negated_action"
                elif len(players) > 1 and not (
                    funding_target
                    and funding_seller
                    and players == {funding_target, funding_seller}
                ):
                    abstention = "multiple_entities_unresolved"
                elif action == "unclear":
                    abstention = "unsupported_grammar"
                claims.append(
                    Claim(
                        claim_id=f"{post.post_id}:{segment.start()}:{player}",
                        post_id=post.post_id,
                        author_id=post.author_id,
                        player_id=None if ambiguous else player,
                        topic=topic,
                        action=action,
                        evidence_span=span,
                        span_start=segment.start(),
                        span_end=segment.end(),
                        evidence_family=post.evidence_family
                        or "exact-text:"
                        + sha256(" ".join(post.text.casefold().split()).encode()).hexdigest(),
                        observed_at=post.observed_at,
                        horizon=horizon,
                        condition=condition,
                        funding_player_id=funding_target
                        if player == funding_seller
                        else funding_seller,
                        negated=negated,
                        quoted=quoted,
                        attribution=attribution,
                        question=question,
                        abstention=abstention,
                        kind="report" if topic == "availability" else "opinion",
                    )
                )
            previous = next(iter(players)) if len(players) == 1 and not ambiguous else None
        return claims
