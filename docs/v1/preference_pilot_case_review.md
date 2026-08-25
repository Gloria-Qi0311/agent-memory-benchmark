# Preference Track：30 个英文 Pilot Case 审查稿

> 状态：已冻结，可用于三套 memory 系统的单次 pilot。后续若修改题目，必须作为新版本重新运行，不得回填本轮成绩。
> 自动结构校验、唯一答案校验、选项平衡校验和反事实成对校验均已通过。模型辅助检查曾用于发现题目设计问题，但不作为无限迭代到满分的目标。

## 审查重点

1. 用户表达是否像真实场景中的直接说法；
2. 结合偏好后，正确选项是否唯一且合理；
3. 过去的一次性要求是否被清楚限定，不能误当成当前长期偏好；
4. 合并题是否必须同时使用多个 Agent 的信息；
5. 不提供偏好历史时，候选之间是否仍存在真实取舍。

## 数据分布

- 总计：30 个 case；
- 单项：12 个——跨 Agent 合并、偏好更新、偏好边界各 4 个；
- 综合：18 个——9 组 A/B 反事实对；
- 正确选项：A、B、C 各 10 个；
- 所有 benchmark 外部输入：英文。

## PREF-D-MERGE-001

- 类型：`diagnostic` / `cross_agent_merge`
- 场景：`leisure_hotel`
- 正确选项：**B**

用户历史：

1. `travel_agent`：When I travel for leisure, I prefer quiet hotels and try to avoid crowded, noisy places.
2. `hotel_agent`：I prefer small hotels with local character over standardized international chains.

当前任务：Hana is planning a five-day leisure trip to a large city. Choose the hotel that best matches her preferences.

候选：

- A：A quiet international chain in the city center, with full facilities and convenient transport, but standardized design and little local character.
- B：A quiet, locally owned boutique hotel with few rooms and distinctive neighborhood character, but limited facilities and a location far from the city center.
- C：A small, locally owned design hotel in the city center, with a popular restaurant, concierge service, and easy transport; its rooms overlook a lively pedestrian street and have average soundproofing.

判断理由：B simultaneously satisfies the two preference fragments learned by different agents.

当前有效偏好：`quiet, small_hotel, boutique, local_character`
不应采用的历史偏好/临时要求：无。

## PREF-D-MERGE-002

- 类型：`diagnostic` / `cross_agent_merge`
- 场景：`developer_laptop`
- 正确选项：**B**

用户历史：

1. `travel_setup_agent`：I carry my work laptop between home and the office every day, so I want it to weigh no more than 1.3 kilograms.
2. `development_agent`：I run several local containers at once, so I need at least 32 GB of memory and good sustained cooling.

当前任务：Alex is choosing a laptop for daily software-development work and commuting. Choose the model that best matches his preferences.

候选：

- A：An ultraportable 1.05 kg laptop with 16 GB of memory and quiet low-power cooling.
- B：A 1.28 kg laptop with 32 GB of memory and a dual-fan cooling system suitable for sustained local workloads.
- C：A 1.75 kg mobile workstation with 64 GB of memory and the strongest sustained cooling of the three models.

判断理由：B is the only model that stays within the commuting weight limit while meeting the local-development memory and cooling needs.

当前有效偏好：`under_1_3kg, at_least_32gb, sustained_cooling`
不应采用的历史偏好/临时要求：无。

## PREF-D-UPDATE-001

- 类型：`diagnostic` / `preference_update`
- 场景：`work_device_purchase`
- 正确选项：**B**

用户历史：

1. `shopping_agent`：I used to prioritize price when buying equipment for work. As long as it did the job, that was good enough for me.
2. `work_agent`：Recent equipment failures have disrupted my work. From now on, reliability comes first; I am willing to pay more and no longer put price first.

当前任务：Bao needs a new router for work. Choose the option that best matches his current preferences.

候选：

- A：A mature entry-level model that costs 30% less, covers everyday needs, and includes a standard two-year warranty.
- B：A model that costs 30% more, has the strongest long-term reliability record, and includes a five-year warranty with on-site replacement.
- C：A mid-priced model with the best throughput and management features and a three-year warranty, but only six months of market history.

判断理由：The later explicit update supersedes price-first purchasing in this scope.

当前有效偏好：`reliability_first, proven_stability, long_warranty`
不应采用的历史偏好/临时要求：`low_price, price_first`

## PREF-D-UPDATE-002

- 类型：`diagnostic` / `preference_update`
- 场景：`software_adoption`
- 正确选项：**A**

用户历史：

1. `tool_scout_agent`：I used to prefer mature team tools with predictable releases and long-term support.
2. `engineering_agent`：Several new automation features have recently improved our efficiency. I now prioritize the latest features and rapid iteration, as long as the vendor provides migration support; maturity is no longer my top concern.

当前任务：Chloe needs to choose a new workflow platform for her team. Choose the option that best matches her current preferences.

候选：

- A：A newly launched platform with the most advanced automation, monthly feature releases, and vendor migration support, but a short track record.
- B：A mature all-in-one platform with the broadest feature and plugin set, but complex configuration that requires a certified service partner.
- C：A core-workflow platform with years of validation, predictable releases, clear documentation, and long-term support, but fewer advanced features.

判断理由：A reflects the new innovation-first preference rather than the old maturity preference.

当前有效偏好：`newest_features, rapid_iteration, vendor_migration_support`
不应采用的历史偏好/临时要求：`mature, long_term_support, stable_release_cycle`

## PREF-D-BOUNDARY-001

- 类型：`diagnostic` / `preference_boundary`
- 场景：`leisure_vs_business_hotel`
- 正确选项：**B**

用户历史：

1. `leisure_agent`：For leisure trips, I like quiet, slow-paced small hotels and do not mind staying away from busy areas.
2. `business_agent`：For my one-day business trip to Shanghai last month, I needed a chain hotel near a transport hub so I could keep to the schedule.

当前任务：Diego is planning a new private island vacation. Choose the accommodation that best matches the preferences applicable to this trip.

候选：

- A：An international beachfront resort near the ferry terminal, with full facilities but busy common areas.
- B：A quiet small seaside guesthouse away from the commercial district, with few rooms and a relaxed pace but limited dining options.
- C：An independent design hotel in the island town center, within walking distance of restaurants and the night market, but lively in the evenings.

判断理由：The Shanghai business-trip constraint must not propagate into a new leisure trip.

当前有效偏好：`quiet, small_hotel, slow_paced, farther_from_center`
不应采用的历史偏好/临时要求：`transport_hub_proximity, large_chain`

## PREF-D-BOUNDARY-002

- 类型：`diagnostic` / `preference_boundary`
- 场景：`personal_invitation_style`
- 正确选项：**C**

用户历史：

1. `personal_writing_agent`：For event invitations to friends, I prefer a concise, neutral style. Clear time, location, and RSVP details are enough; I do not need much emotional language.
2. `board_report_agent`：For last week's board report, please use a formal tone, avoid emojis, and keep it under 300 words.

当前任务：Eun needs to write a birthday party invitation to friends. Choose the writing style that best matches her applicable preferences.

候选：

- A：A formally worded invitation that fully explains the arrangements and response process, uses no emojis, and stays under 300 words.
- B：A warm, casual invitation with a personal greeting and a little playful language, while clearly stating the time and location.
- C：A concise, neutral invitation template focused on the time, location, and RSVP, making it easy to confirm quickly.

判断理由：The board-report constraints were task-local and should not affect a personal invitation.

当前有效偏好：`neutral, concise, rsvp_focused, clear_details`
不应采用的历史偏好/临时要求：`formal_tone, no_emoji, max_300_words`

## PREF-C-HOTEL-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_hotel`
- 正确选项：**C**

用户历史：

1. `leisure_agent`：On private vacations, quiet matters most to me, and I dislike crowded, noisy hotels.
2. `hotel_agent`：I prefer small accommodations with local character; large international chains do not appeal to me.
3. `family_trip_agent`：For a week-long family stay last month, the room had to include a kitchen and a washer.

当前任务：The user is taking a five-day private vacation in Kyoto. Choose the hotel that best matches the user's current preferences.

候选：

- A：A large international chain in the city center, with convenient transport and consistent service, but many rooms and a busy atmosphere.
- C：A quiet local machiya boutique hotel with few rooms and distinctive character, but farther from the main sights.
- B：A modern serviced apartment near Kyoto Station, with a kitchen and washer for longer stays, but limited hotel service and local character.

判断理由：The prior family-trip facilities were task-local; the stable leisure preferences select C.

当前有效偏好：`quiet, boutique, local_character`
不应采用的历史偏好/临时要求：`kitchen, laundry`

## PREF-C-HOTEL-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_hotel`
- 正确选项：**A**

用户历史：

1. `leisure_agent`：For hotels on private vacations, convenient transport in the city center matters most to me.
2. `hotel_agent`：I trust large international chains with consistent service standards and full facilities.
3. `family_trip_agent`：For a week-long family stay last month, the room had to include a kitchen and a washer.

当前任务：The user is taking a five-day private vacation in Kyoto. Choose the hotel that best matches the user's current preferences.

候选：

- A：A large international chain in the city center, with convenient transport and consistent service, but many rooms and a busy atmosphere.
- C：A quiet local machiya boutique hotel with few rooms and distinctive character, but farther from the main sights.
- B：A modern serviced apartment near Kyoto Station, with a kitchen and washer for longer stays, but limited hotel service and local character.

判断理由：The same decision surface flips because this user's leisure preferences favor option A.

当前有效偏好：`city_center, large_chain, brand_consistency, full_service`
不应采用的历史偏好/临时要求：`kitchen, laundry`

## PREF-C-ANALYSIS-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_analysis_style`
- 正确选项：**A**

用户历史：

1. `strategy_agent`：When comparing proposals, give me the recommendation first; I do not want to read a long background section before it.
2. `writing_agent`：Do not open with the full derivation. Start with a few clear points on what to choose and what to do next.
3. `training_agent`：For last month's new-hire training, start with a real case to explain the situation and do not make the purchasing decision for them.

当前任务：A few weeks later, the user needs to compare two vendor proposals in an internal product-team review; this material is not for training. Choose the presentation format that best matches the user's current analysis preferences.

候选：

- A：Open with a recommendation, then use three concise bullets to summarize the key trade-offs and next action.
- C：Systematically present the full data, evidence sources, risk assumptions, and detailed reasoning before giving a conclusion.
- B：Start with a real implementation case, then add a one-page comparison table without recommending an option, leaving the review team to decide.

判断理由：The prior training format was task-local; the stable product-decision preference selects A.

当前有效偏好：`conclusion_first, concise, action_oriented, bullet_points`
不应采用的历史偏好/临时要求：`case_first, reader_decides`

## PREF-C-ANALYSIS-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_analysis_style`
- 正确选项：**C**

用户历史：

1. `strategy_agent`：For important proposal comparisons, I want the complete data and evidence sources, not just a simplified conclusion.
2. `writing_agent`：Write out the risk assumptions and reasoning clearly so I can verify the analysis myself.
3. `training_agent`：For last month's new-hire training, start with a real case to explain the situation and do not make the purchasing decision for them.

当前任务：A few weeks later, the user needs to compare two vendor proposals in an internal product-team review; this material is not for training. Choose the presentation format that best matches the user's current analysis preferences.

候选：

- A：Open with a recommendation, then use three concise bullets to summarize the key trade-offs and next action.
- C：Systematically present the full data, evidence sources, risk assumptions, and detailed reasoning before giving a conclusion.
- B：Start with a real implementation case, then add a one-page comparison table without recommending an option, leaving the review team to decide.

判断理由：The prior training format was task-local; the stable evidence-first preference selects C.

当前有效偏好：`detailed, evidence_rich, full_reasoning, risk_analysis`
不应采用的历史偏好/临时要求：`case_first, reader_decides`

## PREF-C-SOFTWARE-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_software_purchase`
- 正确选项：**C**

用户历史：

1. `procurement_agent`：I used to look at price first when choosing team software. If it worked, that was enough.
2. `team_operations_agent`：After repeated failures with low-cost tools, I now prioritize proven, stable options with long-term support for this team's daily software; price no longer comes first.
3. `demo_agent`：For a one-off innovation demo last month, it was fine to temporarily try the platform with the newest features.

当前任务：The user needs to choose a project management platform for a ten-person team to use daily over the next year. Choose the option that best matches the user's current preferences.

候选：

- A：The lowest-priced option, with simple core features and same-day rollout; it relies mainly on community support and has fewer integrations.
- C：A higher-priced option with years of validation, a strong reliability record, mature integrations, and long-term vendor support, but a two-week rollout.
- B：A new platform with the most automation features and free vendor migration assistance, but a short track record and frequent releases.

判断理由：The stable updated preference applies to this team's daily software; the demo exception is expired.

当前有效偏好：`proven_reliability, stable, long_term_support`
不应采用的历史偏好/临时要求：`newest_features, low_price`

## PREF-C-SOFTWARE-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_software_purchase`
- 正确选项：**A**

用户历史：

1. `procurement_agent`：I used to choose mature team software with comprehensive features and strong support.
2. `team_operations_agent`：This team's budget will be tight for the next year. For their daily software, I now prioritize price and fast rollout instead of paying for a full ecosystem they will not use.
3. `demo_agent`：For a one-off innovation demo last month, it was fine to temporarily try the platform with the newest features.

当前任务：The user needs to choose a project management platform for a ten-person team to use daily over the next year. Choose the option that best matches the user's current preferences.

候选：

- A：The lowest-priced option, with simple core features and same-day rollout; it relies mainly on community support and has fewer integrations.
- C：A higher-priced option with years of validation, a strong reliability record, mature integrations, and long-term vendor support, but a two-week rollout.
- B：A new platform with the most automation features and free vendor migration assistance, but a short track record and frequent releases.

判断理由：The explicit budget-first update selects A; the innovation-demo exception is expired.

当前有效偏好：`low_price, simple_setup, basic_functionality`
不应采用的历史偏好/临时要求：`newest_features, mature_ecosystem, long_term_support`

## PREF-D-MERGE-003

- 类型：`diagnostic` / `cross_agent_merge`
- 场景：`restaurant_choice`
- 正确选项：**C**

用户历史：

1. `food_agent`：When choosing a restaurant for myself, I want a menu with several genuinely plant-based main dishes, not just side salads.
2. `social_agent`：I prefer restaurants quiet enough for an unhurried conversation; loud, crowded dining rooms wear me out.

当前任务：Iris is meeting a close friend for dinner. Choose the restaurant that best matches her preferences.

候选：

- A：A lively plant-based food hall with eight vegan mains, communal tables, loud music, and an average dinner price of $30 per person.
- C：A small, quiet neighborhood restaurant with five plant-based mains, spaced tables, a relaxed two-hour seating, and an average dinner price of $55 per person.
- B：A small, quiet traditional grill with spaced tables, a relaxed two-hour seating, only one plant-based main, and an average dinner price of $30 per person.

判断理由：C is the only option that combines a real plant-based menu with a quiet setting.

当前有效偏好：`plant_based_mains, many_vegan_options, quiet, uncrowded`
不应采用的历史偏好/临时要求：无。

## PREF-D-MERGE-004

- 类型：`diagnostic` / `cross_agent_merge`
- 场景：`home_office_chair`
- 正确选项：**C**

用户历史：

1. `home_agent`：My desk nook is narrow. The chair must be no more than 60 centimeters wide, and within that limit I prefer the most compact option.
2. `ergonomics_agent`：I sit for long work sessions and want adjustable lumbar support; the more completely I can adjust its height and depth, the better.

当前任务：Jonah is buying a chair for his home office. Choose the chair that best matches his preferences.

候选：

- A：A compact 48 cm-wide task chair with a fixed mesh back and no adjustable lumbar support.
- C：A $550, 58 cm-wide compact ergonomic chair with adjustable lumbar height and depth, designed for long work sessions.
- B：A $320, 68 cm-wide executive ergonomic chair with the widest lumbar height-and-depth adjustment range and a larger padded back.

判断理由：C is the only chair narrow enough for the desk nook while also providing adjustable lumbar support for long sessions.

当前有效偏好：`under_60cm, adjustable_lumbar, lumbar_height_depth, long_session_support`
不应采用的历史偏好/临时要求：无。

## PREF-D-UPDATE-003

- 类型：`diagnostic` / `preference_update`
- 场景：`exercise_class`
- 正确选项：**C**

用户历史：

1. `fitness_agent`：I used to choose intense group workouts because the competition kept me motivated.
2. `routine_agent`：My routine has changed. I now stick with low-impact sessions I can do independently at a steady pace; group competition is no longer what I want.

当前任务：Kavya is choosing a recurring weekly exercise class. Choose the option that best matches her current preferences.

候选：

- A：A high-intensity team circuit with leaderboards, partner drills, and a fixed competitive pace.
- C：A low-impact studio session with individual stations, self-paced progress, and optional instructor guidance.
- B：A moderate dance class with a social group format, synchronized routines, and energetic music.

判断理由：The explicit routine change supersedes the former preference for competitive group exercise.

当前有效偏好：`low_impact, independent, steady_pace, self_paced`
不应采用的历史偏好/临时要求：`high_intensity, group_competition`

## PREF-D-UPDATE-004

- 类型：`diagnostic` / `preference_update`
- 场景：`grocery_fulfillment`
- 正确选项：**A**

用户历史：

1. `grocery_agent`：I used to choose the fastest grocery delivery window, even when it cost more.
2. `household_agent`：I work near the market now. For weekly groceries, I prefer a scheduled pickup with minimal packaging, and speed is no longer worth an extra delivery fee.

当前任务：Luis is placing his regular weekly grocery order. Choose the fulfillment option that best matches his current preferences.

候选：

- B：A ninety-minute home delivery with a priority fee and individually bagged categories.
- A：A scheduled pickup beside Luis's workplace, packed together in reusable crates with no delivery fee.
- C：A next-day home delivery with a small fee and standard disposable bags.

判断理由：The current pickup and packaging preference replaces the previous speed-first choice.

当前有效偏好：`scheduled_pickup, near_work, minimal_packaging, no_delivery_fee`
不应采用的历史偏好/临时要求：`fastest_delivery, priority_fee`

## PREF-D-BOUNDARY-003

- 类型：`diagnostic` / `preference_boundary`
- 场景：`personal_vs_client_dinner`
- 正确选项：**C**

用户历史：

1. `food_agent`：For my own dinners, I enjoy spicy regional food and like trying dishes I have not had before.
2. `client_agent`：For last month's client dinner, I needed a quiet private room and a mild, familiar menu because the guests had different tastes.

当前任务：Maya is choosing a restaurant for a casual dinner with a close friend. Choose the option that best matches Maya's applicable preferences.

候选：

- A：A quiet hotel dining room with a private booth and a familiar mild international menu.
- C：A casual regional restaurant known for spicy seasonal dishes and a rotating menu of less familiar specialties.
- B：A popular pizza restaurant with a familiar menu, lively atmosphere, and several shareable classics.

判断理由：The client-dinner requirements were guest-specific and do not replace Maya's personal dining preference.

当前有效偏好：`spicy, regional_food, novel_dishes`
不应采用的历史偏好/临时要求：`quiet, private_room, mild, familiar_menu`

## PREF-D-BOUNDARY-004

- 类型：`diagnostic` / `preference_boundary`
- 场景：`routine_project_communication`
- 正确选项：**C**

用户历史：

1. `collaboration_agent`：For routine project work, I prefer written asynchronous updates that I can review and respond to in my own time.
2. `incident_agent`：During last week's production outage, call me immediately and keep a live video room open until service is restored.

当前任务：Noah is setting the normal communication policy for a new project with no active incident. Choose the policy that best matches his applicable preferences.

候选：

- A：Keep a video room open during working hours and call whenever a teammate needs a quick response.
- C：Use written project updates and comment threads, with teammates responding asynchronously when available.
- B：Hold two scheduled video meetings each day and summarize decisions afterward in writing.

判断理由：The live-call instruction applied to an outage, not routine project work.

当前有效偏好：`written, asynchronous, review_later`
不应采用的历史偏好/临时要求：`live_video, phone_calls`

## PREF-C-FLIGHT-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_flight`
- 正确选项：**A**

用户历史：

1. `travel_agent`：For vacation flights, I strongly prefer nonstop routes because connections make the trip tiring.
2. `schedule_agent`：I prefer daytime flights that arrive with enough time to settle in before the evening.
3. `family_agent`：For a family trip last year, we needed two checked bags, and one relative who was recovering from surgery needed airport wheelchair assistance.

当前任务：The user is booking a personal flight to Lisbon for a five-day vacation. Choose the itinerary that best matches the user's current preferences.

候选：

- A：A nonstop morning flight with a standard carry-on allowance, arriving before dinner; it costs 18% more than the cheapest option.
- B：The lowest-priced overnight itinerary with one connection and a six-hour layover; carry-on costs extra.
- C：A nonstop overnight flight at a mid-range price with a carry-on included, arriving early in the morning.

判断理由：The stable preferences in variant A select A; the held-constant historical requirement is task-local.

当前有效偏好：`nonstop, daytime, arrive_early`
不应采用的历史偏好/临时要求：`checked_bags, wheelchair_assistance`

## PREF-C-FLIGHT-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_flight`
- 正确选项：**B**

用户历史：

1. `travel_agent`：For personal trips, keeping the fare as low as possible matters more to me than avoiding a connection.
2. `schedule_agent`：I am comfortable flying overnight and taking a long layover if that meaningfully lowers the price.
3. `family_agent`：For a family trip last year, we needed two checked bags, and one relative who was recovering from surgery needed airport wheelchair assistance.

当前任务：The user is booking a personal flight to Lisbon for a five-day vacation. Choose the itinerary that best matches the user's current preferences.

候选：

- A：A nonstop morning flight with a standard carry-on allowance, arriving before dinner; it costs 18% more than the cheapest option.
- B：The lowest-priced overnight itinerary with one connection and a six-hour layover; carry-on costs extra.
- C：A nonstop overnight flight at a mid-range price with a carry-on included, arriving early in the morning.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`lowest_price, overnight, one_connection, long_layover`
不应采用的历史偏好/临时要求：`checked_bags, wheelchair_assistance`

## PREF-C-MEETING-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_meeting`
- 正确选项：**A**

用户历史：

1. `facilitation_agent`：For project kickoffs, I want people working together rather than listening to a long presentation.
2. `team_agent`：Give every function a real chance to shape the plan through small-group discussion and a shared workspace.
3. `investor_agent`：For last quarter's investor update, we needed a polished formal deck with questions moderated by the CEO.

当前任务：The user is planning a ninety-minute internal kickoff for a new cross-functional project. Choose the format that best matches the user's current preferences.

候选：

- A：A facilitated workshop with small-group exercises, a shared whiteboard, and time for every function to shape the plan.
- B：A concise decision meeting built around a pre-read, three unresolved questions, and a written owner and next step for each decision.
- C：A polished formal presentation followed by a short moderated question period, with discussion led by senior sponsors.

判断理由：The stable preferences in variant A select A; the held-constant historical requirement is task-local.

当前有效偏好：`interactive, workshop, shared_input, collaborative`
不应采用的历史偏好/临时要求：`formal, presentation, senior_led`

## PREF-C-MEETING-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_meeting`
- 正确选项：**B**

用户历史：

1. `facilitation_agent`：For internal project meetings, I prefer a short pre-read and a discussion focused only on unresolved decisions.
2. `team_agent`：Each decision should end with a named owner and a clear next step; open-ended workshops frustrate me.
3. `investor_agent`：For last quarter's investor update, we needed a polished formal deck with questions moderated by the CEO.

当前任务：The user is planning a ninety-minute internal kickoff for a new cross-functional project. Choose the format that best matches the user's current preferences.

候选：

- A：A facilitated workshop with small-group exercises, a shared whiteboard, and time for every function to shape the plan.
- B：A concise decision meeting built around a pre-read, three unresolved questions, and a written owner and next step for each decision.
- C：A polished formal presentation followed by a short moderated question period, with discussion led by senior sponsors.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`concise, pre_read, decision_focused, clear_owners, next_steps`
不应采用的历史偏好/临时要求：`formal, presentation, senior_led`

## PREF-C-MEAL-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_meal`
- 正确选项：**A**

用户历史：

1. `nutrition_agent`：For weekday meals, I prioritize a high-protein plan that includes fish, chicken, or eggs.
2. `routine_agent`：I need meals I can reheat in under five minutes between meetings, even if the menu repeats.
3. `event_agent`：For last month's office event, every meal had to be nut-free and carry full allergen labels.

当前任务：The user is selecting a weekday meal-plan service for regular personal use. Choose the plan that best matches the user's current preferences.

候选：

- A：A high-protein plan with chicken, fish, and eggs; every meal reheats in under five minutes, but the menu repeats often.
- B：A plant-based plan with beans, grains, and seasonal vegetables, offering twelve rotating recipes that take about twenty minutes to prepare.
- C：A broadly familiar catering plan with clearly labeled allergens and no nuts, but limited protein and only four menu choices.

判断理由：The stable preferences in variant A select A; the held-constant historical requirement is task-local.

当前有效偏好：`high_protein, animal_protein, under_five_minutes`
不应采用的历史偏好/临时要求：`nut_free, allergen_labels`

## PREF-C-MEAL-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_meal`
- 正确选项：**B**

用户历史：

1. `nutrition_agent`：For my regular meals, I prefer plant-based dishes built around beans, grains, and vegetables.
2. `routine_agent`：Menu variety matters to me, and I am happy to spend around twenty minutes preparing dinner.
3. `event_agent`：For last month's office event, every meal had to be nut-free and carry full allergen labels.

当前任务：The user is selecting a weekday meal-plan service for regular personal use. Choose the plan that best matches the user's current preferences.

候选：

- A：A high-protein plan with chicken, fish, and eggs; every meal reheats in under five minutes, but the menu repeats often.
- B：A plant-based plan with beans, grains, and seasonal vegetables, offering twelve rotating recipes that take about twenty minutes to prepare.
- C：A broadly familiar catering plan with clearly labeled allergens and no nuts, but limited protein and only four menu choices.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`plant_based, varied_menu, twenty_minutes`
不应采用的历史偏好/临时要求：`nut_free, allergen_labels`

## PREF-C-NOTIFY-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_notification`
- 正确选项：**C**

用户历史：

1. `workspace_agent`：I used to keep all workspace notifications on in real time.
2. `focus_agent`：The interruptions are hurting my focus. From now on, send blockers immediately but collect routine changes into one daily digest.
3. `leave_agent`：While I was on vacation last month, hold all noncritical notifications until I returned.

当前任务：The user is configuring notifications for daily work in a new team workspace. Choose the policy that best matches the user's current preferences.

候选：

- A：Put all project updates, including blockers, into one end-of-day digest.
- B：Send every message, status change, and blocker immediately as a separate notification.
- C：Send blockers immediately and combine routine status changes into one scheduled daily digest.

判断理由：The stable preferences in variant A select C; the held-constant historical requirement is task-local.

当前有效偏好：`urgent_immediate, routine_digest, scheduled_digest`
不应采用的历史偏好/临时要求：`noncritical_delayed`

## PREF-C-NOTIFY-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_notification`
- 正确选项：**B**

用户历史：

1. `workspace_agent`：I used to prefer a daily digest for routine workspace updates.
2. `focus_agent`：My role now requires continuous coordination. I want every project message, status change, and blocker delivered immediately instead of waiting for a digest.
3. `leave_agent`：While I was on vacation last month, hold all noncritical notifications until I returned.

当前任务：The user is configuring notifications for daily work in a new team workspace. Choose the policy that best matches the user's current preferences.

候选：

- A：Put all project updates, including blockers, into one end-of-day digest.
- B：Send every message, status change, and blocker immediately as a separate notification.
- C：Send blockers immediately and combine routine status changes into one scheduled daily digest.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`all_realtime, urgent_immediate, routine_realtime`
不应采用的历史偏好/临时要求：`noncritical_delayed`

## PREF-C-COURSE-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_course`
- 正确选项：**A**

用户历史：

1. `learning_agent`：I learn professional skills best by building something real rather than only listening to lectures.
2. `career_agent`：I want each module to contribute to a portfolio project and include feedback I can apply the next week.
3. `certification_agent`：For a certification exam last spring, I needed timed drills and test-taking shortcuts for two weeks.

当前任务：The user is choosing a twelve-week course to build a durable new professional skill. Choose the course format that best matches the user's current learning preferences.

候选：

- A：A project-based course in which each module adds to a working portfolio project, with weekly instructor feedback.
- B：A structured course that teaches principles in sequence through lectures, readings, and cumulative concept exercises.
- C：An intensive exam bootcamp focused on timed drills, test-taking shortcuts, and a final practice exam.

判断理由：The stable preferences in variant A select A; the held-constant historical requirement is task-local.

当前有效偏好：`hands_on, project_based, portfolio, feedback`
不应采用的历史偏好/临时要求：`exam_focused, timed_drills, shortcuts`

## PREF-C-COURSE-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_course`
- 正确选项：**B**

用户历史：

1. `learning_agent`：I learn durable professional skills best when the underlying principles are taught in a clear sequence.
2. `career_agent`：I prefer structured readings and cumulative concept exercises before applying a method in practice.
3. `certification_agent`：For a certification exam last spring, I needed timed drills and test-taking shortcuts for two weeks.

当前任务：The user is choosing a twelve-week course to build a durable new professional skill. Choose the course format that best matches the user's current learning preferences.

候选：

- A：A project-based course in which each module adds to a working portfolio project, with weekly instructor feedback.
- B：A structured course that teaches principles in sequence through lectures, readings, and cumulative concept exercises.
- C：An intensive exam bootcamp focused on timed drills, test-taking shortcuts, and a final practice exam.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`structured_theory, sequential, conceptual_foundation, cumulative`
不应采用的历史偏好/临时要求：`exam_focused, timed_drills, shortcuts`

## PREF-C-FURNITURE-001-A

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_furniture`
- 正确选项：**A**

用户历史：

1. `home_agent`：For furniture I will keep for years, I prefer durable pieces that can be repaired instead of replaced.
2. `shopping_agent`：Certified materials and a local maker matter more to me than getting the item immediately.
3. `rental_agent`：For a furnished rental last year, the table had to fold flat and be easy to move between rooms.

当前任务：The user is buying a dining table for their current home. Choose the option that best matches the user's current preferences.

候选：

- A：A repairable solid-wood table made from certified timber by a local workshop, with a ten-year warranty and six-week lead time.
- B：The lowest-priced flat-pack table, available for delivery tomorrow, with a two-year expected lifespan.
- C：A compact folding table on wheels that is easy to move and store, but uses lightweight composite material.

判断理由：The stable preferences in variant A select A; the held-constant historical requirement is task-local.

当前有效偏好：`durable, repairable, certified_materials, local_maker, long_warranty`
不应采用的历史偏好/临时要求：`compact, folding, portable`

## PREF-C-FURNITURE-001-B

- 类型：`composite` / `composite_journey`
- 场景：`counterfactual_furniture`
- 正确选项：**B**

用户历史：

1. `home_agent`：For household furniture, my current priority is the lowest possible upfront price.
2. `shopping_agent`：I need delivery within the next two days and accept that I may replace the item after a couple of years.
3. `rental_agent`：For a furnished rental last year, the table had to fold flat and be easy to move between rooms.

当前任务：The user is buying a dining table for their current home. Choose the option that best matches the user's current preferences.

候选：

- A：A repairable solid-wood table made from certified timber by a local workshop, with a ten-year warranty and six-week lead time.
- B：The lowest-priced flat-pack table, available for delivery tomorrow, with a two-year expected lifespan.
- C：A compact folding table on wheels that is easy to move and store, but uses lightweight composite material.

判断理由：The stable preferences in variant B select B; the held-constant historical requirement is task-local.

当前有效偏好：`lowest_price, fast_delivery, short_lifespan`
不应采用的历史偏好/临时要求：`compact, folding, portable`

