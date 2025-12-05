# coding = utf-8
"""
子图查询统一API
为前端SubgraphViewer组件提供统一的子图查询接口
"""

from graph_retriever import GraphRetriever
from typing import Dict, List, Any


class SubgraphAPI:
    """子图查询统一API"""
    
    def __init__(self):
        self.retriever = GraphRetriever()
    
    def query_subgraph(self, subgraph_type: str, entity: str, depth: int = 1) -> Dict[str, Any]:
        """
        统一子图查询接口
        
        Args:
            subgraph_type: 子图类型 (Dish/Ingredient/Tag/Flavor/Similar/UserPreference/MultiHop)
            entity: 实体名称（根据类型不同而不同）
            depth: 查询深度（默认1）
        
        Returns:
            Dict: 包含 nodes 和 edges 的图数据
        """
        try:
            if subgraph_type == "Dish":
                return self._query_dish_subgraph(entity, depth)
            elif subgraph_type == "Ingredient":
                return self._query_ingredient_subgraph(entity, depth)
            elif subgraph_type == "Tag":
                return self._query_tag_subgraph(entity, depth)
            elif subgraph_type == "Flavor":
                return self._query_flavor_subgraph(entity, depth)
            elif subgraph_type == "Similar":
                return self._query_similar_subgraph(entity, depth)
            elif subgraph_type == "UserPreference":
                return self._query_user_preference_subgraph(entity, depth)
            elif subgraph_type == "MultiHop":
                return self._query_multihop_subgraph(entity, depth)
            else:
                return {"error": f"未知的子图类型: {subgraph_type}", "nodes": [], "edges": []}
        except Exception as e:
            return {"error": str(e), "nodes": [], "edges": []}
    
    def _query_dish_subgraph(self, dish_name: str, depth: int) -> Dict[str, Any]:
        """查询菜品子图"""
        info = self.retriever.search_by_dish(dish_name, depth)
        
        nodes = []
        edges = []
        node_id_map = {}
        
        # 添加中心菜品节点
        dish_id = f"dish_{dish_name}"
        nodes.append({
            "id": dish_id,
            "label": dish_name,
            "type": "Dish",
            "group": "dish"
        })
        node_id_map[dish_name] = dish_id
        
        # 添加食材节点和边
        for i, ingredient in enumerate(info.get('ingredients', [])):
            ing_id = f"ingredient_{i}"
            nodes.append({
                "id": ing_id,
                "label": ingredient,
                "type": "Ingredient",
                "group": "ingredient"
            })
            edges.append({
                "from": dish_id,
                "to": ing_id,
                "label": "需要食材"
            })
        
        # 添加调料节点和边
        for i, condiment in enumerate(info.get('condiments', [])):
            cond_id = f"condiment_{i}"
            nodes.append({
                "id": cond_id,
                "label": condiment,
                "type": "Condiment",
                "group": "condiment"
            })
            edges.append({
                "from": dish_id,
                "to": cond_id,
                "label": "需要调料"
            })
        
        # 添加标签节点和边
        for i, tag in enumerate(info.get('tags', [])):
            tag_id = f"tag_{i}"
            nodes.append({
                "id": tag_id,
                "label": tag,
                "type": "Tag",
                "group": "tag"
            })
            edges.append({
                "from": dish_id,
                "to": tag_id,
                "label": "标签"
            })
        
        # 添加口味节点和边
        for i, flavor in enumerate(info.get('flavors', [])):
            flavor_id = f"flavor_{i}"
            nodes.append({
                "id": flavor_id,
                "label": flavor,
                "type": "Flavor",
                "group": "flavor"
            })
            edges.append({
                "from": dish_id,
                "to": flavor_id,
                "label": "口味"
            })
        
        # 添加相似菜品节点和边
        for i, similar in enumerate(info.get('similar_dishes', [])):
            similar_id = f"similar_{i}"
            nodes.append({
                "id": similar_id,
                "label": similar,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": dish_id,
                "to": similar_id,
                "label": "相似"
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_ingredient_subgraph(self, ingredient_name: str, depth: int) -> Dict[str, Any]:
        """查询食材子图"""
        dishes = self.retriever.search_by_ingredient(ingredient_name, limit=15)
        
        nodes = []
        edges = []
        
        # 添加中心食材节点
        ing_id = f"ingredient_{ingredient_name}"
        nodes.append({
            "id": ing_id,
            "label": ingredient_name,
            "type": "Ingredient",
            "group": "ingredient"
        })
        
        # 添加相关菜品节点和边
        for i, dish_info in enumerate(dishes):
            dish_name = dish_info.get('dish')
            dish_id = f"dish_{i}"
            nodes.append({
                "id": dish_id,
                "label": dish_name,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": ing_id,
                "to": dish_id,
                "label": "可做"
            })
            
            # 添加菜品的标签
            for j, tag in enumerate(dish_info.get('tags', [])[:3]):
                tag_id = f"tag_{i}_{j}"
                nodes.append({
                    "id": tag_id,
                    "label": tag,
                    "type": "Tag",
                    "group": "tag"
                })
                edges.append({
                    "from": dish_id,
                    "to": tag_id,
                    "label": "标签"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_tag_subgraph(self, tag_name: str, depth: int) -> Dict[str, Any]:
        """查询标签子图"""
        dishes = self.retriever.search_by_tag(tag_name, limit=15)
        
        nodes = []
        edges = []
        
        # 添加中心标签节点
        tag_id = f"tag_{tag_name}"
        nodes.append({
            "id": tag_id,
            "label": tag_name,
            "type": "Tag",
            "group": "tag"
        })
        
        # 添加相关菜品节点和边
        for i, dish_info in enumerate(dishes):
            dish_name = dish_info.get('dish')
            dish_id = f"dish_{i}"
            nodes.append({
                "id": dish_id,
                "label": dish_name,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": tag_id,
                "to": dish_id,
                "label": "包含"
            })
            
            # 添加菜品的口味
            for j, flavor in enumerate(dish_info.get('flavors', [])[:2]):
                flavor_id = f"flavor_{i}_{j}"
                nodes.append({
                    "id": flavor_id,
                    "label": flavor,
                    "type": "Flavor",
                    "group": "flavor"
                })
                edges.append({
                    "from": dish_id,
                    "to": flavor_id,
                    "label": "口味"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_flavor_subgraph(self, flavor_name: str, depth: int) -> Dict[str, Any]:
        """查询口味子图"""
        dishes = self.retriever.search_by_flavor(flavor_name, limit=15)
        
        nodes = []
        edges = []
        
        # 添加中心口味节点
        flavor_id = f"flavor_{flavor_name}"
        nodes.append({
            "id": flavor_id,
            "label": flavor_name,
            "type": "Flavor",
            "group": "flavor"
        })
        
        # 添加相关菜品节点和边
        for i, dish_info in enumerate(dishes):
            dish_name = dish_info.get('dish')
            dish_id = f"dish_{i}"
            nodes.append({
                "id": dish_id,
                "label": dish_name,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": flavor_id,
                "to": dish_id,
                "label": "具有"
            })
            
            # 添加菜品的标签
            for j, tag in enumerate(dish_info.get('tags', [])[:2]):
                tag_id = f"tag_{i}_{j}"
                nodes.append({
                    "id": tag_id,
                    "label": tag,
                    "type": "Tag",
                    "group": "tag"
                })
                edges.append({
                    "from": dish_id,
                    "to": tag_id,
                    "label": "标签"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_similar_subgraph(self, dish_name: str, depth: int) -> Dict[str, Any]:
        """查询相似菜品子图"""
        similar_dishes = self.retriever.find_similar_dishes(dish_name, limit=10)
        
        nodes = []
        edges = []
        
        # 添加中心菜品节点
        dish_id = f"dish_{dish_name}"
        nodes.append({
            "id": dish_id,
            "label": dish_name,
            "type": "Dish",
            "group": "dish"
        })
        
        # 添加相似菜品节点和边
        for i, (similar_dish, score, features) in enumerate(similar_dishes):
            similar_id = f"similar_{i}"
            nodes.append({
                "id": similar_id,
                "label": similar_dish,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": dish_id,
                "to": similar_id,
                "label": f"相似度:{score}"
            })
            
            # 添加共同特征节点
            for j, feature in enumerate(features[:3]):
                feature_id = f"feature_{i}_{j}"
                nodes.append({
                    "id": feature_id,
                    "label": feature,
                    "type": "Feature",
                    "group": "feature"
                })
                edges.append({
                    "from": similar_id,
                    "to": feature_id,
                    "label": "共同点"
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_user_preference_subgraph(self, user_id: str, depth: int) -> Dict[str, Any]:
        """查询用户偏好子图"""
        user_data = self.retriever.get_user_preference_dishes(user_id, limit=10)
        
        nodes = []
        edges = []
        
        # 添加中心用户节点
        user_node_id = f"user_{user_id}"
        nodes.append({
            "id": user_node_id,
            "label": user_id,
            "type": "User",
            "group": "user"
        })
        
        # 添加用户历史菜品
        history = user_data.get('history', [])
        for i, record in enumerate(history[:10]):
            dish_name = record.get('dish')
            action = record.get('action', 'unknown')
            dish_id = f"dish_{i}"
            nodes.append({
                "id": dish_id,
                "label": dish_name,
                "type": "Dish",
                "group": "dish"
            })
            edges.append({
                "from": user_node_id,
                "to": dish_id,
                "label": action
            })
        
        # 添加用户偏好（口味、标签）
        preferences = user_data.get('preferences', {})
        
        # 添加口味偏好
        for i, flavor in enumerate(preferences.get('flavors', [])[:5]):
            flavor_id = f"pref_flavor_{i}"
            nodes.append({
                "id": flavor_id,
                "label": flavor,
                "type": "Flavor",
                "group": "flavor"
            })
            edges.append({
                "from": user_node_id,
                "to": flavor_id,
                "label": "喜欢口味"
            })
        
        # 添加标签偏好
        for i, tag in enumerate(preferences.get('tags', [])[:5]):
            tag_id = f"pref_tag_{i}"
            nodes.append({
                "id": tag_id,
                "label": tag,
                "type": "Tag",
                "group": "tag"
            })
            edges.append({
                "from": user_node_id,
                "to": tag_id,
                "label": "偏好标签"
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def _query_multihop_subgraph(self, entity_description: str, depth: int) -> Dict[str, Any]:
        """查询多跳子图（简化版）"""
        # 简化实现：尝试将输入解析为菜品名，然后进行多跳查询
        # 实际应用中可以使用NLP解析entity_description
        
        # 默认尝试作为菜品查询
        try:
            info = self.retriever.search_by_dish(entity_description, depth=min(depth, 2))
            return self._query_dish_subgraph(entity_description, depth)
        except:
            return {"error": "无法解析多跳查询", "nodes": [], "edges": []}


if __name__ == "__main__":
    # 测试子图API
    api = SubgraphAPI()
    
    print("测试1: 菜品子图")
    result = api.query_subgraph("Dish", "宫保鸡丁", depth=1)
    print(f"  节点数: {len(result['nodes'])}, 边数: {len(result['edges'])}")
    
    print("\n测试2: 食材子图")
    result = api.query_subgraph("Ingredient", "鸡肉", depth=1)
    print(f"  节点数: {len(result['nodes'])}, 边数: {len(result['edges'])}")
    
    print("\n测试3: 标签子图")
    result = api.query_subgraph("Tag", "快手菜", depth=1)
    print(f"  节点数: {len(result['nodes'])}, 边数: {len(result['edges'])}")
