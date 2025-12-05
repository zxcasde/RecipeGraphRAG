# coding = utf-8
"""
用户偏好自动提取模块
从用户的自然对话中提取偏好、历史和标签
基于规则匹配 + 知识图谱实体匹配
"""

import re
import json
from py2neo import Graph


class PreferenceExtractor:
    """从用户对话中自动提取偏好信息（基于规则 + 知识图谱）"""
    
    def __init__(self, use_deepseek=True, api_key=None):
        """
        初始化偏好提取器
        
        Args:
            use_deepseek: 保留参数以兼容，但不使用
            api_key: 保留参数以兼容，但不使用
        """
        # 连接知识图谱
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
        
        # 加载知识图谱中的实体
        self._load_entities_from_graph()
        # 定义口味关键词
        self.flavor_keywords = {
            '酸': ['酸', '酸味', '酸的', '酸爽', '酸辣'],
            '甜': ['甜', '甜味', '甜的', '甜品', '甜食'],
            '苦': ['苦', '苦味', '苦的'],
            '辣': ['辣', '辣味', '辣的', '麻辣', '香辣', '酸辣', '微辣', '中辣', '特辣', '辛辣'],
            '咸': ['咸', '咸味', '咸的', '重口味'],
            '鲜': ['鲜', '鲜味', '鲜美', '鲜香'],
            '麻': ['麻', '麻味', '麻辣', '花椒'],
            '香': ['香', '香味', '香的'],
            '清淡': ['清淡', '淡', '少油', '少盐'],
        }
        
        # 定义生活习惯/场景标签
        self.tag_keywords = {
            '熬夜': ['熬夜', '晚睡', '夜宵', '宵夜'],
            '加班': ['加班', '工作忙', '没时间'],
            '健身': ['健身', '锻炼', '运动', '增肌'],
            '减脂': ['减脂', '减肥', '瘦身', '控制体重', '低卡'],
            '养生': ['养生', '保健', '滋补', '调理'],
            '快手': ['快手', '快速', '简单', '方便', '省时', '10分钟', '5分钟'],
            '宴客': ['宴客', '请客', '聚餐', '招待', '待客'],
            '便当': ['便当', '带饭', '午餐盒'],
            '下酒': ['下酒', '喝酒', '配酒'],
            '早餐': ['早餐', '早饭', '早上吃'],
            '午餐': ['午餐', '午饭', '中午吃'],
            '晚餐': ['晚餐', '晚饭', '晚上吃'],
        }
        
        # 常见食材（作为备用，优先使用知识图谱中的）
        self.ingredient_keywords = [
            '鸡肉', '猪肉', '牛肉', '羊肉', '鱼', '虾', '蟹', '鸡蛋', '豆腐',
            '土豆', '番茄', '黄瓜', '茄子', '青椒', '洋葱', '蒜', '姜',
            '米饭', '面条', '面粉', '豆芽', '白菜', '菠菜', '芹菜'
        ]
    
    def _load_entities_from_graph(self):
        """从知识图谱加载所有实体"""
        try:
            # 加载所有菜品名
            cypher_dishes = "MATCH (d:Dish) RETURN d.name as name"
            dishes = self.g.run(cypher_dishes).data()
            self.dish_names = [d['name'] for d in dishes if d['name']]
            
            # 加载所有食材名
            cypher_ingredients = "MATCH (i:Ingredient) RETURN i.name as name"
            ingredients = self.g.run(cypher_ingredients).data()
            self.graph_ingredients = [i['name'] for i in ingredients if i['name']]
            
            # 加载所有口味
            cypher_flavors = "MATCH (f:Flavor) RETURN f.name as name"
            flavors = self.g.run(cypher_flavors).data()
            self.graph_flavors = [f['name'] for f in flavors if f['name']]
            
            # 加载所有标签
            cypher_tags = "MATCH (t:Tag) RETURN t.name as name"
            tags = self.g.run(cypher_tags).data()
            self.graph_tags = [t['name'] for t in tags if t['name']]
            
            print(f"  已加载知识图谱实体: {len(self.dish_names)}道菜, {len(self.graph_ingredients)}种食材, {len(self.graph_flavors)}种口味, {len(self.graph_tags)}个标签")
        except Exception as e:
            print(f"  加载知识图谱实体失败: {e}")
            self.dish_names = []
            self.graph_ingredients = []
            self.graph_flavors = []
            self.graph_tags = []
    
    def extract_from_query(self, user_query):
        """
        从用户查询中提取偏好信息（基于规则匹配）
        
        Args:
            user_query: 用户的自然语言查询
        
        Returns:
            Dict: {
                'dishes_cooked': [],      # 做过的菜
                'dishes_liked': [],       # 喜欢的菜
                'flavors': [],            # 口味偏好
                'tags': [],               # 生活习惯/场景标签
                'ingredients': [],        # 食材偏好
                'has_preference': bool    # 是否包含偏好信息
            }
        """
        result = self._default_result()
        
        # 规则1: 提取做过的菜（优先匹配知识图谱中的菜品）
        # 先检查是否有"做过"/"煮过"等关键词
        if re.search(r'(?:做|煮|炒|烧|炖|蒸|煎|炸|烤)过', user_query):
            # 遍历知识图谱中的所有菜品，看是否在查询中出现
            for dish_name in self.dish_names:
                if dish_name in user_query:
                    if dish_name not in result['dishes_cooked']:
                        result['dishes_cooked'].append(dish_name)
                        result['has_preference'] = True
        
        # 规则2: 提取喜欢的菜（优先匹配知识图谱中的菜品）
        # 检查是否有"喜欢"/"爱吃"等关键词
        preference_words = ['喜欢', '爱吃', '爱', '最爱', '很爱', '特别喜欢']
        has_like_context = any(word in user_query for word in preference_words)
        
        if has_like_context:
            # 遍历知识图谱中的所有菜品
            for dish_name in self.dish_names:
                if dish_name in user_query:
                    # 排除已经在dishes_cooked中的
                    if dish_name not in result['dishes_cooked'] and dish_name not in result['dishes_liked']:
                        result['dishes_liked'].append(dish_name)
                        result['has_preference'] = True
        
        # 规则3: 提取口味偏好（优先匹配知识图谱中的口味）
        # 检查是否包含表达偏好的词
        preference_words_for_flavor = ['喜欢', '爱吃', '想吃', '偏好', '口味', '爱', '最爱']
        has_preference_context = any(word in user_query for word in preference_words_for_flavor)
        
        # 先匹配知识图谱中的口味
        for flavor in self.graph_flavors:
            if flavor in user_query:
                if has_preference_context or flavor + '的' in user_query or flavor + '味' in user_query:
                    if flavor not in result['flavors']:
                        result['flavors'].append(flavor)
                        result['has_preference'] = True
        
        # 再匹配预定义的口味关键词（作为补充）
        for flavor, keywords in self.flavor_keywords.items():
            if flavor not in result['flavors']:  # 避免重复
                for keyword in keywords:
                    if keyword in user_query:
                        if has_preference_context or keyword + '的' in user_query or keyword + '味' in user_query:
                            if flavor not in result['flavors']:
                                result['flavors'].append(flavor)
                                result['has_preference'] = True
                            break
        
        # 规则4: 提取生活习惯/场景标签（优先匹配知识图谱中的标签）
        # 先匹配知识图谱中的标签
        for tag in self.graph_tags:
            if tag in user_query:
                if tag not in result['tags']:
                    result['tags'].append(tag)
                    result['has_preference'] = True
        
        # 再匹配预定义的标签关键词（作为补充）
        for tag, keywords in self.tag_keywords.items():
            if tag not in result['tags']:  # 避免重复
                for keyword in keywords:
                    if keyword in user_query:
                        if tag not in result['tags']:
                            result['tags'].append(tag)
                            result['has_preference'] = True
                        break
        
        # 规则5: 提取食材偏好（优先匹配知识图谱中的食材）
        # 只有在明确表达喜欢的情况下才提取
        if has_preference_context:
            # 先匹配知识图谱中的食材
            for ingredient in self.graph_ingredients:
                if ingredient in user_query:
                    if ingredient not in result['ingredients']:
                        result['ingredients'].append(ingredient)
                        result['has_preference'] = True
            
            # 再匹配预定义的食材（作为补充）
            for ingredient in self.ingredient_keywords:
                if ingredient not in result['ingredients'] and ingredient in user_query:
                    result['ingredients'].append(ingredient)
                    result['has_preference'] = True
        
        return result
    
    def _default_result(self):
        """默认返回结果"""
        return {
            'dishes_cooked': [],
            'dishes_liked': [],
            'flavors': [],
            'tags': [],
            'ingredients': [],
            'has_preference': False
        }


if __name__ == '__main__':
    """测试偏好提取"""
    extractor = PreferenceExtractor()
    
    test_cases = [
        "我喜欢吃辛辣的食物",
        "我做过西红柿炒鸡蛋",
        "我最近经常熬夜，想吃点养生的食物",
        "白灼虾怎么做",
        "我喜欢吃宫保鸡丁和麻婆豆腐",
        "我喜欢吃鸡肉",
    ]
    
    print("=" * 60)
    print("测试用户偏好提取")
    print("=" * 60)
    
    for query in test_cases:
        print(f"\n用户查询: {query}")
        result = extractor.extract_from_query(query)
        print(f"提取结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("-" * 60)
