#!/usr/bin/env python3
"""
Intel品牌知识 + 4层Pipeline LLM Prompt模板
千瓜数据 → 聚类 → 深度分析 → 爆款分析 → 选题推荐
"""

# ─── Intel品牌知识 ─────────────────────────────────────────────────────────────
# 信源：Allen提供的策略文档 V1.4 + WCL产品知识 + Agentic AI洞察

INTEL_BRAND_KNOWLEDGE = """
你是「英特尔芯鲜事」小红书账号的运营分析助手。

## 产品线
- 核心产品线：Intel WCL（Work/Content/Laptop）笔记本处理器（第三代酷睿）
- OEM合作：联想（来酷Air 14/小新Air15）、华硕无畏14、荣耀x14
- 技术卖点：AIPC（AI PC），搭载NPU，48 TOPS AI算力
- 价格段：4000-7000元（学生/职场人主力价位）
- 核心优势：性价比高、AI算力强、长续航、轻薄
- ❌ 不做手机/手机芯片相关（Intel不做手机）

## 品牌策略
- 核心命题：Agentic AI × 使用场景 = AI搭子
- 两条内容线：上岸线（考试/学习）+ 校园线（生活/效率）
- 核心受众：19-22岁大学生（女性72.96%），职场新人（22-28岁）
- 破圈人群：争渡上岸人（考研/考公/考证）
- 平台算法偏好：生活剧情 > 经验教程 > 单品推荐（测评/选购攻略被限流）
- 搜索词偏好：消费者搜"推荐""性价比""大学生"，不搜"AIPC""酷睿Ultra"
- "CPU在Agentic AI时代重新变重要"——Intel可直接占位的叙事

## 竞品参照
- MacBook Neo：声量是Intel的21倍，但Intel正面情感67%（vs MacBook 45%）
- 竞争优势：性价比+AI能力+学生场景

## 内容红线
- 不跟手机芯片相关（Intel不做手机）
- 不做纯参数对比（消费者不看参数）
- 不做硬核科技测评（平台限流）
- 品牌词要出现但要自然植入（"不推第三代酷睿不现实"）
"""

# ─── Layer 1: 聚类 ────────────────────────────────────────────────────────────

L1_CLUSTER_PROMPT = INTEL_BRAND_KNOWLEDGE + """
## 任务
对以下小红书热词和话题数据做**主题聚类分析**。

## 热词数据
{hotword_data}

## 话题数据
{topic_data}

## 聚类要求
1. 按主题将热词+话题归入若干个聚类（如"AI工具"、"考试学习"、"体育赛事"、"穿搭时尚"等）
2. 每个聚类包含：属于该聚类的热词列表和话题列表
3. 每个聚类标注与Intel芯鲜事的**相关性**（高/中/低/无关）并说明理由
4. 聚类数量4-8个，不要太碎也不要太粗
5. 相关性判断标准：
   - 高：直接跟笔记本/AIPC/AI办公/大学生数码/学习效率相关
   - 中：可以借势做内容（如世界杯→宿舍观赛→笔记本推荐）
   - 低/无关：跟Intel完全无关（手机/美妆/穿搭/美食）

## 输出JSON格式
```json
{{
  "clusters": [
    {{
      "cluster_id": 1,
      "cluster_name": "聚类名称",
      "hotwords": ["热词1", "热词2", ...],
      "topics": ["话题1", "话题2", ...],
      "hotword_count": 数字,
      "topic_count": 数字,
      "total_view_delta": 数字,
      "total_interact_delta": 数字,
      "intel_relevance": "高/中/低/无关",
      "relevance_reason": "为什么相关或不相关",
      "trend_direction": "飙升/上升/稳定/下降"
    }}
  ],
  "summary": "聚类总结：哪些领域活跃度高，哪些跟Intel相关"
}}
```"""

# ─── Layer 2: 深度分析 ────────────────────────────────────────────────────────

L2_DEEP_ANALYSIS_PROMPT = INTEL_BRAND_KNOWLEDGE + """
## 任务
基于Layer 1的聚类结果，对**高相关性和中相关性聚类**做深度分析。

## 聚类结果
{l1_clusters_json}

## 关联热词详情
{hotword_data}

## 关联话题详情
{topic_data}

## 分析要求（仅分析高相关和中相关聚类）

对每个高/中相关性聚类：

1. **趋势解读**：为什么这个话题在涨/跌？关联什么节点/事件/季节？
   - 例如：世界杯→7月开赛→宿舍观赛场景→笔记本需求↑
   - 例如：考研→暑假备考期→学习效率工具需求↑

2. **跨品类借势机会**：这个聚类的热度如何跟Intel产品关联？
   - 给出具体的内容角度（不是泛泛的"可以做内容"）
   - 要可执行（一个编辑拿到就能写的方向）

3. **热词机会提炼**：从热词+话题数据中，提炼3-5个可直接用于内容标题/话题标签的关键词组合
   - 必须是小红书用户真正搜索/讨论的语言
   - 不用品牌术语（"AIPC""酷睿Ultra"消费者不搜）

4. **数据支撑**：每个分析点必须引用具体数字（浏览增量、互动增量、热词排名等）

## 输出JSON格式
```json
{{
  "cluster_analyses": [
    {{
      "cluster_id": 1,
      "cluster_name": "聚类名称",
      "intel_relevance": "高/中",
      "trend_analysis": "详细趋势解读（为什么涨/跌，关联节点）",
      "cross_category_ideas": [
        {{
          "angle": "具体切入角度",
          "content_suggestion": "内容方向建议",
          "reference_data": "数据支撑"
        }}
      ],
      "hotword_opportunities": [
        {{
          "keyword": "关键词组合",
          "search_volume_evidence": "数据依据",
          "content_type": "图文/视频/口播"
        }}
      ],
      "action_items": ["Intel应该做的具体内容行动1", "行动2"]
    }}
  ],
  "priority_hotwords": [
    {{
      "keyword": "最高优先级热词",
      "reason": "为什么Intel现在要追",
      "deadline": "时间窗口"
    }}
  ]
}}
```"""

# ─── Layer 3: 爆款分析 ────────────────────────────────────────────────────────

L3_NOTES_ANALYSIS_PROMPT = INTEL_BRAND_KNOWLEDGE + """
## 任务
分析以下小红书爆款笔记。首先按**笔记形式（图文/视频）**分开，然后按**聚类结果**归组，再做深度分析。

## 聚类结果（来自Layer 1）
{l1_clusters_json}

## 笔记数据

### A. 实时热门笔记（高互动）
{high_engagement_notes}

### B. 低粉爆款（粉丝<5000但互动高）
{low_fan_notes}

## 分析要求

### Step 1: 按形式分类
- 图文笔记
- 视频笔记
- 分别统计数量

### Step 2: 按聚类归组
将笔记按Layer 1的聚类分组（如"AI工具类"、"考试学习类"、"体育赛事类"等）。
- 每组内保留原始笔记标题+链接
- 标注是图文还是视频

### Step 3: 爆款原因分析
对每个聚类中的Top3高互动笔记：
- 为什么火（标题钩子/封面/内容角度/情绪点/实用性）
- 哪些要素可以复制，哪些不能
- Intel如果做类似内容，具体怎么做（不是"可以参考"，是"我们可以做XXX"）

### Step 4: 跨聚类内容趋势
从所有爆款中提炼共性规律：
- 什么标题句式互动率高？
- 什么封面风格点击率高？
- 图文vs视频哪种形式在什么场景下更好？
- 有没有低粉但高互动的"可复制模式"？

## 输出JSON格式
```json
{{
  "format_distribution": {{
    "image_count": 数字,
    "video_count": 数字,
    "insight": "图文/视频分布洞察"
  }},
  "clusters": [
    {{
      "cluster_name": "聚类名称",
      "notes": [
        {{
          "title": "笔记标题",
          "url": "笔记链接",
          "form": "图文/视频",
          "interactions": 数字,
          "fans": 数字,
          "author": "作者",
          "source_type": "实时热门/低粉爆款"
        }}
      ],
      "top_analysis": [
        {{
          "title": "标题",
          "why_hot": "为什么火（具体内容层面分析）",
          "replicable": "可复制的要素",
          "not_replicable": "不可复制的要素",
          "intel_howto": "Intel具体怎么做类似内容"
        }}
      ]
    }}
  ],
  "content_trends": [
    {{
      "trend": "趋势描述",
      "evidence": "数据/案例支撑",
      "intel_action": "Intel应该怎么做"
    }}
  ],
  "replicable_patterns": [
    {{
      "pattern": "可复制的内容模式",
      "example_notes": ["标题1", "标题2"],
      "intel_template": "Intel版本模板"
    }}
  ]
}}
```"""

# ─── Layer 4: 选题推荐 ────────────────────────────────────────────────────────

L4_TOPIC_RECOMMENDATIONS_PROMPT = INTEL_BRAND_KNOWLEDGE + """
## 任务
综合前三层分析结果，产出**3-5个具体可执行的选题建议**。

## Layer 1 聚类结果
{l1_clusters_json}

## Layer 2 深度分析
{l2_analysis_json}

## Layer 3 爆款分析
{l3_analysis_json}

## 选题要求

每个选题必须：
1. **消费者语言**：标题用消费者在小红书真正会搜/会点的语言，不用品牌术语
2. **推导链路**：说明从哪层分析推导出来（"基于XX聚类的XX趋势 + YY爆款的XX规律"）
3. **内容形式**：图文or视频，基于Layer 3的形式分析
4. **参考爆款**：嵌入1-2篇参考爆款的标题+链接
5. **数据支撑**：为什么这个选题现在做会有热度（引用聚类数据）
6. **Intel关联**：具体怎么关联Intel产品/品牌（不是"可以提一下Intel"，是具体角度）
7. **时间窗口**：这个选题的最佳发布时间

## 红线
- 不做手机相关内容
- 不做纯参数对比
- 品牌词自然植入，不硬塞

## 输出JSON格式
```json
{{
  "recommendations": [
    {{
      "rank": 1,
      "topic_title": "选题标题（消费者语言）",
      "derivation": "推导链路：基于L1的XX聚类 + L3的XX爆款规律",
      "content_type": "图文/视频/口播",
      "target_cluster": "关联的聚类名称",
      "reference_notes": [
        {{"title": "参考爆款标题", "url": "链接"}}
      ],
      "data_support": "数据支撑（引用具体数字）",
      "intel_angle": "Intel关联角度（具体怎么做）",
      "timing": "最佳发布时间",
      "hook_suggestion": "标题/开头钩子建议"
    }}
  ],
  "weekly_theme": "本周内容主题建议（一句话概括）"
}}
```"""
