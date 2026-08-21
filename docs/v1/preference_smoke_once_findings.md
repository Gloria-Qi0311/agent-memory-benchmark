# Preference Track：已作废的中文单次 Smoke 结果

> **状态：不可用于横向比较。** 本轮中文 case 中，mem0 将偏好抽取为英文，而配置的 embedding 不能可靠完成中文 query 与英文 memory 的跨语言检索。该结果仅保留为工程排错记录，后续正式比较统一使用英文 case 并全部重跑。

## 结论

本轮完成 `12 cases × 3 systems × 1 run`。这是一轮工程和区分度 smoke，不是最终排名。

| 系统 | 最终选择 | 单项 | 综合 | 反事实成对成功 | 空 context | 平均 context 字符 |
|---|---:|---:|---:|---:|---:|---:|
| `naive_markdown` | 12/12 | 6/6 | 6/6 | 3/3 | 0/12 | 125.4 |
| `AMH` | 12/12 | 6/6 | 6/6 | 3/3 | 0/12 | 50.6 |
| `mem0` | 8/12 | 4/6 | 4/6 | 1/3 | 7/12 | 119.9 |

完整原始结果：

- [`data/results/preference-smoke-once-naive-amh.json`](../../data/results/preference-smoke-once-naive-amh.json)
- [`data/results/preference-smoke-once-mem0.json`](../../data/results/preference-smoke-once-mem0.json)

## 如何理解结果

### `naive_markdown`

它把所有用户原话按时间顺序完整返回。DeepSeek 能够从原文中识别更新、作用域和一次性要求，因此 12/12。

这一结果说明在当前短历史中，保留完整原文是很强的基线；它不代表该方案在长历史下仍然高效，因为本轮每个 case 只有 2～3 条写入。

### `AMH`

它通过关键词检索返回较短 context，平均长度约为 naive 的 40%，仍然得到 12/12。

但部分“合并题”只检索到一条偏好也能答对。例如 `PREF-D-MERGE-001` 只返回“喜欢安静”，没有返回“喜欢当地特色的小酒店”，DeepSeek 仍选择 B。因此 100% 不能证明它已经完整合并多个 Agent 的偏好，只证明当前候选使一条关键偏好有时已经足够做出正确选择。

这是 case 区分度问题，扩展正式数据前需要把合并题改成：两个偏好碎片缺一不可，分别只看到任意一个碎片时都无法唯一确定正确答案。

### `mem0`

mem0 大多数写入抽取是成功的，内部 snapshot 中能看到结构化偏好；但它通常把中文原话总结为英文，而当前固定 query 是中文。配置使用的本地 embedding 模型对中英文跨语言检索支持不足，导致 7/12 个 case 返回空 context。

额外诊断确认：相同的两条英文 memory，用中文 query 检索为空，改用等义英文 query 能检索成功。因此本轮 mem0 的主要瓶颈是“抽取后语言改变 + 单语向量检索”，不是单纯没有保存偏好。

4 个错误分别是：

| Case | 表现 | 主要原因 |
|---|---|---|
| `PREF-D-UPDATE-002` | 应选 A，选 C | memory 已保存，但中文 query 检索为空；reader 回到默认成熟方案 |
| `PREF-D-BOUNDARY-001` | 应选 B，选 A | 检索只返回过去商务出差要求，漏掉当前私人度假偏好，属于作用域检索错误 |
| `PREF-C-ANALYSIS-001-A` | 应选 A，选 C | 一条写入未形成 memory，且最终检索为空；reader 使用默认证据优先判断 |
| `PREF-C-SOFTWARE-001-B` | 应选 A，选 C | 新预算偏好已保存，但中文 query 检索为空；reader 回到默认稳定方案 |

另外有 3 个空 context case 依靠 DeepSeek 默认判断答对，所以 mem0 的 8/12 仍高估了有效记忆检索能力。

## 本轮验证出的流程价值

这次结果证明四项修正是必要的：

1. 只把最终 choice 作为核心评分，避免内部偏好代码造成误判；
2. 同时保留常见偏好和非默认但合理的偏好，暴露“空 context 也能蒙对”；
3. 保存 memory snapshot、retrieved context 和最终回答，才能区分写入、检索和应用失败；
4. 本轮只运行一次，因此只能用于发现工程与设计问题，不能作为稳定的系统排名。

## 下一步建议

不要立即扩展到 60 个 case，也不要立即跑三次。先处理两个 smoke 发现：

1. 明确中文 benchmark 下 mem0 的公平配置：采用真正支持中英文跨语言检索的同一 embedding 模型，或约束 mem0 保持中文记忆；不应只为 mem0 把 query 翻成英文，因为那会改变三个系统的外部输入。
2. 强化合并题区分度：正确候选必须同时满足两个 Agent 的偏好；两个干扰项分别只满足其中一个，确保只检索到单条偏好不能稳定答对。

修正后重新冻结 12 个 smoke case，再决定是否执行三次稳定性 smoke。只有链路公平、case 确实能测到目标能力后，才扩展 60 个 pilot case。
