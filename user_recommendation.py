# coding = utf-8
"""
用户个性化推荐引擎
"""

from py2neo import Graph
import json
from collections import defaultdict


class UserRecommendation:
    """用户推荐系统"""
    
    def __init__(self):
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
    
    def get_user_history(self, user_id):
        """获取用户历史记录"""
        cypher = """
        MATCH (u:User {user_id: $user_id})-[r]->(d:Dish)
        RETURN type(r) as action, d.name as dish, r.count as count, r.rating as rating
        ORDER BY r.count DESC, r.rating DESC
        """
        result = self.g.run(cypher, user_id=user_id).data()
        return result
    
    def recommend_by_history(self, user_id, limit=5):
        """
        基于历史记录推荐
        推荐用户搜索过但没做过的菜品
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})-[:searched]->(d:Dish)
        WHERE NOT (u)-[:cooked]->(d)
        WITH d, COUNT(*) as search_count
        ORDER BY search_count DESC
        LIMIT $limit
        RETURN d.name as dish, d.difficulty as difficulty, search_count
        """
        result = self.g.run(cypher, user_id=user_id, limit=limit).data()
        return result
    
    def recommend_by_scene(self, scene_name, limit=10):
        """
        基于场景推荐
        例如：熬夜、加班、减肥等
        """
        cypher = """
        MATCH (s:Scene {name: $scene})<-[:suitable_for]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_tag]->(t:Tag)
        WITH d, COLLECT(DISTINCT t.name) as tags
        RETURN d.name as dish, d.difficulty as difficulty, tags
        LIMIT $limit
        """
        result = self.g.run(cypher, scene=scene_name, limit=limit).data()
        return result
    
    def recommend_by_flavor(self, flavor_preference, limit=10):
        """
        基于口味偏好推荐
        例如：清淡、麻辣、酸甜等
        """
        cypher = """
        MATCH (f:Flavor {name: $flavor})<-[:has_flavor]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_tag]->(t:Tag)
        WITH d, COLLECT(DISTINCT t.name) as tags
        RETURN d.name as dish, d.difficulty as difficulty, tags
        LIMIT $limit
        """
        result = self.g.run(cypher, flavor=flavor_preference, limit=limit).data()
        return result
    
    def recommend_by_tag(self, tag_name, limit=10):
        """
        基于标签推荐
        例如：简单、快手、下饭等
        """
        cypher = """
        MATCH (t:Tag {name: $tag})<-[:has_tag]-(d:Dish)
        OPTIONAL MATCH (d)-[:has_flavor]->(f:Flavor)
        WITH d, COLLECT(DISTINCT f.name) as flavors
        RETURN d.name as dish, d.difficulty as difficulty, flavors
        LIMIT $limit
        """
        result = self.g.run(cypher, tag=tag_name, limit=limit).data()
        return result
    
    def recommend_similar_dishes(self, user_id, limit=5):
        """
        基于相似度推荐
        找出用户喜欢的菜品的相似菜品
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})-[:liked|cooked]->(d1:Dish)-[:similar_to]-(d2:Dish)
        WHERE NOT (u)-[:cooked]->(d2)
        WITH d2, d1, COUNT(DISTINCT d1) as similar_count
        OPTIONAL MATCH (d2)-[:has_flavor]->(f:Flavor)
        WITH d2, similar_count, COLLECT(DISTINCT f.name) as flavors
        ORDER BY similar_count DESC
        LIMIT $limit
        RETURN d2.name as dish, d2.difficulty as difficulty, flavors, similar_count
        """
        result = self.g.run(cypher, user_id=user_id, limit=limit).data()
        return result
    
    def get_similar_dishes_with_reason(self, user_id, limit=5):
        """
        获取相似菜品并返回原因
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})-[r:liked|cooked]->(d1:Dish)-[:similar_to]-(d2:Dish)
        WHERE NOT (u)-[:cooked]->(d2)
        WITH d1, d2, type(r) as action
        OPTIONAL MATCH (d1)-[:has_flavor]->(f:Flavor)<-[:has_flavor]-(d2)
        WITH d1, d2, action, COLLECT(DISTINCT f.name) as common_flavors
        OPTIONAL MATCH (d1)-[:need_ingredient]->(i:Ingredient)<-[:need_ingredient]-(d2)
        WITH d1, d2, action, common_flavors, COLLECT(DISTINCT i.name) as common_ingredients
        RETURN d1.name as source_dish, d2.name as recommended_dish, 
               action, common_flavors, common_ingredients
        LIMIT $limit
        """
        result = self.g.run(cypher, user_id=user_id, limit=limit).data()
        return result
    
    def analyze_user_preference(self, user_id):
        """
        分析用户偏好
        返回用户最喜欢的口味、标签、场景
        """
        # 分析口味偏好
        flavor_cypher = """
        MATCH (u:User {user_id: $user_id})-[:liked|cooked]->(d:Dish)-[:has_flavor]->(f:Flavor)
        WITH f.name as flavor, COUNT(*) as count
        ORDER BY count DESC
        LIMIT 3
        RETURN COLLECT(flavor) as top_flavors
        """
        
        # 分析标签偏好
        tag_cypher = """
        MATCH (u:User {user_id: $user_id})-[:liked|cooked]->(d:Dish)-[:has_tag]->(t:Tag)
        WITH t.name as tag, COUNT(*) as count
        ORDER BY count DESC
        LIMIT 3
        RETURN COLLECT(tag) as top_tags
        """
        
        flavors = self.g.run(flavor_cypher, user_id=user_id).data()
        tags = self.g.run(tag_cypher, user_id=user_id).data()
        
        return {
            "flavors": flavors[0]["top_flavors"] if flavors else [],
            "tags": tags[0]["top_tags"] if tags else []
        }
    
    def recommend_by_multiple_criteria(self, user_id, scene=None, flavor=None, tag=None, limit=10):
        """
        综合推荐：结合场景、口味、标签
        """
        conditions = []
        params = {"user_id": user_id, "limit": limit}
        
        if scene:
            conditions.append("(d)-[:suitable_for]->(s:Scene {name: $scene})")
            params["scene"] = scene
        
        if flavor:
            conditions.append("(d)-[:has_flavor]->(f:Flavor {name: $flavor})")
            params["flavor"] = flavor
        
        if tag:
            conditions.append("(d)-[:has_tag]->(t:Tag {name: $tag})")
            params["tag"] = tag
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cypher = f"""
        MATCH (u:User {{user_id: $user_id}})
        MATCH (d:Dish)
        WHERE NOT (u)-[:cooked]->(d) AND {where_clause}
        OPTIONAL MATCH (d)-[:has_tag]->(tag:Tag)
        OPTIONAL MATCH (d)-[:has_flavor]->(flv:Flavor)
        WITH d, COLLECT(DISTINCT tag.name) as tags, COLLECT(DISTINCT flv.name) as flavors
        RETURN d.name as dish, d.difficulty as difficulty, tags, flavors
        LIMIT $limit
        """
        
        result = self.g.run(cypher, **params).data()
        return result


if __name__ == "__main__":
    rec = UserRecommendation()
    
    print("=" * 60)
    print("测试用户推荐系统")
    print("=" * 60)
    
    user_id = "user001"
    
    # 1. 获取用户历史
    print(f"\n1. 用户 {user_id} 的历史记录：")
    history = rec.get_user_history(user_id)
    for h in history:
        print(f"   - {h['action']}: {h['dish']}")
    
    # 2. 基于历史推荐
    print(f"\n2. 基于历史推荐（搜索过但没做过）：")
    recs = rec.recommend_by_history(user_id)
    for r in recs:
        print(f"   - {r['dish']} (难度: {r['difficulty']})")
    
    # 3. 基于场景推荐
    print(f"\n3. 基于场景推荐（加班/熬夜）：")
    scene_recs = rec.recommend_by_scene("加班", limit=5)
    for r in scene_recs:
        print(f"   - {r['dish']} (标签: {', '.join(r['tags'])})")
    
    # 4. 基于口味推荐
    print(f"\n4. 基于口味推荐（清淡）：")
    flavor_recs = rec.recommend_by_flavor("清淡", limit=5)
    for r in flavor_recs:
        print(f"   - {r['dish']} (标签: {', '.join(r['tags'])})")
    
    # 5. 基于相似度推荐
    print(f"\n5. 基于相似度推荐：")
    similar_recs = rec.recommend_similar_dishes(user_id)
    for r in similar_recs:
        print(f"   - {r['dish']} (口味: {', '.join(r['flavors'])})")
    
    # 6. 获取推荐原因
    print(f"\n6. 相似菜品推荐（带原因）：")
    reasons = rec.get_similar_dishes_with_reason(user_id)
    for r in reasons:
        print(f"   - 因为你{r['action']}过 {r['source_dish']}")
        print(f"     推荐: {r['recommended_dish']}")
        print(f"     共同口味: {', '.join(r['common_flavors'])}")
        print(f"     共同食材: {', '.join(r['common_ingredients'][:3])}")
    
    # 7. 分析用户偏好
    print(f"\n7. 用户偏好分析：")
    prefs = rec.analyze_user_preference(user_id)
    print(f"   - 喜欢的口味: {', '.join(prefs['flavors'])}")
    print(f"   - 喜欢的标签: {', '.join(prefs['tags'])}")
    
    print("\n" + "=" * 60)
