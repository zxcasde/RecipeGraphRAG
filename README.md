# RecipeQA - 菜谱问答图 RAG 系统

基于知识图谱和向量检索的智能菜谱推荐与问答系统。

## 📁 核心文件

### 🚀 启动文件
- **`app.py`** - Streamlit Web 应用主程序

### 🧠 核心系统
- **`graph_rag_system.py`** - 图 RAG 系统主控制器（融合向量+图谱检索）
- **`llm_server.py`** - DeepSeek LLM 服务封装（支持流式输出）

### 🔍 检索模块
- **`vector_retriever.py`** - 向量检索（基于 SentenceTransformer）
- **`graph_retriever.py`** - 图谱检索（Neo4j Cypher 查询）
- **`query_optimizer.py`** - 查询优化器（LLM 提取意图和实体）

### 🎯 推荐模块
- **`advanced_recommender.py`** - 高级推荐引擎（场景推荐、相似推荐）
- **`preference_extractor.py`** - 用户偏好提取器
- **`user_manager.py`** - 用户画像管理
- **`user_graph_model.py`** - 用户图谱模型
- **`user_recommendation.py`** - 用户推荐逻辑

### 🛠️ 数据处理
- **`build_recipegraph_v2.py`** - 构建知识图谱（Neo4j）
- **`parse_recipe_md.py`** - 解析菜谱 Markdown 文件
- **`llm_recipe_parser.py`** - LLM 辅助解析菜谱
- **`generate_dict.py`** - 生成实体词典

### 📂 数据目录
- **`data/`** - 菜谱数据和向量索引
- **`dict/`** - 实体词典（食材、口味、标签等）

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install streamlit neo4j sentence-transformers openai python-dotenv
安装neo4j community并配置
```

### 2. 配置环境变量
创建 `.env` 文件：
```
DEEPSEEK_API_KEY=your_api_key_here
$env:DEEPSEEK_API_KEY="sk-c3c8709965474f6f908d0d11d849d2a6" <- 我的api
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 3. 构建知识图谱
```bash
python build_recipegraph_v2.py
```

### 4. 构建向量索引
```bash
python vector_retriever.py
```

### 5. 启动应用
```bash
streamlit run app.py
# 或双击 start_app.bat
```

## 🎯 核心功能

- ✅ **智能检索**：融合向量检索和图谱检索
- ✅ **查询优化**：LLM 提取用户意图和实体
- ✅ **个性化推荐**：基于用户历史和偏好
- ✅ **场景推荐**：健身、减肥、熬夜等场景
- ✅ **流式输出**：实时生成答案
- ✅ **用户画像**：自动学习用户偏好

## 📊 系统架构

```
用户查询 → 查询优化 → 并行检索（向量+图谱） → 结果融合 → LLM 生成答案
                ↓
          用户偏好提取 → 用户画像更新 → 个性化推荐
```

## 🔧 技术栈

- **前端**：Streamlit
- **LLM**：DeepSeek API
- **向量检索**：SentenceTransformer (paraphrase-multilingual-MiniLM-L12-v2)
- **图数据库**：Neo4j
- **语言**：Python 3.8+
# RecipeGraphRAG
# RecipeGraphRAG
