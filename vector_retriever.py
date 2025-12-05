# coding = utf-8
"""
向量检索模块
使用sentence-transformers进行语义检索
"""

import json
import pickle
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("警告：sentence-transformers未安装，向量检索功能将不可用")
    print("安装命令：pip install sentence-transformers")


class VectorRetriever:
    """向量检索器"""
    
    def __init__(self, model_name="BAAI/bge-m3"):
        """
        初始化向量检索器
        
        Args:
            model_name: sentence-transformers模型名称
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("请先安装sentence-transformers: pip install sentence-transformers")
        # BAAI/bge-m3  paraphrase-multilingual-MiniLM-L12-v2
        self.model = SentenceTransformer(model_name, cache_folder=f'/data/yangguang/Model/bge-m3', local_files_only=True)
        self.dish_vectors = {}  # 菜品名称向量
        self.dish_desc_vectors = {}  # 菜品描述向量
        self.dish_data = {}  # 菜品完整数据
        
    def build_index(self, recipes_json_path):
        """
        构建向量索引
        
        Args:
            recipes_json_path: recipes.json文件路径
        """
        print("正在加载菜谱数据...")
        recipes = []
        with open(recipes_json_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        recipe = json.loads(line)
                        recipes.append(recipe)
                    except json.JSONDecodeError as e:
                        print(f"警告：跳过无效行：{e}")
                        continue
        
        print(f"加载了 {len(recipes)} 道菜谱")
        print("正在构建向量索引...")
        
        # 准备文本
        dish_names = []
        dish_descriptions = []
        
        for recipe in recipes:
            name = recipe.get('name', '')
            if not name:
                continue
            
            # 菜品名称
            dish_names.append(name)
            
            # 菜品描述（综合多个字段）
            desc_parts = [name]
            
            # 添加分类（语义化）
            category = recipe.get('category', '')
            if category:
                category_map = {
                    'dessert': '甜品',
                    'main_dish': '主菜',
                    'soup': '汤',
                    'condiment': '调味料',
                    'drink': '饮品',
                    'staple': '主食',
                    'appetizer': '凉菜',
                    'side_dish': '配菜'
                }
                category_cn = category_map.get(category, category)
                desc_parts.append(f"分类：{category_cn}")
            
            # 添加标签（重要！用于匹配"快手菜"、"烘焙"等）
            tags = recipe.get('tags', [])
            if tags:
                tags_text = '、'.join(tags)
                desc_parts.append(f"标签：{tags_text}")
            
            # 添加口味（重要！用于匹配"辣"、"甜"等）
            flavors = recipe.get('flavors', [])
            if flavors:
                flavors_text = '、'.join(flavors)
                desc_parts.append(f"口味：{flavors_text}")
            
            # 添加难度（语义化，用于匹配"新手"、"简单"等）
            difficulty = recipe.get('difficulty')
            if difficulty:
                difficulty_map = {
                    1: "非常简单（新手友好）",
                    2: "简单（适合新手）",
                    3: "中等难度",
                    4: "较难",
                    5: "高难度"
                }
                difficulty_text = difficulty_map.get(difficulty, f"难度{difficulty}")
                desc_parts.append(f"难度：{difficulty_text}")
            
            # 添加菜品描述（重要！包含菜品特点）
            desc = recipe.get('desc', '')
            if desc:
                desc_parts.append(f"简介：{desc}")
            
            # 添加食材
            ingredients = recipe.get('ingredients', [])
            if ingredients:
                # 处理新格式：[{"name": "xxx", "amount": "xxx", "is_main": true}, ...]
                if isinstance(ingredients[0], dict):
                    ing_names = [ing.get('name', '') for ing in ingredients[:10]]
                else:
                    ing_names = ingredients[:10]
                ing_text = '、'.join(ing_names)
                desc_parts.append(f"食材：{ing_text}")
            
            # 添加调料
            condiments = recipe.get('condiments', [])
            if condiments:
                # 处理新格式：[{"name": "xxx", "amount": "xxx"}, ...]
                if isinstance(condiments[0], dict):
                    cond_names = [cond.get('name', '') for cond in condiments[:8]]
                else:
                    cond_names = condiments[:8]
                cond_text = '、'.join(cond_names)
                desc_parts.append(f"调料：{cond_text}")
            
            # 添加烹饪方法
            method = recipe.get('method', '')
            if method:
                desc_parts.append(f"做法：{method}")
            
            description = '。'.join(desc_parts)
            dish_descriptions.append(description)
            
            # 保存完整数据
            self.dish_data[name] = recipe
        
        # 编码向量
        print("正在编码菜品名称...")
        name_vectors = self.model.encode(dish_names, show_progress_bar=True, normalize_embeddings=True)
        
        print("正在编码菜品描述...")
        desc_vectors = self.model.encode(dish_descriptions, show_progress_bar=True, normalize_embeddings=True)
        
        # 保存向量
        for name, name_vec, desc_vec in zip(dish_names, name_vectors, desc_vectors):
            self.dish_vectors[name] = name_vec
            self.dish_desc_vectors[name] = desc_vec
        
        print(f"向量索引构建完成！共 {len(self.dish_vectors)} 道菜品")
    
    def save_index(self, save_path="data/vector_index.pkl"):
        """保存向量索引"""
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'dish_vectors': self.dish_vectors,
            'dish_desc_vectors': self.dish_desc_vectors,
            'dish_data': self.dish_data
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"向量索引已保存到：{save_path}")
    
    def load_index(self, load_path="data/vector_index.pkl"):
        """加载向量索引"""
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        
        self.dish_vectors = data['dish_vectors']
        self.dish_desc_vectors = data['dish_desc_vectors']
        self.dish_data = data['dish_data']
        
        print(f"向量索引已加载：{len(self.dish_vectors)} 道菜品")
    
    def search(self, query, top_k=10, use_description=True):
        """
        向量检索
        
        Args:
            query: 查询文本
            top_k: 返回Top-K结果
            use_description: 是否使用描述向量（更准确但慢）
        
        Returns:
            List[Tuple[str, float]]: [(菜品名, 相似度分数), ...]
        """
        # 编码查询
        query_vector = self.model.encode([query], normalize_embeddings=True)[0]
        
        # 选择向量库
        vectors_dict = self.dish_desc_vectors if use_description else self.dish_vectors
        
        # 计算相似度
        similarities = []
        for dish_name, dish_vector in vectors_dict.items():
            similarity = float(np.dot(query_vector, dish_vector))
            similarities.append((dish_name, similarity))
        
        # 排序并返回Top-K
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_dish_data(self, dish_name):
        """获取菜品完整数据"""
        return self.dish_data.get(dish_name)


if __name__ == "__main__":
    # 测试向量检索
    print("=" * 60)
    print("向量检索模块测试")
    print("=" * 60)
    
    retriever = VectorRetriever()
    
    # 构建索引
    recipes_path = "data/recipes_llm.json"
    retriever.build_index(recipes_path)
    
    # 保存索引
    retriever.save_index()
    
    # 测试检索
    test_queries = [
        "我想吃辣的菜",
        "有什么简单的家常菜",
        "鸡肉可以做什么",
        "清淡的汤",
        "适合夏天的菜"
    ]
    
    print("\n" + "=" * 60)
    print("检索测试")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n查询：{query}")
        results = retriever.search(query, top_k=5)
        for i, (dish, score) in enumerate(results, 1):
            print(f"  {i}. {dish} (相似度: {score:.3f})")
