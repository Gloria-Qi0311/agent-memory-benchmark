# Preference Track v0：英文 Smoke Case 审阅稿

## 当前状态

Preference Track 的 12 个 smoke case 已统一改为英文。三个系统将收到完全相同的英文输入：

- 用户偏好原话；
- 偏好更新与一次性要求；
- memory query；
- 当前任务；
- 三个候选；
- Agent D 的决策 prompt。

之前的中文单次运行因 mem0 的英文 memory 与中文 query 存在 embedding 语言错配，已经标记为不可横向比较。英文版需要三个系统全部重新运行。

当时机器可执行的完整内容位于 `data/cases/preference_smoke_n12.json`；该 smoke
数据集后来被 30-case pilot 取代，不再作为正式数据保留。

## 12 个 case

| Case | 能力 | 场景 | Ground truth |
|---|---|---|---|
| `PREF-D-MERGE-001` | 跨 Agent 合并 | Leisure hotel | B |
| `PREF-D-MERGE-002` | 跨 Agent 合并 | Product analysis style | B |
| `PREF-D-UPDATE-001` | 偏好更新 | Work router | B |
| `PREF-D-UPDATE-002` | 偏好更新 | Team workflow platform | A |
| `PREF-D-BOUNDARY-001` | 偏好边界 | Leisure vs business hotel | B |
| `PREF-D-BOUNDARY-002` | 偏好边界 | Friend invitation vs board report | C |
| `PREF-C-HOTEL-001-A` | 综合双胞胎 | Kyoto hotel, variant A | C |
| `PREF-C-HOTEL-001-B` | 综合双胞胎 | Kyoto hotel, variant B | A |
| `PREF-C-ANALYSIS-001-A` | 综合双胞胎 | Vendor analysis, variant A | A |
| `PREF-C-ANALYSIS-001-B` | 综合双胞胎 | Vendor analysis, variant B | C |
| `PREF-C-SOFTWARE-001-A` | 综合双胞胎 | Team software, variant A | C |
| `PREF-C-SOFTWARE-001-B` | 综合双胞胎 | Team software, variant B | A |

正确答案位置保持 A、B、C 各 4 个。

## 两道合并题为什么必须合并两条偏好

### `PREF-D-MERGE-001`

Writer 1：

> When I travel for leisure, I prefer quiet hotels and try to avoid crowded, noisy places.

Writer 2：

> I prefer small hotels with local character over standardized international chains.

候选设计：

- A 满足 quiet，但不满足 small/local；
- B 同时满足 quiet 与 small/local；
- C 满足 small/local，但不满足 quiet。

因此完整证据选择 B。模型消融中：无历史 3/3 回答 `UNKNOWN`；只给 writer 1 时答案不稳定；只给 writer 2 时稳定选择 C；两条都给时 3/3 选择 B。

### `PREF-D-MERGE-002`

Writer 1：

> When comparing options, I want to see the complete evidence and main risks before the recommendation.

Writer 2：

> Please do not give me only summary bullets. Show the reasoning step by step so I can verify it myself.

候选设计：

- A 强于完整 evidence/risk，但缺少逐步推导；
- B 同时包含完整 evidence/risk 与逐步推导，但阅读成本最高；
- C 强于逐步推导和复核，但只有高层证据摘要。

完整证据下 B 是唯一 Ground truth。消融中，无历史 3/3 回答 `UNKNOWN`；任意单条证据都不能 3/3 稳定命中 B；两条都给时 2/3 选择 B、1/3 弃权。该题可用于 smoke，但正式扩题时应继续避免“组合项天然显得最全面”的描述偏差。

## 更新题

### `PREF-D-UPDATE-001`

旧偏好是价格优先；新偏好明确改为工作设备可靠性优先。三个候选分别在低价、长期可靠性、高性能功能上占优，Ground truth 为 B。

### `PREF-D-UPDATE-002`

旧偏好是成熟稳定；新偏好明确改为最新自动化、快速迭代和厂商迁移支持优先。Ground truth 为 A。这是一道合理但不符合 reader 默认谨慎倾向的题，用于识别空 memory 下的常识猜测。

## 边界题

### `PREF-D-BOUNDARY-001`

稳定偏好是私人度假选择安静、慢节奏的小酒店；上个月上海商务出差的连锁酒店与交通枢纽要求是一次性的。当前新私人度假应选择 B。

### `PREF-D-BOUNDARY-002`

稳定偏好是朋友活动邀请使用简洁、中性、清楚的 RSVP 信息；上周董事会报告的正式、无 emoji、300 词限制是一次性的。当前生日邀请应选择 C。

## 三组综合双胞胎

每组双胞胎保持：

- 同一个 persona；
- 同一个当前任务；
- 同一组候选及排列；
- 同一条一次性要求；
- 只改变目标稳定偏好或更新方向；
- Ground truth 随偏好翻转。

Hotel pair 的答案为 C/A；Analysis pair 为 A/C；Software pair 为 C/A。只有两边都答对才算反事实成对成功。

## 已完成的质量检查

- 12 个 case 全部声明 `language: en`；
- 自动校验所有用户可见输入不包含中文字符；
- writer utterance 是自然第一人称原话，不含数据集转述包装；
- 每题 Ground truth 是结构化属性匹配的唯一最高分；
- A/B/C 各 4 个正确答案；
- 三组双胞胎保持相同 persona、临时事件和 decision surface；
- 两道合并题自动验证任一 writer 的结构化 evidence group 不能单独唯一决定答案；
- 英文无历史检查中，允许弃权时所有已完成题面均选择 `UNKNOWN`；
- 合并题完成 no-history / writer-1-only / writer-2-only / all-writers 消融。

无历史强制三选一分数不要求压到随机值。数据集保留真实常见偏好，同时加入少量非默认但合理的偏好，避免为了低基线制造反常识用户。

## 冻结与重跑规则

英文 case 在最终 API 质检完成后冻结。冻结后不能因为某个系统分数低而改题；只有发现 Ground truth 错误、题意歧义、runner bug、存储污染或配置不公平，才允许宣布整轮作废并重新测试。

正式英文 smoke 将重新运行：

```text
12 cases × 3 systems × 1 run
```

中文结果仅作排错记录，不进入英文结果表。
