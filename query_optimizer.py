# coding = utf-8
"""
LLM查询优化模块
使用LLM优化和重写用户查询
"""

from llm_server import ModelAPI
import re
import json


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, model_url="http://localhost:3001/generate", use_deepseek=False, api_key=None):
        """
        初始化查询优化器
        
        Args:
            model_url: 本地LLM服务URL
            use_deepseek: 是否使用DeepSeek API
            api_key: DeepSeek API密钥
        """
        if use_deepseek:
            self.model = ModelAPI(use_deepseek=True, api_key=api_key)
        else:
            self.model = ModelAPI(MODEL_URL=model_url)
    
    def optimize_query(self, user_query):
        """
        优化用户查询
        
        Args:
            user_query: 原始用户查询
        
        Returns:
            Dict: {
                'optimized_query': 优化后的查询,
                'intent': 意图类型,
                'entities': 识别的实体,
                'keywords': 关键词
            }
        """
        prompt = f"""你是一个菜谱问答系统的查询优化助手。请分析用户的查询，提取关键信息。

用户查询：{user_query}

请按以下格式返回JSON：
{{
    "optimized_query": "优化后的查询（补充完整、去除口语化）",
    "intent": "意图类型（query_dish/recommend/how_to_cook/ingredient_search/scene_search）",
    "entities": {{
        "dishes": ["菜品名或菜品类型，如：蛋糕、面包、饼干、汤、主菜"],
        "ingredients": ["食材名"],
        "scenes": ["场景"],
        "flavors": ["口味"],
        "tags": ["标签，如：快手菜、甜品、烘焙、新手友好、下午茶、家常菜"]
    }},
    "keywords": ["关键词1", "关键词2"],
    "difficulty_preference": "难度偏好（easy/medium/hard/null）"
}}

示例1：
用户查询：我想吃蛋糕类食品，最好是新手容易做的
返回：
{{
    "optimized_query": "推荐适合新手制作的蛋糕类甜品",
    "intent": "recommend",
    "entities": {{
        "dishes": ["蛋糕"],
        "ingredients": [],
        "scenes": [],
        "flavors": ["甜"],
        "tags": ["甜品", "烘焙", "新手友好", "快手菜"]
    }},
    "keywords": ["蛋糕", "新手", "简单", "甜品"],
    "difficulty_preference": "easy"
}}

示例2：
用户查询：我想吃点辣的
返回：
{{
    "optimized_query": "推荐一些辣味的菜品",
    "intent": "recommend",
    "entities": {{"dishes": [], "ingredients": [], "scenes": [], "flavors": ["辣"], "tags": []}},
    "keywords": ["辣", "推荐"],
    "difficulty_preference": null
}}

示例3：
用户查询：我喜欢吃有酸味的食物
返回：
{{
    "optimized_query": "推荐一些酸味的菜品",
    "intent": "recommend",
    "entities": {{"dishes": [], "ingredients": [], "scenes": [], "flavors": ["酸"], "tags": []}},
    "keywords": ["酸", "推荐"],
    "difficulty_preference": null
}}

示例4：
用户查询：想吃点甜的
返回：
{{
    "optimized_query": "推荐一些甜味的菜品",
    "intent": "recommend",
    "entities": {{"dishes": [], "ingredients": [], "scenes": [], "flavors": ["甜"], "tags": []}},
    "keywords": ["甜", "推荐"],
    "difficulty_preference": null
}}

注意：
- 常见口味包括：酸、甜、苦、辣、咸、鲜、麻、香等
- 常见标签包括：快手菜、甜品、烘焙、下午茶、家常菜、宴客菜、新手友好、减肥、营养等
- 菜品类型包括：蛋糕、面包、饼干、汤、主菜、凉菜、甜品、饮品等
- 难度关键词：新手/简单/容易/快手 → easy，中等 → medium，复杂/高级/难 → hard

现在请分析上面的用户查询："""

        try:
            response, _ = self.model.chat(query=prompt, history=[])
            
            # 尝试解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # 如果没有JSON，返回默认结构
                return self._default_optimization(user_query, response)
        
        except Exception as e:
            print(f"查询优化失败: {e}")
            return self._default_optimization(user_query, str(e))
    
    def _default_optimization(self, user_query, llm_response=""):
        """默认优化（当LLM失败时）"""
        # 简单的规则匹配
        intent = "query_dish"
        entities = {
            "dishes": [],
            "ingredients": [],
            "scenes": [],
            "flavors": [],
            "tags": []
        }
        keywords = []
        
        # 意图识别
        if any(word in user_query for word in ["推荐", "有什么", "做什么"]):
            intent = "recommend"
        elif any(word in user_query for word in ["怎么做", "做法", "步骤"]):
            intent = "how_to_cook"
        elif any(word in user_query for word in ["食材", "原料", "需要什么"]):
            intent = "ingredient_search"
        
        # 场景识别
        scenes = ["加班", "熬夜", "减肥", "健身", "聚会", "周末", "夜宵"]
        for scene in scenes:
            if scene in user_query:
                entities["scenes"].append(scene)
                keywords.append(scene)
        
        # 口味识别
        flavors = ["辣", "麻辣", "清淡", "酸", "甜", "酸甜", "咸", "鲜"]
        for flavor in flavors:
            if flavor in user_query:
                entities["flavors"].append(flavor)
                keywords.append(flavor)
        
        # 标签识别
        tags = ["简单", "快手", "下饭", "新手", "家常"]
        for tag in tags:
            if tag in user_query:
                entities["tags"].append(tag)
                keywords.append(tag)
        
        return {
            "optimized_query": user_query,
            "intent": intent,
            "entities": entities,
            "keywords": keywords,
            "llm_response": llm_response
        }
    
    def expand_query(self, query, context=None):
        """
        查询扩展
        
        Args:
            query: 原始查询
            context: 上下文信息（可选）
        
        Returns:
            List[str]: 扩展后的查询列表
        """
        prompt = f"""请为以下菜谱查询生成3个语义相似但表达不同的查询变体，用于扩展检索范围。

原始查询：{query}

要求：
1. 保持原意
2. 使用不同的表达方式
3. 可以补充相关信息

请直接返回3个查询，每行一个，不要编号。

示例：
原始查询：我想吃辣的菜
返回：
推荐一些麻辣口味的菜品
有什么辣味的家常菜
适合喜欢吃辣的人的菜谱

现在请为上面的查询生成变体："""

        try:
            response, _ = self.model.chat(query=prompt, history=[])
            
            # 提取查询
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            # 去除编号
            queries = []
            for line in lines:
                # 去除数字编号、点、破折号等
                cleaned = re.sub(r'^[\d\-\.\)）、]+\s*', '', line)
                if cleaned and len(cleaned) > 2:
                    queries.append(cleaned)
            
            return queries[:3] if queries else [query]
        
        except Exception as e:
            print(f"查询扩展失败: {e}")
            return [query]
    
    def generate_search_keywords(self, query):
        """
        生成搜索关键词
        
        Args:
            query: 用户查询
        
        Returns:
            List[str]: 关键词列表
        """
        prompt = f"""请从以下菜谱查询中提取最重要的3-5个搜索关键词。

查询：{query}

要求：
1. 提取核心概念
2. 包括菜品名、食材、场景、口味等
3. 去除无意义的词（如"我想"、"有什么"等）

请直接返回关键词，用逗号分隔。

示例：
查询：我今天加班熬夜，想吃点简单快手的辣菜
返回：加班,熬夜,简单,快手,辣

现在请提取关键词："""

        try:
            response, _ = self.model.chat(query=prompt, history=[])
            
            # 提取关键词
            keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
            # 去除编号等
            keywords = [re.sub(r'^[\d\.\)）、]+\s*', '', kw) for kw in keywords]
            keywords = [kw for kw in keywords if kw and len(kw) > 1]
            
            return keywords[:5]
        
        except Exception as e:
            print(f"关键词提取失败: {e}")
            # 简单分词
            return [word for word in query if len(word) > 1][:5]


if __name__ == "__main__":
    # 测试查询优化
    print("=" * 60)
    print("查询优化模块测试")
    print("=" * 60)
    
    optimizer = QueryOptimizer()
    
    test_queries = [
        "我想吃点辣的",
        "今天加班熬夜吃什么好",
        "宫保鸡丁怎么做",
        "鸡肉可以做什么菜",
        "有什么简单的家常菜"
    ]
    
    for query in test_queries:
        print(f"\n原始查询：{query}")
        
        # 优化查询
        result = optimizer.optimize_query(query)
        print(f"优化后：{result['optimized_query']}")
        print(f"意图：{result['intent']}")
        print(f"实体：{result['entities']}")
        print(f"关键词：{result['keywords']}")
        
        # 查询扩展
        expanded = optimizer.expand_query(query)
        print(f"扩展查询：")
        for i, eq in enumerate(expanded, 1):
            print(f"  {i}. {eq}")
