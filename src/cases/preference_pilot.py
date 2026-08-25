"""Thirty-case Preference Track pilot built on the reviewed smoke schema.

The pilot keeps the original twelve surfaces (with the disputed merge case
repaired) and adds six diagnostic cases plus six counterfactual pairs.  Cases
are curated rather than LLM-generated so every authored trade-off and ground
truth remains inspectable.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

from .preference import (
    _candidate,
    _case,
    _decision,
    _truth,
    _write,
    smoke_cases,
    validate_cases,
)


def _additional_diagnostic_cases() -> list[dict]:
    return [
        _case(
            "PREF-D-MERGE-003", "diagnostic", "cross_agent_merge",
            ["cross_agent_transfer", "preference_synthesis"],
            "restaurant_choice", "Iris",
            [
                _write(1, "food_agent", "restaurant discovery agent", "personal_dining", "stable",
                       "When choosing a restaurant for myself, I want a menu with several genuinely plant-based main dishes, not just side salads."),
                _write(2, "social_agent", "social planning agent", "personal_dining", "stable",
                       "I prefer restaurants quiet enough for an unhurried conversation; loud, crowded dining rooms wear me out."),
            ],
            _decision(
                "dinner planner", "dining", "personal_dining",
                "Iris is meeting a close friend for dinner. Choose the restaurant that best matches her preferences.",
                "What restaurant qualities does Iris prefer for a personal dinner?",
                [
                    _candidate("A", "A lively plant-based food hall with eight vegan mains, communal tables, loud music, and an average dinner price of $30 per person.",
                               "plant_based_mains", "many_vegan_options", "loud", "crowded", "standard_price"),
                    _candidate("C", "A small, quiet neighborhood restaurant with five plant-based mains, spaced tables, a relaxed two-hour seating, and an average dinner price of $55 per person.",
                               "plant_based_mains", "many_vegan_options", "quiet", "uncrowded", "unhurried", "premium_price"),
                    _candidate("B", "A small, quiet traditional grill with spaced tables, a relaxed two-hour seating, only one plant-based main, and an average dinner price of $30 per person.",
                               "quiet", "uncrowded", "unhurried", "limited_plant_based", "standard_price"),
                ],
            ),
            _truth(
                ["plant_based_mains", "many_vegan_options", "quiet", "uncrowded"], "C",
                ["plant_based_mains", "quiet"],
                evidence_groups=[["plant_based_mains", "many_vegan_options"], ["quiet", "uncrowded"]],
                explanation="C is the only option that combines a real plant-based menu with a quiet setting.",
            ),
        ),
        _case(
            "PREF-D-MERGE-004", "diagnostic", "cross_agent_merge",
            ["cross_agent_transfer", "preference_synthesis"],
            "home_office_chair", "Jonah",
            [
                _write(1, "home_agent", "home office planning agent", "home_office_chair", "stable",
                       "My desk nook is narrow. The chair must be no more than 60 centimeters wide, and within that limit I prefer the most compact option."),
                _write(2, "ergonomics_agent", "workplace ergonomics agent", "home_office_chair", "stable",
                       "I sit for long work sessions and want adjustable lumbar support; the more completely I can adjust its height and depth, the better."),
            ],
            _decision(
                "home office shopping agent", "shopping", "home_office_chair",
                "Jonah is buying a chair for his home office. Choose the chair that best matches his preferences.",
                "What size and back-support features does Jonah need in a home office chair?",
                [
                    _candidate("A", "A compact 48 cm-wide task chair with a fixed mesh back and no adjustable lumbar support.",
                               "most_compact", "under_60cm", "fixed_back", "no_adjustable_lumbar"),
                    _candidate("C", "A $550, 58 cm-wide compact ergonomic chair with adjustable lumbar height and depth, designed for long work sessions.",
                               "under_60cm", "adjustable_lumbar", "lumbar_height_depth", "long_session_support", "premium_price"),
                    _candidate("B", "A $320, 68 cm-wide executive ergonomic chair with the widest lumbar height-and-depth adjustment range and a larger padded back.",
                               "wide", "strongest_lumbar", "adjustable_lumbar", "lumbar_height_depth", "widest_adjustment_range", "long_session_support", "mid_price"),
                ],
            ),
            _truth(
                ["under_60cm", "adjustable_lumbar", "lumbar_height_depth", "long_session_support"], "C",
                ["under_60cm", "adjustable_lumbar", "lumbar_height_depth"],
                evidence_groups=[["most_compact"], ["widest_adjustment_range"]],
                explanation="C is the only chair narrow enough for the desk nook while also providing adjustable lumbar support for long sessions.",
            ),
        ),
        _case(
            "PREF-D-UPDATE-003", "diagnostic", "preference_update",
            ["cross_agent_transfer", "preference_freshness", "stale_preference_rejection"],
            "exercise_class", "Kavya",
            [
                _write(1, "fitness_agent", "fitness discovery agent", "weekly_exercise", "stable",
                       "I used to choose intense group workouts because the competition kept me motivated."),
                _write(2, "routine_agent", "weekly routine agent", "weekly_exercise", "update",
                       "My routine has changed. I now stick with low-impact sessions I can do independently at a steady pace; group competition is no longer what I want."),
            ],
            _decision(
                "fitness planning agent", "wellness", "weekly_exercise",
                "Kavya is choosing a recurring weekly exercise class. Choose the option that best matches her current preferences.",
                "What kind of weekly exercise does Kavya currently prefer?",
                [
                    _candidate("A", "A high-intensity team circuit with leaderboards, partner drills, and a fixed competitive pace.",
                               "high_intensity", "group_competition", "leaderboard"),
                    _candidate("C", "A low-impact studio session with individual stations, self-paced progress, and optional instructor guidance.",
                               "low_impact", "independent", "steady_pace", "self_paced"),
                    _candidate("B", "A moderate dance class with a social group format, synchronized routines, and energetic music.",
                               "moderate_intensity", "social_group", "fixed_pace"),
                ],
            ),
            _truth(
                ["low_impact", "independent", "steady_pace", "self_paced"], "C",
                ["low_impact", "independent", "steady_pace"],
                superseded=["high_intensity", "group_competition"],
                explanation="The explicit routine change supersedes the former preference for competitive group exercise.",
            ),
        ),
        _case(
            "PREF-D-UPDATE-004", "diagnostic", "preference_update",
            ["cross_agent_transfer", "preference_freshness", "stale_preference_rejection"],
            "grocery_fulfillment", "Luis",
            [
                _write(1, "grocery_agent", "grocery shopping agent", "weekly_groceries", "stable",
                       "I used to choose the fastest grocery delivery window, even when it cost more."),
                _write(2, "household_agent", "household planning agent", "weekly_groceries", "update",
                       "I work near the market now. For weekly groceries, I prefer a scheduled pickup with minimal packaging, and speed is no longer worth an extra delivery fee."),
            ],
            _decision(
                "grocery fulfillment agent", "shopping", "weekly_groceries",
                "Luis is placing his regular weekly grocery order. Choose the fulfillment option that best matches his current preferences.",
                "How does Luis currently prefer to receive his weekly groceries?",
                [
                    _candidate("B", "A ninety-minute home delivery with a priority fee and individually bagged categories.",
                               "fastest_delivery", "priority_fee", "extra_packaging"),
                    _candidate("A", "A scheduled pickup beside Luis's workplace, packed together in reusable crates with no delivery fee.",
                               "scheduled_pickup", "near_work", "minimal_packaging", "no_delivery_fee"),
                    _candidate("C", "A next-day home delivery with a small fee and standard disposable bags.",
                               "next_day_delivery", "small_fee", "standard_packaging"),
                ],
            ),
            _truth(
                ["scheduled_pickup", "near_work", "minimal_packaging", "no_delivery_fee"], "A",
                ["scheduled_pickup", "minimal_packaging"],
                superseded=["fastest_delivery", "priority_fee"],
                explanation="The current pickup and packaging preference replaces the previous speed-first choice.",
            ),
        ),
        _case(
            "PREF-D-BOUNDARY-003", "diagnostic", "preference_boundary",
            ["cross_agent_transfer", "scope_resolution", "temporary_constraint_filtering"],
            "personal_vs_client_dinner", "Maya",
            [
                _write(1, "food_agent", "personal dining agent", "personal_dining", "stable",
                       "For my own dinners, I enjoy spicy regional food and like trying dishes I have not had before."),
                _write(2, "client_agent", "client hospitality agent", "client_dinner_last_month", "temporary",
                       "For last month's client dinner, I needed a quiet private room and a mild, familiar menu because the guests had different tastes."),
            ],
            _decision(
                "personal dinner agent", "dining", "personal_dining",
                "Maya is choosing a restaurant for a casual dinner with a close friend. Choose the option that best matches Maya's applicable preferences.",
                "What dining preferences apply to Maya's casual personal dinner?",
                [
                    _candidate("A", "A quiet hotel dining room with a private booth and a familiar mild international menu.",
                               "quiet", "private_room", "mild", "familiar_menu"),
                    _candidate("C", "A casual regional restaurant known for spicy seasonal dishes and a rotating menu of less familiar specialties.",
                               "spicy", "regional_food", "novel_dishes", "casual"),
                    _candidate("B", "A popular pizza restaurant with a familiar menu, lively atmosphere, and several shareable classics.",
                               "familiar_menu", "lively", "shareable"),
                ],
            ),
            _truth(
                ["spicy", "regional_food", "novel_dishes"], "C",
                ["spicy", "regional_food", "novel_dishes"],
                expired=["quiet", "private_room", "mild", "familiar_menu"],
                explanation="The client-dinner requirements were guest-specific and do not replace Maya's personal dining preference.",
            ),
        ),
        _case(
            "PREF-D-BOUNDARY-004", "diagnostic", "preference_boundary",
            ["cross_agent_transfer", "scope_resolution", "temporary_constraint_filtering"],
            "routine_project_communication", "Noah",
            [
                _write(1, "collaboration_agent", "collaboration agent", "routine_project_work", "stable",
                       "For routine project work, I prefer written asynchronous updates that I can review and respond to in my own time."),
                _write(2, "incident_agent", "incident response agent", "outage_last_week", "temporary",
                       "During last week's production outage, call me immediately and keep a live video room open until service is restored."),
            ],
            _decision(
                "project setup agent", "work", "routine_project_work",
                "Noah is setting the normal communication policy for a new project with no active incident. Choose the policy that best matches his applicable preferences.",
                "How does Noah prefer routine project communication when there is no incident?",
                [
                    _candidate("A", "Keep a video room open during working hours and call whenever a teammate needs a quick response.",
                               "live_video", "phone_calls", "synchronous"),
                    _candidate("C", "Use written project updates and comment threads, with teammates responding asynchronously when available.",
                               "written", "asynchronous", "review_later"),
                    _candidate("B", "Hold two scheduled video meetings each day and summarize decisions afterward in writing.",
                               "scheduled_video", "synchronous", "written_summary"),
                ],
            ),
            _truth(
                ["written", "asynchronous", "review_later"], "C",
                ["written", "asynchronous"],
                expired=["live_video", "phone_calls"],
                explanation="The live-call instruction applied to an outage, not routine project work.",
            ),
        ),
    ]


def _additional_composite_cases() -> list[dict]:
    flight_decision = _decision(
        "flight booking agent", "travel", "personal_flight",
        "The user is booking a personal flight to Lisbon for a five-day vacation. Choose the itinerary that best matches the user's current preferences.",
        "What does this user currently prefer for personal vacation flights?",
        [
            _candidate("A", "A nonstop morning flight with a standard carry-on allowance, arriving before dinner; it costs 18% more than the cheapest option.",
                       "nonstop", "daytime", "carry_on_included", "arrive_early", "higher_price"),
            _candidate("B", "The lowest-priced overnight itinerary with one connection and a six-hour layover; carry-on costs extra.",
                       "lowest_price", "overnight", "one_connection", "long_layover"),
            _candidate("C", "A nonstop overnight flight at a mid-range price with a carry-on included, arriving early in the morning.",
                       "nonstop", "overnight", "carry_on_included", "mid_price"),
        ],
    )
    meeting_decision = _decision(
        "team meeting agent", "work", "team_planning",
        "The user is planning a ninety-minute internal kickoff for a new cross-functional project. Choose the format that best matches the user's current preferences.",
        "What format does this user currently prefer for an internal project kickoff?",
        [
            _candidate("A", "A facilitated workshop with small-group exercises, a shared whiteboard, and time for every function to shape the plan.",
                       "interactive", "workshop", "shared_input", "collaborative"),
            _candidate("B", "A concise decision meeting built around a pre-read, three unresolved questions, and a written owner and next step for each decision.",
                       "concise", "pre_read", "decision_focused", "clear_owners", "next_steps"),
            _candidate("C", "A polished formal presentation followed by a short moderated question period, with discussion led by senior sponsors.",
                       "formal", "presentation", "senior_led", "limited_discussion"),
        ],
    )
    meal_decision = _decision(
        "meal planning agent", "food", "weekday_meals",
        "The user is selecting a weekday meal-plan service for regular personal use. Choose the plan that best matches the user's current preferences.",
        "What does this user currently prefer for regular weekday meals?",
        [
            _candidate("A", "A high-protein plan with chicken, fish, and eggs; every meal reheats in under five minutes, but the menu repeats often.",
                       "high_protein", "animal_protein", "under_five_minutes", "repetitive"),
            _candidate("B", "A plant-based plan with beans, grains, and seasonal vegetables, offering twelve rotating recipes that take about twenty minutes to prepare.",
                       "plant_based", "varied_menu", "seasonal", "twenty_minutes"),
            _candidate("C", "A broadly familiar catering plan with clearly labeled allergens and no nuts, but limited protein and only four menu choices.",
                       "nut_free", "allergen_labels", "familiar", "limited_variety"),
        ],
    )
    notification_decision = _decision(
        "notification setup agent", "work", "work_notifications",
        "The user is configuring notifications for daily work in a new team workspace. Choose the policy that best matches the user's current preferences.",
        "How does this user currently want daily work notifications handled?",
        [
            _candidate("A", "Put all project updates, including blockers, into one end-of-day digest.",
                       "all_digest", "routine_digest", "urgent_delayed"),
            _candidate("B", "Send every message, status change, and blocker immediately as a separate notification.",
                       "all_realtime", "urgent_immediate", "routine_realtime", "many_interruptions"),
            _candidate("C", "Send blockers immediately and combine routine status changes into one scheduled daily digest.",
                       "urgent_immediate", "routine_digest", "scheduled_digest", "fewer_interruptions"),
        ],
    )
    course_decision = _decision(
        "learning agent", "education", "professional_learning",
        "The user is choosing a twelve-week course to build a durable new professional skill. Choose the course format that best matches the user's current learning preferences.",
        "How does this user currently prefer to learn a durable professional skill?",
        [
            _candidate("A", "A project-based course in which each module adds to a working portfolio project, with weekly instructor feedback.",
                       "hands_on", "project_based", "portfolio", "feedback"),
            _candidate("B", "A structured course that teaches principles in sequence through lectures, readings, and cumulative concept exercises.",
                       "structured_theory", "sequential", "conceptual_foundation", "cumulative"),
            _candidate("C", "An intensive exam bootcamp focused on timed drills, test-taking shortcuts, and a final practice exam.",
                       "exam_focused", "timed_drills", "shortcuts", "practice_exam"),
        ],
    )
    furniture_decision = _decision(
        "furniture shopping agent", "shopping", "home_furniture",
        "The user is buying a dining table for their current home. Choose the option that best matches the user's current preferences.",
        "What does this user currently prioritize when buying long-term home furniture?",
        [
            _candidate("A", "A repairable solid-wood table made from certified timber by a local workshop, with a ten-year warranty and six-week lead time.",
                       "durable", "repairable", "certified_materials", "local_maker", "long_warranty"),
            _candidate("B", "The lowest-priced flat-pack table, available for delivery tomorrow, with a two-year expected lifespan.",
                       "lowest_price", "fast_delivery", "flat_pack", "short_lifespan"),
            _candidate("C", "A compact folding table on wheels that is easy to move and store, but uses lightweight composite material.",
                       "compact", "folding", "portable", "lightweight"),
        ],
    )

    pairs = [
        (
            "PREF-C-FLIGHT-001", "counterfactual_flight", "Omar", flight_decision,
            [
                ("A", [
                    _write(1, "travel_agent", "travel planning agent", "personal_flight", "stable",
                           "For vacation flights, I strongly prefer nonstop routes because connections make the trip tiring."),
                    _write(2, "schedule_agent", "schedule planning agent", "personal_flight", "stable",
                           "I prefer daytime flights that arrive with enough time to settle in before the evening."),
                ], ["nonstop", "daytime", "arrive_early"], ["nonstop", "daytime"]),
                ("B", [
                    _write(1, "travel_agent", "travel planning agent", "personal_flight", "stable",
                           "For personal trips, keeping the fare as low as possible matters more to me than avoiding a connection."),
                    _write(2, "schedule_agent", "schedule planning agent", "personal_flight", "stable",
                           "I am comfortable flying overnight and taking a long layover if that meaningfully lowers the price."),
                ], ["lowest_price", "overnight", "one_connection", "long_layover"], ["lowest_price", "overnight"]),
            ],
            _write(3, "family_agent", "family travel agent", "family_trip_last_year", "temporary",
                   "For a family trip last year, we needed two checked bags, and one relative who was recovering from surgery needed airport wheelchair assistance."),
            ["checked_bags", "wheelchair_assistance"],
        ),
        (
            "PREF-C-MEETING-001", "counterfactual_meeting", "Priya", meeting_decision,
            [
                ("A", [
                    _write(1, "facilitation_agent", "facilitation agent", "team_planning", "stable",
                           "For project kickoffs, I want people working together rather than listening to a long presentation."),
                    _write(2, "team_agent", "team collaboration agent", "team_planning", "stable",
                           "Give every function a real chance to shape the plan through small-group discussion and a shared workspace."),
                ], ["interactive", "workshop", "shared_input", "collaborative"], ["workshop", "shared_input"]),
                ("B", [
                    _write(1, "facilitation_agent", "facilitation agent", "team_planning", "stable",
                           "For internal project meetings, I prefer a short pre-read and a discussion focused only on unresolved decisions."),
                    _write(2, "team_agent", "team collaboration agent", "team_planning", "stable",
                           "Each decision should end with a named owner and a clear next step; open-ended workshops frustrate me."),
                ], ["concise", "pre_read", "decision_focused", "clear_owners", "next_steps"], ["decision_focused", "clear_owners"]),
            ],
            _write(3, "investor_agent", "investor presentation agent", "investor_update_last_quarter", "temporary",
                   "For last quarter's investor update, we needed a polished formal deck with questions moderated by the CEO."),
            ["formal", "presentation", "senior_led"],
        ),
        (
            "PREF-C-MEAL-001", "counterfactual_meal", "Quinn", meal_decision,
            [
                ("A", [
                    _write(1, "nutrition_agent", "nutrition agent", "weekday_meals", "stable",
                           "For weekday meals, I prioritize a high-protein plan that includes fish, chicken, or eggs."),
                    _write(2, "routine_agent", "routine planning agent", "weekday_meals", "stable",
                           "I need meals I can reheat in under five minutes between meetings, even if the menu repeats."),
                ], ["high_protein", "animal_protein", "under_five_minutes"], ["high_protein", "under_five_minutes"]),
                ("B", [
                    _write(1, "nutrition_agent", "nutrition agent", "weekday_meals", "stable",
                           "For my regular meals, I prefer plant-based dishes built around beans, grains, and vegetables."),
                    _write(2, "routine_agent", "routine planning agent", "weekday_meals", "stable",
                           "Menu variety matters to me, and I am happy to spend around twenty minutes preparing dinner."),
                ], ["plant_based", "varied_menu", "twenty_minutes"], ["plant_based", "varied_menu"]),
            ],
            _write(3, "event_agent", "event catering agent", "office_event_last_month", "temporary",
                   "For last month's office event, every meal had to be nut-free and carry full allergen labels."),
            ["nut_free", "allergen_labels"],
        ),
        (
            "PREF-C-NOTIFY-001", "counterfactual_notification", "Rina", notification_decision,
            [
                ("C", [
                    _write(1, "workspace_agent", "workspace agent", "work_notifications", "stable",
                           "I used to keep all workspace notifications on in real time."),
                    _write(2, "focus_agent", "focus planning agent", "work_notifications", "update",
                           "The interruptions are hurting my focus. From now on, send blockers immediately but collect routine changes into one daily digest."),
                ], ["urgent_immediate", "routine_digest", "scheduled_digest"], ["urgent_immediate", "routine_digest"]),
                ("B", [
                    _write(1, "workspace_agent", "workspace agent", "work_notifications", "stable",
                           "I used to prefer a daily digest for routine workspace updates."),
                    _write(2, "focus_agent", "focus planning agent", "work_notifications", "update",
                           "My role now requires continuous coordination. I want every project message, status change, and blocker delivered immediately instead of waiting for a digest."),
                ], ["all_realtime", "urgent_immediate", "routine_realtime"], ["all_realtime", "routine_realtime"]),
            ],
            _write(3, "leave_agent", "leave coverage agent", "vacation_last_month", "temporary",
                   "While I was on vacation last month, hold all noncritical notifications until I returned."),
            ["noncritical_delayed"],
        ),
        (
            "PREF-C-COURSE-001", "counterfactual_course", "Sam", course_decision,
            [
                ("A", [
                    _write(1, "learning_agent", "learning preference agent", "professional_learning", "stable",
                           "I learn professional skills best by building something real rather than only listening to lectures."),
                    _write(2, "career_agent", "career development agent", "professional_learning", "stable",
                           "I want each module to contribute to a portfolio project and include feedback I can apply the next week."),
                ], ["hands_on", "project_based", "portfolio", "feedback"], ["project_based", "portfolio"]),
                ("B", [
                    _write(1, "learning_agent", "learning preference agent", "professional_learning", "stable",
                           "I learn durable professional skills best when the underlying principles are taught in a clear sequence."),
                    _write(2, "career_agent", "career development agent", "professional_learning", "stable",
                           "I prefer structured readings and cumulative concept exercises before applying a method in practice."),
                ], ["structured_theory", "sequential", "conceptual_foundation", "cumulative"], ["structured_theory", "conceptual_foundation"]),
            ],
            _write(3, "certification_agent", "certification agent", "certification_exam_last_spring", "temporary",
                   "For a certification exam last spring, I needed timed drills and test-taking shortcuts for two weeks."),
            ["exam_focused", "timed_drills", "shortcuts"],
        ),
        (
            "PREF-C-FURNITURE-001", "counterfactual_furniture", "Tara", furniture_decision,
            [
                ("A", [
                    _write(1, "home_agent", "home planning agent", "home_furniture", "stable",
                           "For furniture I will keep for years, I prefer durable pieces that can be repaired instead of replaced."),
                    _write(2, "shopping_agent", "shopping agent", "home_furniture", "stable",
                           "Certified materials and a local maker matter more to me than getting the item immediately."),
                ], ["durable", "repairable", "certified_materials", "local_maker", "long_warranty"], ["durable", "certified_materials"]),
                ("B", [
                    _write(1, "home_agent", "home planning agent", "home_furniture", "stable",
                           "For household furniture, my current priority is the lowest possible upfront price."),
                    _write(2, "shopping_agent", "shopping agent", "home_furniture", "stable",
                           "I need delivery within the next two days and accept that I may replace the item after a couple of years."),
                ], ["lowest_price", "fast_delivery", "short_lifespan"], ["lowest_price", "fast_delivery"]),
            ],
            _write(3, "rental_agent", "temporary rental agent", "furnished_rental_last_year", "temporary",
                   "For a furnished rental last year, the table had to fold flat and be easy to move between rooms."),
            ["compact", "folding", "portable"],
        ),
    ]

    cases: list[dict] = []
    for pair_id, scenario, persona, decision, variants, temporary, expired in pairs:
        for suffix, (expected, stable_writes, active, required) in zip(("A", "B"), variants):
            capabilities = [
                "cross_agent_merge", "scope_resolution",
                "temporary_constraint_filtering", "counterfactual",
            ]
            if pair_id == "PREF-C-NOTIFY-001":
                capabilities.extend(["preference_update", "stale_preference_rejection"])
            cases.append(_case(
                f"{pair_id}-{suffix}", "composite", "composite_journey",
                capabilities,
                scenario, persona, stable_writes + [copy.deepcopy(temporary)], copy.deepcopy(decision),
                _truth(
                    active, expected, required, expired=expired,
                    explanation=(
                        f"The stable preferences in variant {suffix} select {expected}; "
                        "the held-constant historical requirement is task-local."
                    ),
                ),
                pair_id=pair_id,
            ))
    return cases


def pilot_cases() -> list[dict]:
    """Return a validated fresh copy of the thirty curated pilot cases."""
    cases = smoke_cases() + _additional_diagnostic_cases() + _additional_composite_cases()
    validate_cases(cases)
    layers = Counter(case["layer"] for case in cases)
    capabilities = Counter(
        case["primary_capability"]
        for case in cases
        if case["layer"] == "diagnostic"
    )
    if len(cases) != 30:
        raise ValueError(f"pilot must contain 30 cases, got {len(cases)}")
    if layers != {"diagnostic": 12, "composite": 18}:
        raise ValueError(f"unexpected layer distribution: {dict(layers)}")
    expected_capabilities = {
        "cross_agent_merge": 4,
        "preference_update": 4,
        "preference_boundary": 4,
    }
    if capabilities != expected_capabilities:
        raise ValueError(f"unexpected diagnostic distribution: {dict(capabilities)}")
    return copy.deepcopy(cases)


def generate_pilot(out_path: Path) -> None:
    cases = pilot_cases()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(cases, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def generate_review(out_path: Path) -> None:
    """Render the pilot into a product-readable Markdown review artifact."""
    cases = pilot_cases()
    lines = [
        "# Preference Track：30 个英文 Pilot Case 审查稿",
        "",
        "> 状态：已冻结，可用于三套 memory 系统的单次 pilot。后续若修改题目，必须作为新版本重新运行，不得回填本轮成绩。",
        "> 自动结构校验、唯一答案校验、选项平衡校验和反事实成对校验均已通过。模型辅助检查曾用于发现题目设计问题，但不作为无限迭代到满分的目标。",
        "",
        "## 审查重点",
        "",
        "1. 用户表达是否像真实场景中的直接说法；",
        "2. 结合偏好后，正确选项是否唯一且合理；",
        "3. 过去的一次性要求是否被清楚限定，不能误当成当前长期偏好；",
        "4. 合并题是否必须同时使用多个 Agent 的信息；",
        "5. 不提供偏好历史时，候选之间是否仍存在真实取舍。",
        "",
        "## 数据分布",
        "",
        "- 总计：30 个 case；",
        "- 单项：12 个——跨 Agent 合并、偏好更新、偏好边界各 4 个；",
        "- 综合：18 个——9 组 A/B 反事实对；",
        "- 正确选项：A、B、C 各 10 个；",
        "- 所有 benchmark 外部输入：英文。",
        "",
    ]
    for case in cases:
        truth = case["ground_truth"]
        lines.extend([
            f"## {case['case_id']}",
            "",
            f"- 类型：`{case['layer']}` / `{case['primary_capability']}`",
            f"- 场景：`{case['scenario']}`",
            f"- 正确选项：**{truth['expected_choice']}**",
            "",
            "用户历史：",
            "",
        ])
        lines.extend(
            f"{write['order']}. `{write['agent_id']}`：{write['utterance']}"
            for write in case["writes"]
        )
        lines.extend(["", f"当前任务：{case['decision']['task']}", "", "候选：", ""])
        lines.extend(
            f"- {candidate['id']}：{candidate['description']}"
            for candidate in case["decision"]["candidates"]
        )
        lines.extend([
            "",
            f"判断理由：{truth['explanation']}",
            "",
            f"当前有效偏好：`{', '.join(truth['active_preferences'])}`",
        ])
        ignored = truth["forbidden_reason_codes"]
        lines.append(
            f"不应采用的历史偏好/临时要求：`{', '.join(ignored)}`"
            if ignored else
            "不应采用的历史偏好/临时要求：无。"
        )
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
