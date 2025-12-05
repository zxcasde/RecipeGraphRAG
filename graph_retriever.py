# coding = utf-8
"""
图谱检索增强模块
基于Neo4j知识图谱的多跳检索
"""

from py2neo import Graph
from typing import List, Dict, Tuple, Set
from collections import defaultdict


class GraphRetriever:
    """图谱检索器"""
    
    def __init__(self):
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
    
    def search_by_dish(self, dish_name, depth=1):
        """
        以菜品为中心的子图检索
        
        Args:
            dish_name: 菜品名称
            depth: 检索深度（跳数）
        
        Returns:
            Dict: 包含菜品相关的所有信息
        """
        cypher = f"""
        MATCH path=(d:Dish {{name: $dish_name}})-[r*1..{depth}]-(n)
        RETURN path
        LIMIT 100
        """
        
        result = self.g.run(cypher, dish_name=dish_name).data()
        
        # 提取信息
        info = {
            'dish': dish_name,
            'ingredients': [],
            'condiments': [],
            'tools': [],
            'method': None,
            'category': None,
            'tags': [],
            'flavors': [],
            'similar_dishes': [],
            'difficulty': None,
            'steps': None,
            'tips': None
        }
        
        # 用于存储带用量的食材和调料
        ingredient_dict = {}
        condiment_dict = {}
        
        for record in result:
            path_data = record['path']
            nodes = path_data.nodes
            rels = path_data.relationships
            
            # 提取食材和调料的用量信息
            for rel in rels:
                rel_type = type(rel).__name__
                start_node = rel.start_node
                end_node = rel.end_node
                
                # 检查是否是食材或调料关系
                if 'Dish' in start_node.labels and start_node.get('name') == dish_name:
                    amount = rel.get('amount', '')
                    
                    if 'Ingredient' in end_node.labels:
                        ing_name = end_node.get('name', '')
                        if ing_name and ing_name not in ingredient_dict:
                            ingredient_dict[ing_name] = amount
                    elif 'Condiment' in end_node.labels:
                        cond_name = end_node.get('name', '')
                        if cond_name and cond_name not in condiment_dict:
                            condiment_dict[cond_name] = amount
            
            for node in nodes:
                node_labels = list(node.labels)
                if not node_labels:
                    continue
                
                label = node_labels[0]
                name = node.get('name', '')
                
                if label == 'Tool' and name:
                    if name not in info['tools']:
                        info['tools'].append(name)
                elif label == 'Tag' and name:
                    if name not in info['tags']:
                        info['tags'].append(name)
                elif label == 'Flavor' and name:
                    if name not in info['flavors']:
                        info['flavors'].append(name)
                elif label == 'Dish' and name != dish_name:
                    if name not in info['similar_dishes']:
                        info['similar_dishes'].append(name)
            
            # 提取菜品属性
            for node in nodes:
                if 'Dish' in node.labels and node.get('name') == dish_name:
                    info['difficulty'] = node.get('difficulty')
                    info['steps'] = node.get('steps')
                    info['tips'] = node.get('tips')
        
        # 将带用量的食材和调料转换为列表格式
        info['ingredients'] = [f"{name} {amount}".strip() if amount else name 
                               for name, amount in ingredient_dict.items()]
        info['condiments'] = [f"{name} {amount}".strip() if amount else name 
                              for name, amount in condiment_dict.items()]
        
        return info
    
    def search_by_ingredient(self, ingredient_name, limit=10):
        """
        根据食材查找菜品
        
        Args:
            ingredient_name: 食材名称
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 菜品列表
        """
        cypher = """
        MATCH (i:Ingredient {name: $ingredient})<-[:need_ingredient]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_tag]->(t:Tag)
        OPTIONAL MATCH (d)-[:has_flavor]->(f:Flavor)
        WITH d, COLLECT(DISTINCT t.name) as tags, COLLECT(DISTINCT f.name) as flavors
        RETURN d.name as dish, d.difficulty as difficulty, tags, flavors
        LIMIT $limit
        """
        
        result = self.g.run(cypher, ingredient=ingredient_name, limit=limit).data()
        return result
    
    def search_by_tag(self, tag_name, limit=10):
        """
        根据标签查找菜品（包括场景标签，如：熬夜、快手菜、健身等）
        
        Args:
            tag_name: 标签名称
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 菜品列表
        """
        cypher = """
        MATCH (t:Tag {name: $tag})<-[:has_tag]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_tag]->(t2:Tag)
        OPTIONAL MATCH (d)-[:has_flavor]->(f:Flavor)
        WITH d, COLLECT(DISTINCT t2.name) as tags, COLLECT(DISTINCT f.name) as flavors
        RETURN d.name as dish, d.difficulty as difficulty, tags, flavors
        LIMIT $limit
        """
        
        result = self.g.run(cypher, tag=tag_name, limit=limit).data()
        return result
    
    def search_by_flavor(self, flavor_name, limit=10):
        """
        根据口味查找菜品
        
        Args:
            flavor_name: 口味名称
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 菜品列表
        """
        cypher = """
        MATCH (f:Flavor {name: $flavor})<-[:has_flavor]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_tag]->(t:Tag)
        WITH d, COLLECT(DISTINCT t.name) as tags
        RETURN d.name as dish, d.difficulty as difficulty, tags
        LIMIT $limit
        """
        
        result = self.g.run(cypher, flavor=flavor_name, limit=limit).data()
        return result
    
    def find_similar_dishes(self, dish_name, limit=5):
        """
        查找相似菜品（基于共同食材、口味、标签）
        
        Args:
            dish_name: 菜品名称
            limit: 返回数量限制
        
        Returns:
            List[Tuple[str, int, List[str]]]: [(菜品名, 相似度分数, 共同特征), ...]
        """
        # 方法1：通过similar_to关系
        cypher1 = """
        MATCH (d1:Dish {name: $dish})-[:similar_to]-(d2:Dish)
        RETURN d2.name as dish, 'similar_to' as reason
        LIMIT $limit
        """
        
        # 方法2：通过共同食材
        cypher2 = """
        MATCH (d1:Dish {name: $dish})-[:need_ingredient]->(i:Ingredient)<-[:need_ingredient]-(d2:Dish)
        WHERE d1 <> d2
        WITH d2, COUNT(DISTINCT i) as common_ingredients, COLLECT(DISTINCT i.name) as ingredients
        RETURN d2.name as dish, common_ingredients as score, ingredients as common_features
        ORDER BY score DESC
        LIMIT $limit
        """
        
        # 方法3：通过共同口味
        cypher3 = """
        MATCH (d1:Dish {name: $dish})-[:has_flavor]->(f:Flavor)<-[:has_flavor]-(d2:Dish)
        WHERE d1 <> d2
        WITH d2, COUNT(DISTINCT f) as common_flavors, COLLECT(DISTINCT f.name) as flavors
        RETURN d2.name as dish, common_flavors as score, flavors as common_features
        ORDER BY score DESC
        LIMIT $limit
        """
        
        results = []
        
        # 合并结果
        for cypher in [cypher1, cypher2, cypher3]:
            data = self.g.run(cypher, dish=dish_name, limit=limit).data()
            for item in data:
                dish = item.get('dish')
                score = item.get('score', 1)
                features = item.get('common_features', [])
                reason = item.get('reason', '相似')
                
                if dish:
                    results.append((dish, score, features if isinstance(features, list) else [reason]))
        
        # 去重并排序
        dish_scores = defaultdict(lambda: {'score': 0, 'features': set()})
        for dish, score, features in results:
            dish_scores[dish]['score'] += score
            dish_scores[dish]['features'].update(features)
        
        # 转换为列表
        final_results = [
            (dish, data['score'], list(data['features']))
            for dish, data in dish_scores.items()
        ]
        
        # 排序
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results[:limit]
    
    def get_user_preference_dishes(self, user_id, limit=10):
        """
        获取用户偏好的菜品
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            Dict: 包含用户历史和推荐
        """
        # 获取用户历史
        history_cypher = """
        MATCH (u:User {user_id: $user_id})-[r]->(d:Dish)
        RETURN type(r) as action, d.name as dish, r.count as count
        ORDER BY r.count DESC
        """
        
        history = self.g.run(history_cypher, user_id=user_id).data()
        
        # 获取用户节点的preferences属性（包含口味、标签、食材偏好）
        user_pref_cypher = """
        MATCH (u:User {user_id: $user_id})
        RETURN u.preferences as preferences
        """
        
        user_prefs = self.g.run(user_pref_cypher, user_id=user_id).data()
        
        # 解析preferences JSON
        import json
        preferences = {}
        if user_prefs and user_prefs[0].get('preferences'):
            try:
                preferences = json.loads(user_prefs[0]['preferences'])
                print(f"  [DEBUG] 从用户节点读取偏好: {preferences}")
            except Exception as e:
                print(f"  [DEBUG] 解析preferences失败: {e}")
                preferences = {}
        
        # 如果没有preferences属性或为空，尝试从关系推断
        if not preferences or not any([preferences.get('flavors'), preferences.get('tags'), preferences.get('ingredients')]):
            print(f"  [DEBUG] 用户节点无偏好数据，尝试从关系推断...")
            pref_cypher = """
            MATCH (u:User {user_id: $user_id})-[:liked|cooked]->(d:Dish)
            OPTIONAL MATCH (d)-[:has_flavor]->(f:Flavor)
            OPTIONAL MATCH (d)-[:has_tag]->(t:Tag)
            WITH COLLECT(DISTINCT f.name) as flavors, COLLECT(DISTINCT t.name) as tags
            RETURN flavors, tags
            """
            
            prefs = self.g.run(pref_cypher, user_id=user_id).data()
            inferred_prefs = prefs[0] if prefs else {'flavors': [], 'tags': []}
            print(f"  [DEBUG] 从关系推断的偏好: {inferred_prefs}")
            
            # 合并推断的偏好和已有偏好
            if not preferences:
                preferences = inferred_prefs
            else:
                # 补充缺失的字段
                if 'flavors' not in preferences:
                    preferences['flavors'] = inferred_prefs.get('flavors', [])
                if 'tags' not in preferences:
                    preferences['tags'] = inferred_prefs.get('tags', [])
        
        # 确保返回的preferences包含所有必要字段
        if 'flavors' not in preferences:
            preferences['flavors'] = []
        if 'tags' not in preferences:
            preferences['tags'] = []
        if 'ingredients' not in preferences:
            preferences['ingredients'] = []
        
        print(f"  [DEBUG] 最终返回的偏好数据: {preferences}")
        
        return {
            'history': history,
            'preferences': preferences
        }
    
    def multi_hop_search(self, start_nodes, relation_types, depth=2):
        """
        多跳图谱搜索
        
        Args:
            start_nodes: 起始节点列表 [(label, name), ...]
            relation_types: 关系类型列表
            depth: 搜索深度
        
        Returns:
            List[Dict]: 搜索结果
        """
        # 构建Cypher查询
        node_conditions = " OR ".join([
            f"(n:{label} {{name: '{name}'}})"
            for label, name in start_nodes
        ])
        
        rel_pattern = "|".join(relation_types) if relation_types else ""
        
        cypher = f"""
        MATCH (n) WHERE {node_conditions}
        MATCH path=(n)-[r:{rel_pattern}*1..{depth}]-(m)
        RETURN path
        LIMIT 50
        """
        
        result = self.g.run(cypher).data()
        return result


if __name__ == "__main__":
    # 测试图谱检索
    print("=" * 60)
    print("图谱检索模块测试")
    print("=" * 60)
    
    retriever = GraphRetriever()
    
    # 测试1：菜品子图检索
    print("\n1. 菜品子图检索（宫保鸡丁）：")
    info = retriever.search_by_dish("宫保鸡丁", depth=1)
    print(f"   食材: {', '.join(info['ingredients'][:5])}")
    print(f"   调料: {', '.join(info['condiments'][:5])}")
    print(f"   标签: {', '.join(info['tags'])}")
    print(f"   口味: {', '.join(info['flavors'])}")
    
    # 测试2：食材检索
    print("\n2. 食材检索（鸡肉）：")
    dishes = retriever.search_by_ingredient("鸡肉", limit=5)
    for d in dishes:
        print(f"   - {d['dish']}")
    
    # 测试3：标签检索（场景标签）
    print("\n3. 标签检索（熬夜）：")
    dishes = retriever.search_by_tag("熬夜", limit=5)
    for d in dishes:
        print(f"   - {d['dish']}")
    
    # 测试4：相似菜品
    print("\n4. 相似菜品（番茄炒蛋）：")
    similar = retriever.find_similar_dishes("番茄炒蛋", limit=3)
    for dish, score, features in similar:
        print(f"   - {dish} (分数: {score}, 共同点: {', '.join(features[:3])})")
