# Preference Track：30 题英文 Pilot 单次结果

> 状态：冻结 case 后的有效单次 pilot。三个系统使用同一批英文输入、同一个 DeepSeek reader、相同决策 prompt；每个 case 独立存储。本轮每个系统只运行一次，不是统计显著的最终排名。

## 结果

| 系统 | 总准确率 | 单项题 | 综合题 | 反事实成对成功 | 空 context | 平均 context 字符 |
|---|---:|---:|---:|---:|---:|---:|
| `naive_markdown` | **30/30（100%）** | 12/12 | 18/18 | 9/9 | 0 | 324.8 |
| `mem0` | **30/30（100%）** | 12/12 | 18/18 | 9/9 | 0 | 275.7 |
| `AMH` | **28/30（93.3%）** | 11/12 | 17/18 | 8/9 | 1 | 239.4 |

原始结果：

- `data/results/preference-pilot-n30-once-naive-amh.json`
- `data/results/preference-pilot-n30-once-mem0.json`

## 产品结论

在短历史、显式英文偏好、单次运行的条件下，`naive_markdown` 与 `mem0` 都能把多个 Agent 写入的偏好正确用于最终选择。`mem0` 的 context 比完整原文基线短约 15%，本轮没有观察到因此产生的决策损失。`AMH` 的 context 最短，但两次漏掉决定性信息。

这个结果不能证明 naive 或 mem0 在真实长期记忆中总体更好。每个 case 仍只有 2～3 条写入，完整原文很容易放入 context；检索系统处理长历史和噪声的主要价值尚未被测试。

## AMH 的两个错误

1. `PREF-D-UPDATE-002`：用户已从“成熟稳定”更新为“最新功能和快速迭代”，但 AMH 只返回旧偏好：`I used to prefer mature team tools with predictable releases and long-term support.` reader 因此选择旧偏好对应的 C，而不是 A。
2. `PREF-C-ANALYSIS-001-B`：AMH 返回空 context。reader 没有用户偏好证据，只能采用默认的“结论优先”格式 A，而 ground truth 是完整证据与推理格式 C。

两次均可从检索 context 定位为检索遗漏，不是 reader 在拿到完整信息后理解错误。

## mem0 工程检查

- 30 个 case 全部完成，无 API/runtime 错误；
- 空 context：0；
- 写入管线警告：0；
- snapshot 数量没有超过本题写入数量；
- 每个 case 使用独立 Qdrant 与独立 `history.db`，没有发现跨 case 串数据；
- 反事实 9 组全部双题正确。

日志中的 spaCy 信息是 mem0 的可选词形功能未安装提示，本轮使用的向量检索与记忆抽取均正常，没有因此产生 case 错误。

## Case 质量与冻结规则

30 个 case 在写入阶段遵守统一规则：用户表达必须自然、正确答案必须唯一、临时要求必须显式限定、合并题单个 Agent 不能稳定决定完整目标、正确选项 A/B/C 各 10 个。程序结构与 ground-truth 校验共 39 项通过。

模型辅助检查曾发现任务描述泄露答案和“综合选项隐藏支配”等问题；明确问题已在正式跑分前修正。根据产品决策，质量检查用于发现明显问题，不再为了追求模型辅助指标满分而无限调题。case 冻结后没有根据三个 memory 系统的成绩修改题目。

## 下一步建议

不要立刻把同类短历史题扩到几百道。下一轮新增约 20～30 个长历史 case，在同一个 case 内放入 20～100 条经过控制的历史，其中包含相关偏好、无关噪声、旧偏好、新偏好和一次性要求。这样才能测试：

- naive 全量 context 是否被噪声和长度拖累；
- mem0 的抽取与检索压缩是否开始体现价值或造成信息损失；
- AMH 的关键词检索遗漏是否随历史长度增加；
- 三个系统的 context 成本、延迟和准确率如何共同变化。

长历史 pilot 仍先各跑一次；case 冻结后再决定是否对完整 benchmark 跑三次并报告平均值与波动。
