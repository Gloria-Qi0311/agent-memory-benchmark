"""Preference Track v0 — curated smoke cases and structural validation.

The first review batch is deliberately curated instead of LLM-generated:
six diagnostic cases (two per capability) and three counterfactual pairs
(six composite cases).  The final decision agent sees only ``decision`` plus
whatever a memory adapter retrieves; it never receives ``writes`` or
``ground_truth`` directly.

Ground truth is executable.  Each candidate exposes preference attributes,
and the expected choice must be the unique candidate matching the largest
number of currently active preferences.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re


OUTPUT_SCHEMA = {
    "choice": "A | B | C",
    "applied_preference_codes": ["preference_code"],
}

_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _write(
    order: int,
    agent_id: str,
    role: str,
    scope: str,
    preference_kind: str,
    utterance: str,
) -> dict:
    return {
        "order": order,
        "agent_id": agent_id,
        "role": role,
        "session_id": f"session_{order}",
        "scope": scope,
        "preference_kind": preference_kind,
        "source_type": "user_explicit",
        "utterance": utterance,
    }


def _candidate(candidate_id: str, description: str, *attributes: str) -> dict:
    return {
        "id": candidate_id,
        "description": description,
        "attributes": list(attributes),
    }


def _decision(
    role: str,
    domain: str,
    context_type: str,
    task: str,
    memory_query: str,
    candidates: list[dict],
) -> dict:
    return {
        "agent_id": "agent_d",
        "role": role,
        "current_context": {
            "domain": domain,
            "context_type": context_type,
        },
        "task": task,
        "memory_query": memory_query,
        "candidates": candidates,
        "instruction": (
            "Use only the current task, candidate information, and retrieved "
            "shared-memory context. Choose the option that best fits the user's "
            "currently applicable preferences. Return JSON only."
        ),
        "output_schema": copy.deepcopy(OUTPUT_SCHEMA),
    }


def _truth(
    active: list[str],
    expected_choice: str,
    required: list[str],
    *,
    wrong_scope: list[str] | None = None,
    expired: list[str] | None = None,
    superseded: list[str] | None = None,
    evidence_groups: list[list[str]] | None = None,
    explanation: str,
) -> dict:
    wrong_scope = wrong_scope or []
    expired = expired or []
    superseded = superseded or []
    return {
        "active_preferences": active,
        "wrong_scope_preferences": wrong_scope,
        "expired_preferences": expired,
        "superseded_preferences": superseded,
        "evidence_groups": evidence_groups or [],
        "expected_choice": expected_choice,
        "required_reason_codes": required,
        "forbidden_reason_codes": wrong_scope + expired + superseded,
        "explanation": explanation,
    }


def _case(
    case_id: str,
    layer: str,
    primary_capability: str,
    capabilities: list[str],
    scenario: str,
    persona: str,
    writes: list[dict],
    decision: dict,
    ground_truth: dict,
    pair_id: str | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "language": "en",
        "pair_id": pair_id,
        "layer": layer,
        "primary_capability": primary_capability,
        "capabilities": capabilities,
        "scenario": scenario,
        "persona": persona,
        "writes": writes,
        "decision": decision,
        "ground_truth": ground_truth,
    }


def _diagnostic_cases() -> list[dict]:
    return [
        _case(
            "PREF-D-MERGE-001",
            "diagnostic",
            "cross_agent_merge",
            ["cross_agent_transfer", "preference_synthesis"],
            "leisure_hotel",
            "Hana",
            [
                _write(1, "travel_agent", "travel discovery agent", "leisure_travel", "stable",
                       "When I travel for leisure, I prefer quiet hotels and try to avoid crowded, noisy places."),
                _write(2, "hotel_agent", "hotel recommendation agent", "leisure_travel", "stable",
                       "I prefer small hotels with local character over standardized international chains."),
            ],
            _decision(
                "Kyoto hotel planner", "travel", "leisure_travel",
                "Hana is planning a five-day leisure trip to a large city. Choose the hotel that best matches her preferences.",
                "What accommodation preferences does Hana have for a leisure trip?",
                [
                    _candidate("A", "A quiet international chain in the city center, with full facilities and convenient transport, but standardized design and little local character.",
                               "quiet", "city_center", "large_chain", "full_service", "little_local_character"),
                    _candidate("B", "A quiet, locally owned boutique hotel with few rooms and distinctive neighborhood character, but limited facilities and a location far from the city center.",
                               "quiet", "small_hotel", "boutique", "local_character", "limited_facilities", "farther_from_center"),
                    _candidate("C", "A small, locally owned design hotel in the city center, with a popular restaurant, concierge service, and easy transport; its rooms overlook a lively pedestrian street and have average soundproofing.",
                               "small_hotel", "local_character", "city_center", "restaurant", "concierge", "easy_transport", "lively", "average_soundproofing"),
                ],
            ),
            _truth(
                ["quiet", "small_hotel", "boutique", "local_character"], "B",
                ["quiet", "small_hotel", "local_character"],
                evidence_groups=[["quiet"], ["small_hotel", "local_character"]],
                explanation="B simultaneously satisfies the two preference fragments learned by different agents.",
            ),
        ),
        _case(
            "PREF-D-MERGE-002",
            "diagnostic",
            "cross_agent_merge",
            ["cross_agent_transfer", "preference_synthesis"],
            "developer_laptop",
            "Alex",
            [
                _write(1, "travel_setup_agent", "mobile work setup agent", "developer_laptop", "stable",
                       "I carry my work laptop between home and the office every day, so I want it to weigh no more than 1.3 kilograms."),
                _write(2, "development_agent", "software development agent", "developer_laptop", "stable",
                       "I run several local containers at once, so I need at least 32 GB of memory and good sustained cooling."),
            ],
            _decision(
                "work laptop agent", "shopping", "developer_laptop",
                "Alex is choosing a laptop for daily software-development work and commuting. Choose the model that best matches his preferences.",
                "What does Alex need from a laptop for commuting and local development?",
                [
                    _candidate("A", "An ultraportable 1.05 kg laptop with 16 GB of memory and quiet low-power cooling.",
                               "ultralight", "under_1_3kg", "sixteen_gb", "low_power_cooling"),
                    _candidate("B", "A 1.28 kg laptop with 32 GB of memory and a dual-fan cooling system suitable for sustained local workloads.",
                               "under_1_3kg", "at_least_32gb", "thirty_two_gb", "sustained_cooling", "dual_fan"),
                    _candidate("C", "A 1.75 kg mobile workstation with 64 GB of memory and the strongest sustained cooling of the three models.",
                               "at_least_32gb", "sixty_four_gb", "sustained_cooling", "strongest_cooling", "heavy"),
                ],
            ),
            _truth(
                ["under_1_3kg", "at_least_32gb", "sustained_cooling"], "B",
                ["under_1_3kg", "at_least_32gb", "sustained_cooling"],
                evidence_groups=[
                    ["under_1_3kg"],
                    ["at_least_32gb", "sustained_cooling"],
                ],
                explanation="B is the only model that stays within the commuting weight limit while meeting the local-development memory and cooling needs.",
            ),
        ),
        _case(
            "PREF-D-UPDATE-001",
            "diagnostic",
            "preference_update",
            ["cross_agent_transfer", "preference_freshness", "stale_preference_rejection"],
            "work_device_purchase",
            "Bao",
            [
                _write(1, "shopping_agent", "shopping assistant", "work_device_purchase", "stable",
                       "I used to prioritize price when buying equipment for work. As long as it did the job, that was good enough for me."),
                _write(2, "work_agent", "work setup agent", "work_device_purchase", "update",
                       "Recent equipment failures have disrupted my work. From now on, reliability comes first; I am willing to pay more and no longer put price first."),
            ],
            _decision(
                "procurement agent", "shopping", "work_device_purchase",
                "Bao needs a new router for work. Choose the option that best matches his current preferences.",
                "What does Bao currently prioritize when buying equipment for work?",
                [
                    _candidate("A", "A mature entry-level model that costs 30% less, covers everyday needs, and includes a standard two-year warranty.",
                               "low_price", "basic_functionality", "mature_entry_model", "standard_warranty"),
                    _candidate("B", "A model that costs 30% more, has the strongest long-term reliability record, and includes a five-year warranty with on-site replacement.",
                               "reliability_first", "proven_stability", "long_warranty", "onsite_replacement"),
                    _candidate("C", "A mid-priced model with the best throughput and management features and a three-year warranty, but only six months of market history.",
                               "mid_price", "high_performance", "feature_rich", "three_year_warranty", "newer_model"),
                ],
            ),
            _truth(
                ["reliability_first", "proven_stability", "long_warranty"], "B",
                ["reliability_first", "proven_stability"],
                superseded=["low_price", "price_first"],
                explanation="The later explicit update supersedes price-first purchasing in this scope.",
            ),
        ),
        _case(
            "PREF-D-UPDATE-002",
            "diagnostic",
            "preference_update",
            ["cross_agent_transfer", "preference_freshness", "stale_preference_rejection"],
            "software_adoption",
            "Chloe",
            [
                _write(1, "tool_scout_agent", "software discovery agent", "team_software", "stable",
                       "I used to prefer mature team tools with predictable releases and long-term support."),
                _write(2, "engineering_agent", "engineering operations agent", "team_software", "update",
                       "Several new automation features have recently improved our efficiency. I now prioritize the latest features and rapid iteration, as long as the vendor provides migration support; maturity is no longer my top concern."),
            ],
            _decision(
                "team tooling agent", "work", "team_software",
                "Chloe needs to choose a new workflow platform for her team. Choose the option that best matches her current preferences.",
                "What does Chloe currently prefer when choosing software for her team?",
                [
                    _candidate("A", "A newly launched platform with the most advanced automation, monthly feature releases, and vendor migration support, but a short track record.",
                               "newest_features", "rapid_iteration", "vendor_migration_support", "short_track_record"),
                    _candidate("B", "A mature all-in-one platform with the broadest feature and plugin set, but complex configuration that requires a certified service partner.",
                               "mature", "feature_rich", "broad_ecosystem", "professional_configuration"),
                    _candidate("C", "A core-workflow platform with years of validation, predictable releases, clear documentation, and long-term support, but fewer advanced features.",
                               "mature", "maintainable", "long_term_support", "stable_release_cycle", "fewer_advanced_features"),
                ],
            ),
            _truth(
                ["newest_features", "rapid_iteration", "vendor_migration_support"], "A",
                ["newest_features", "rapid_iteration", "vendor_migration_support"],
                superseded=["mature", "long_term_support", "stable_release_cycle"],
                explanation="A reflects the new innovation-first preference rather than the old maturity preference.",
            ),
        ),
        _case(
            "PREF-D-BOUNDARY-001",
            "diagnostic",
            "preference_boundary",
            ["cross_agent_transfer", "scope_resolution", "temporary_constraint_filtering"],
            "leisure_vs_business_hotel",
            "Diego",
            [
                _write(1, "leisure_agent", "leisure travel agent", "leisure_travel", "stable",
                       "For leisure trips, I like quiet, slow-paced small hotels and do not mind staying away from busy areas."),
                _write(2, "business_agent", "business travel agent", "business_trip_shanghai_01", "temporary",
                       "For my one-day business trip to Shanghai last month, I needed a chain hotel near a transport hub so I could keep to the schedule."),
            ],
            _decision(
                "vacation planner", "travel", "leisure_travel",
                "Diego is planning a new private island vacation. Choose the accommodation that best matches the preferences applicable to this trip.",
                "Which accommodation preferences apply to Diego's new private vacation?",
                [
                    _candidate("A", "An international beachfront resort near the ferry terminal, with full facilities but busy common areas.",
                               "large_chain", "transport_hub_proximity", "full_service", "busy"),
                    _candidate("B", "A quiet small seaside guesthouse away from the commercial district, with few rooms and a relaxed pace but limited dining options.",
                               "quiet", "small_hotel", "slow_paced", "farther_from_center"),
                    _candidate("C", "An independent design hotel in the island town center, within walking distance of restaurants and the night market, but lively in the evenings.",
                               "town_center", "independent_design_hotel", "walkable", "lively"),
                ],
            ),
            _truth(
                ["quiet", "small_hotel", "slow_paced", "farther_from_center"], "B",
                ["quiet", "small_hotel", "slow_paced"],
                expired=["transport_hub_proximity", "large_chain"],
                explanation="The Shanghai business-trip constraint must not propagate into a new leisure trip.",
            ),
        ),
        _case(
            "PREF-D-BOUNDARY-002",
            "diagnostic",
            "preference_boundary",
            ["cross_agent_transfer", "scope_resolution", "temporary_constraint_filtering"],
            "personal_invitation_style",
            "Eun",
            [
                _write(1, "personal_writing_agent", "personal writing agent", "personal_messages", "stable",
                       "For event invitations to friends, I prefer a concise, neutral style. Clear time, location, and RSVP details are enough; I do not need much emotional language."),
                _write(2, "board_report_agent", "board report agent", "board_report_q3", "temporary",
                       "For last week's board report, please use a formal tone, avoid emojis, and keep it under 300 words."),
            ],
            _decision(
                "personal invitation agent", "writing", "personal_messages",
                "Eun needs to write a birthday party invitation to friends. Choose the writing style that best matches her applicable preferences.",
                "What writing style does Eun prefer for a birthday invitation to friends?",
                [
                    _candidate("A", "A formally worded invitation that fully explains the arrangements and response process, uses no emojis, and stays under 300 words.",
                               "formal_tone", "complete_details", "no_emoji", "max_300_words"),
                    _candidate("B", "A warm, casual invitation with a personal greeting and a little playful language, while clearly stating the time and location.",
                               "warm_tone", "casual", "playful"),
                    _candidate("C", "A concise, neutral invitation template focused on the time, location, and RSVP, making it easy to confirm quickly.",
                               "neutral", "concise", "template", "rsvp_focused", "clear_details"),
                ],
            ),
            _truth(
                ["neutral", "concise", "rsvp_focused", "clear_details"], "C",
                ["neutral", "concise", "rsvp_focused"],
                expired=["formal_tone", "no_emoji", "max_300_words"],
                explanation="The board-report constraints were task-local and should not affect a personal invitation.",
            ),
        ),
    ]


def _composite_cases() -> list[dict]:
    hotel_decision = _decision(
        "Kyoto vacation planner", "travel", "leisure_travel",
        "The user is taking a five-day private vacation in Kyoto. Choose the hotel that best matches the user's current preferences.",
        "What accommodation preferences does this user have for a private vacation in Kyoto?",
        [
            _candidate("A", "A large international chain in the city center, with convenient transport and consistent service, but many rooms and a busy atmosphere.",
                       "city_center", "large_chain", "brand_consistency", "full_service", "busy"),
            _candidate("C", "A quiet local machiya boutique hotel with few rooms and distinctive character, but farther from the main sights.",
                       "quiet", "boutique", "local_character", "farther_from_center"),
            _candidate("B", "A modern serviced apartment near Kyoto Station, with a kitchen and washer for longer stays, but limited hotel service and local character.",
                       "station_proximity", "serviced_apartment", "kitchen", "laundry", "self_service"),
        ],
    )

    analysis_decision = _decision(
        "product analysis agent", "work", "product_decision",
        "A few weeks later, the user needs to compare two vendor proposals in an internal product-team review; this material is not for training. Choose the presentation format that best matches the user's current analysis preferences.",
        "What presentation style does this user prefer when comparing vendor proposals?",
        [
            _candidate("A", "Open with a recommendation, then use three concise bullets to summarize the key trade-offs and next action.",
                       "conclusion_first", "concise", "action_oriented", "bullet_points"),
            _candidate("C", "Systematically present the full data, evidence sources, risk assumptions, and detailed reasoning before giving a conclusion.",
                       "detailed", "evidence_rich", "full_reasoning", "risk_analysis"),
            _candidate("B", "Start with a real implementation case, then add a one-page comparison table without recommending an option, leaving the review team to decide.",
                       "case_first", "accessible", "comparison_table", "reader_decides"),
        ],
    )

    software_decision = _decision(
        "software procurement agent", "shopping", "team_software",
        "The user needs to choose a project management platform for a ten-person team to use daily over the next year. Choose the option that best matches the user's current preferences.",
        "What does this user currently prioritize when choosing daily project management software for the team?",
        [
            _candidate("A", "The lowest-priced option, with simple core features and same-day rollout; it relies mainly on community support and has fewer integrations.",
                       "low_price", "simple_setup", "basic_functionality", "same_day_launch", "community_support"),
            _candidate("C", "A higher-priced option with years of validation, a strong reliability record, mature integrations, and long-term vendor support, but a two-week rollout.",
                       "proven_reliability", "stable", "mature_ecosystem", "long_term_support", "two_week_setup"),
            _candidate("B", "A new platform with the most automation features and free vendor migration assistance, but a short track record and frequent releases.",
                       "newest_features", "advanced_automation", "vendor_migration_support", "short_track_record", "frequent_change"),
        ],
    )

    return [
        _case(
            "PREF-C-HOTEL-001-A", "composite", "composite_journey",
            ["cross_agent_merge", "scope_resolution", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_hotel", "Farida",
            [
                _write(1, "leisure_agent", "leisure travel agent", "leisure_travel", "stable",
                       "On private vacations, quiet matters most to me, and I dislike crowded, noisy hotels."),
                _write(2, "hotel_agent", "hotel discovery agent", "leisure_travel", "stable",
                       "I prefer small accommodations with local character; large international chains do not appeal to me."),
                _write(3, "family_trip_agent", "family travel agent", "family_trip_last_month", "temporary",
                       "For a week-long family stay last month, the room had to include a kitchen and a washer."),
            ],
            copy.deepcopy(hotel_decision),
            _truth(
                ["quiet", "boutique", "local_character"], "C",
                ["quiet", "boutique", "local_character"],
                expired=["kitchen", "laundry"],
                explanation="The prior family-trip facilities were task-local; the stable leisure preferences select C.",
            ),
            pair_id="PREF-C-HOTEL-001",
        ),
        _case(
            "PREF-C-HOTEL-001-B", "composite", "composite_journey",
            ["cross_agent_merge", "scope_resolution", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_hotel", "Farida",
            [
                _write(1, "leisure_agent", "leisure travel agent", "leisure_travel", "stable",
                       "For hotels on private vacations, convenient transport in the city center matters most to me."),
                _write(2, "hotel_agent", "hotel discovery agent", "leisure_travel", "stable",
                       "I trust large international chains with consistent service standards and full facilities."),
                _write(3, "family_trip_agent", "family travel agent", "family_trip_last_month", "temporary",
                       "For a week-long family stay last month, the room had to include a kitchen and a washer."),
            ],
            copy.deepcopy(hotel_decision),
            _truth(
                ["city_center", "large_chain", "brand_consistency", "full_service"], "A",
                ["city_center", "large_chain", "brand_consistency"],
                expired=["kitchen", "laundry"],
                explanation="The same decision surface flips because this user's leisure preferences favor option A.",
            ),
            pair_id="PREF-C-HOTEL-001",
        ),
        _case(
            "PREF-C-ANALYSIS-001-A", "composite", "composite_journey",
            ["cross_agent_merge", "scope_resolution", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_analysis_style", "Hana",
            [
                _write(1, "strategy_agent", "product strategy agent", "product_decision", "stable",
                       "When comparing proposals, give me the recommendation first; I do not want to read a long background section before it."),
                _write(2, "writing_agent", "business writing agent", "product_decision", "stable",
                       "Do not open with the full derivation. Start with a few clear points on what to choose and what to do next."),
                _write(3, "training_agent", "new-hire training agent", "new_hire_training_last_month", "temporary",
                       "For last month's new-hire training, start with a real case to explain the situation and do not make the purchasing decision for them."),
            ],
            copy.deepcopy(analysis_decision),
            _truth(
                ["conclusion_first", "concise", "action_oriented", "bullet_points"], "A",
                ["conclusion_first", "concise", "action_oriented"],
                expired=["case_first", "reader_decides"],
                explanation="The prior training format was task-local; the stable product-decision preference selects A.",
            ),
            pair_id="PREF-C-ANALYSIS-001",
        ),
        _case(
            "PREF-C-ANALYSIS-001-B", "composite", "composite_journey",
            ["cross_agent_merge", "scope_resolution", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_analysis_style", "Hana",
            [
                _write(1, "strategy_agent", "product strategy agent", "product_decision", "stable",
                       "For important proposal comparisons, I want the complete data and evidence sources, not just a simplified conclusion."),
                _write(2, "writing_agent", "business writing agent", "product_decision", "stable",
                       "Write out the risk assumptions and reasoning clearly so I can verify the analysis myself."),
                _write(3, "training_agent", "new-hire training agent", "new_hire_training_last_month", "temporary",
                       "For last month's new-hire training, start with a real case to explain the situation and do not make the purchasing decision for them."),
            ],
            copy.deepcopy(analysis_decision),
            _truth(
                ["detailed", "evidence_rich", "full_reasoning", "risk_analysis"], "C",
                ["detailed", "evidence_rich", "risk_analysis"],
                expired=["case_first", "reader_decides"],
                explanation="The prior training format was task-local; the stable evidence-first preference selects C.",
            ),
            pair_id="PREF-C-ANALYSIS-001",
        ),
        _case(
            "PREF-C-SOFTWARE-001-A", "composite", "composite_journey",
            ["preference_update", "stale_preference_rejection", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_software_purchase", "Chloe",
            [
                _write(1, "procurement_agent", "software procurement agent", "team_software", "stable",
                       "I used to look at price first when choosing team software. If it worked, that was enough."),
                _write(2, "team_operations_agent", "team operations agent", "team_software", "update",
                       "After repeated failures with low-cost tools, I now prioritize proven, stable options with long-term support for this team's daily software; price no longer comes first."),
                _write(3, "demo_agent", "innovation demo agent", "innovation_demo_last_month", "temporary",
                       "For a one-off innovation demo last month, it was fine to temporarily try the platform with the newest features."),
            ],
            copy.deepcopy(software_decision),
            _truth(
                ["proven_reliability", "stable", "long_term_support"], "C",
                ["proven_reliability", "stable", "long_term_support"],
                expired=["newest_features"],
                superseded=["low_price"],
                explanation="The stable updated preference applies to this team's daily software; the demo exception is expired.",
            ),
            pair_id="PREF-C-SOFTWARE-001",
        ),
        _case(
            "PREF-C-SOFTWARE-001-B", "composite", "composite_journey",
            ["preference_update", "stale_preference_rejection", "temporary_constraint_filtering", "counterfactual"],
            "counterfactual_software_purchase", "Chloe",
            [
                _write(1, "procurement_agent", "software procurement agent", "team_software", "stable",
                       "I used to choose mature team software with comprehensive features and strong support."),
                _write(2, "team_operations_agent", "team operations agent", "team_software", "update",
                       "This team's budget will be tight for the next year. For their daily software, I now prioritize price and fast rollout instead of paying for a full ecosystem they will not use."),
                _write(3, "demo_agent", "innovation demo agent", "innovation_demo_last_month", "temporary",
                       "For a one-off innovation demo last month, it was fine to temporarily try the platform with the newest features."),
            ],
            copy.deepcopy(software_decision),
            _truth(
                ["low_price", "simple_setup", "basic_functionality"], "A",
                ["low_price", "simple_setup"],
                expired=["newest_features"],
                superseded=["mature_ecosystem", "long_term_support"],
                explanation="The explicit budget-first update selects A; the innovation-demo exception is expired.",
            ),
            pair_id="PREF-C-SOFTWARE-001",
        ),
    ]


def preference_match_scores(case: dict) -> dict[str, int]:
    """Score candidate attributes against the case's active preferences."""
    active = set(case["ground_truth"]["active_preferences"])
    return {
        candidate["id"]: len(active.intersection(candidate["attributes"]))
        for candidate in case["decision"]["candidates"]
    }


def validate_case(case: dict) -> None:
    """Raise ValueError when a curated case violates the executable contract."""
    required_top_level = {
        "case_id", "language", "pair_id", "layer", "primary_capability", "capabilities",
        "scenario", "persona", "writes", "decision", "ground_truth",
    }
    missing = required_top_level.difference(case)
    if missing:
        raise ValueError(f"{case.get('case_id', '<unknown>')}: missing fields {sorted(missing)}")
    if case["language"] != "en":
        raise ValueError(f"{case['case_id']}: Preference Track smoke cases must use English")
    user_facing_text = [write["utterance"] for write in case["writes"]]
    user_facing_text.extend([
        case["decision"]["task"],
        case["decision"]["memory_query"],
        case["decision"]["instruction"],
    ])
    user_facing_text.extend(
        candidate["description"] for candidate in case["decision"]["candidates"]
    )
    if any(_CJK_RE.search(text) for text in user_facing_text):
        raise ValueError(f"{case['case_id']}: user-facing benchmark input contains CJK text")

    if case["layer"] not in {"diagnostic", "composite"}:
        raise ValueError(f"{case['case_id']}: invalid layer")
    if case["layer"] == "composite" and not case["pair_id"]:
        raise ValueError(f"{case['case_id']}: composite case requires pair_id")
    if case["layer"] == "diagnostic" and case["pair_id"] is not None:
        raise ValueError(f"{case['case_id']}: diagnostic case must not have pair_id")
    if len(case["writes"]) < 2:
        raise ValueError(f"{case['case_id']}: preference case needs at least two writer agents")

    orders = [write["order"] for write in case["writes"]]
    if orders != list(range(1, len(orders) + 1)):
        raise ValueError(f"{case['case_id']}: writes must have contiguous chronological order")
    if any(write["source_type"] != "user_explicit" for write in case["writes"]):
        raise ValueError(f"{case['case_id']}: v0 only allows explicit user preference evidence")
    if any(
        write["utterance"].startswith(f"{case['persona']}说：")
        for write in case["writes"]
    ):
        raise ValueError(f"{case['case_id']}: writer input must be direct user speech")

    decision = case["decision"]
    if decision.get("agent_id") != "agent_d":
        raise ValueError(f"{case['case_id']}: final decision must be made by agent_d")
    candidates = decision.get("candidates", [])
    if len(candidates) != 3:
        raise ValueError(f"{case['case_id']}: exactly three candidates are required")
    candidate_ids = [candidate["id"] for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError(f"{case['case_id']}: duplicate candidate ids")

    truth = case["ground_truth"]
    active = set(truth["active_preferences"])
    required = set(truth["required_reason_codes"])
    invalid = set(truth["forbidden_reason_codes"])
    if not required.issubset(active):
        raise ValueError(f"{case['case_id']}: required reasons must be active")
    if active.intersection(invalid):
        raise ValueError(f"{case['case_id']}: active and forbidden preferences overlap")
    if truth["expected_choice"] not in candidate_ids:
        raise ValueError(f"{case['case_id']}: expected choice is not a candidate")

    evidence_groups = truth.get("evidence_groups", [])
    if case["primary_capability"] == "cross_agent_merge":
        if len(evidence_groups) != len(case["writes"]):
            raise ValueError(
                f"{case['case_id']}: merge cases require one evidence group per writer"
            )
        for group in evidence_groups:
            group_set = set(group)
            group_scores = {
                candidate["id"]: len(group_set.intersection(candidate["attributes"]))
                for candidate in candidates
            }
            group_best = max(group_scores.values())
            group_winners = [
                candidate_id
                for candidate_id, score in group_scores.items()
                if score == group_best
            ]
            if group_winners == [truth["expected_choice"]]:
                raise ValueError(
                    f"{case['case_id']}: one writer alone uniquely determines the full target; "
                    f"group={group}, scores={group_scores}"
                )

    scores = preference_match_scores(case)
    best_score = max(scores.values())
    winners = [candidate_id for candidate_id, score in scores.items() if score == best_score]
    if winners != [truth["expected_choice"]]:
        raise ValueError(
            f"{case['case_id']}: expected {truth['expected_choice']} is not unique winner; "
            f"scores={scores}, winners={winners}"
        )


def validate_cases(cases: list[dict]) -> None:
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate preference case ids")
    for case in cases:
        validate_case(case)

    pair_ids = {case["pair_id"] for case in cases if case["pair_id"]}
    for pair_id in pair_ids:
        pair = [case for case in cases if case["pair_id"] == pair_id]
        if len(pair) != 2:
            raise ValueError(f"{pair_id}: counterfactual pair must contain exactly two cases")
        left, right = pair
        if left["decision"] != right["decision"]:
            raise ValueError(f"{pair_id}: decision surface must be identical")
        if left["persona"] != right["persona"]:
            raise ValueError(f"{pair_id}: persona must be held constant")
        if left["writes"][-1] != right["writes"][-1]:
            raise ValueError(f"{pair_id}: scoped temporary event must be held constant")
        if (
            left["ground_truth"]["expected_choice"]
            == right["ground_truth"]["expected_choice"]
        ):
            raise ValueError(f"{pair_id}: counterfactual truth must flip")


def smoke_cases() -> list[dict]:
    """Return a fresh copy of the 12 curated review cases."""
    cases = _diagnostic_cases() + _composite_cases()
    validate_cases(cases)
    return copy.deepcopy(cases)


def generate_smoke(out_path: Path) -> None:
    cases = smoke_cases()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(cases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
