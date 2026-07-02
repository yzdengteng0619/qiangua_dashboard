# 千瓜小红书数据分析 Pipeline

4层LLM分析Pipeline：热词+话题聚类 → 深度分析 → 爆款笔记分析 → 选题推荐。

## 文件说明

| 文件 | 功能 |
|------|------|
| `qiangua_upload_server.py` | HTTP上传服务（端口8090），支持xls/xlsx/tar/zip上传+解析+LLM分析+看板生成 |
| `qiangua_ingest.py` | 独立的数据解析入库脚本，可命令行单独使用 |
| `intel_brand_knowledge.py` | Intel芯鲜事品牌知识 + 4层Pipeline的LLM prompt模板 |
| `dashboard_generator.py` | HTML看板生成器，从L1-L4分析结果渲染看板 |
| `dashboard_template.html` | 看板HTML模板（CSS+JS，渐进式信息架构） |

## Pipeline架构

```
上传xls/xlsx → 解析入库(SQLite)
                    ↓
Layer 1: 热词+话题主题聚类（LLM）
                    ↓
Layer 2: 高/中相关聚类深度分析（LLM）
                    ↓
Layer 3: 爆款笔记分类+归组+原因分析（LLM）
                    ↓
Layer 4: 综合L1-L3产出选题推荐（LLM）
                    ↓
HTML看板生成（渐进式展开）
```

## 使用方式

### 上传+分析（推荐）
```bash
python3 qiangua_upload_server.py --port 8090
# 浏览器打开 http://localhost:8090 上传文件
```

### 独立解析
```bash
python3 qiangua_ingest.py /path/to/data.xlsx --dashboard
```

## 依赖

- Python 3.10+
- pandas, xlrd（Excel解析）
- requests（LLM API调用）
- SQLite3（内置）

## API Key

运行时从 `~/.minimax_key` 读取MiniMax API Key，不硬编码在代码中。
