# coding = utf-8
"""
高级推荐模块
实现基于用户历史的智能推荐、场景标签检索、做菜助手等功能
"""

from py2neo import Graph
from typing import List, Dict, Tuple
from collections import defaultdict
import json


class AdvancedRecommender:
    """高级推荐系统"""
    
    def __init__(self):
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
        
        # 场景标签映射
        self.scene_tags = {
            "熬夜加班": ["夜宵", "快手", "简单", "提神"],
            "零碎时间": ["快手", "简单", "10分钟"],
            "便携午餐": ["便当", "快手", "易保存"],
            "周末聚餐": ["宴客", "硬菜", "下酒"],
            "健身减脂": ["低脂", "健康", "高蛋白"],
            "儿童营养": ["营养", "易消化", "补钙"],
            "老人养生": ["清淡", "易消化", "养生"],
            "约会浪漫": ["精致", "颜值", "西餐"],
        }
    
    def recommend_unexplored_dishes(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        功能1: 推荐用户未尝试但可能喜欢的菜谱
        
        基于：
        - 用户历史偏好（口味、标签）
        - 相似用户的选择
        - 排除已做过的菜
        
        Args:
            user_id: 用户ID
            limit: 推荐数量
        
        Returns:
            List[Dict]: 推荐菜品列表
        """
        cypher = """
        // 1. 找出用户喜欢的口味和标签
        MATCH (u:User {user_id: $user_id})-[:liked|cooked]->(d1:Dish)
        OPTIONAL MATCH (d1)-[:has_flavor]->(f:Flavor)
        OPTIONAL MATCH (d1)-[:has_tag]->(t:Tag)
        WITH u, COLLECT(DISTINCT f.name) as user_flavors, COLLECT(DISTINCT t.name) as user_tags
        
        // 2. 找出符合用户偏好但未做过的菜
        MATCH (d2:Dish)
        WHERE NOT (u)-[:cooked]->(d2)
        
        // 3. 计算口味匹配度
        OPTIONAL MATCH (d2)-[:has_flavor]->(f2:Flavor)
        WHERE f2.name IN user_flavors
        WITH d2, user_flavors, user_tags, COUNT(DISTINCT f2) as flavor_match
        
        // 4. 计算标签匹配度
        OPTIONAL MATCH (d2)-[:has_tag]->(t2:Tag)
        WHERE t2.name IN user_tags
        WITH d2, flavor_match, COUNT(DISTINCT t2) as tag_match
        
        // 5. 获取菜品详细信息
        OPTIONAL MATCH (d2)-[:has_flavor]->(f:Flavor)
        WITH d2, flavor_match, tag_match, COLLECT(DISTINCT f.name) as flavors
        
        OPTIONAL MATCH (d2)-[:has_tag]->(t:Tag)
        WITH d2, flavor_match, tag_match, flavors, COLLECT(DISTINCT t.name) as tags
        
        // 6. 计算推荐分数并排序
        WITH d2, flavors, tags, d2.difficulty AS difficulty,
            flavor_match, tag_match,
            (flavor_match * 2 + tag_match) AS score
        WHERE score > 0

        WITH d2, flavors, tags, difficulty, flavor_match, tag_match, score
        ORDER BY score DESC, difficulty ASC
        LIMIT $limit

        
        RETURN d2.name as dish, flavors, tags, difficulty, score,
               flavor_match, tag_match
        """
        
        result = self.g.run(cypher, user_id=user_id, limit=limit).data()
        
        # 添加推荐理由
        for item in result:
            reasons = []
            if item['flavor_match'] > 0:
                reasons.append(f"口味匹配({item['flavor_match']}个)")
            if item['tag_match'] > 0:
                reasons.append(f"标签匹配({item['tag_match']}个)")
            item['reason'] = '; '.join(reasons) if reasons else "可能喜欢"
        
        return result
    
    def search_by_scene_tags(self, scene_query: str, limit: int = 5) -> List[Dict]:
        """
        功能2: 基于场景标签的智能检索
        
        Args:
            scene_query: 场景描述（如"我今晚要熬夜加班"）
            limit: 返回数量
        
        Returns:
            List[Dict]: 匹配的菜品列表
        """
        # 识别场景关键词
        matched_tags = []
        for scene, tags in self.scene_tags.items():
            if scene in scene_query:
                matched_tags.extend(tags)
                break
        
        # 如果没有匹配到预定义场景，尝试从查询中提取关键词
        if not matched_tags:
            keywords = ["快手", "简单", "夜宵", "便当", "宴客", "健康", "清淡"]
            matched_tags = [kw for kw in keywords if kw in scene_query]
        
        if not matched_tags:
            return []
        
        # 查询图谱
        cypher = """
        MATCH (d:Dish)-[:has_tag]->(t:Tag)
        WHERE t.name IN $tags
        WITH d, COUNT(DISTINCT t) as tag_count
        
        OPTIONAL MATCH (d)-[:has_flavor]->(f:Flavor)
        OPTIONAL MATCH (d)-[:has_tag]->(t2:Tag)
        WITH d, tag_count, 
             COLLECT(DISTINCT f.name) as flavors,
             COLLECT(DISTINCT t2.name) as tags,
             d.difficulty as difficulty
        
        WITH d, flavors, tags, difficulty, tag_count
        ORDER BY tag_count DESC, difficulty ASC
        LIMIT $limit
        RETURN d.name AS dish, flavors, tags, difficulty, tag_count

        """
        
        result = self.g.run(cypher, tags=matched_tags, limit=limit).data()
        
        # 添加推荐理由
        for item in result:
            item['reason'] = f"适合场景: {', '.join(matched_tags[:3])}"
            item['matched_tags'] = matched_tags
        
        return result
    
    def get_cooking_guidance(self, user_id: str, dish_name: str, current_step: str = None) -> Dict:
        """
        功能3: 做菜助手 - 引导用户一步步操作
        
        Args:
            user_id: 用户ID
            dish_name: 菜品名称
            current_step: 当前步骤描述（如"我切好了"）
        
        Returns:
            Dict: 包含下一步指导的信息
        """
        # 获取菜品的完整步骤
        cypher = """
        MATCH (d:Dish {name: $dish_name})
        RETURN d.steps as steps, d.tips as tips
        """
        
        result = self.g.run(cypher, dish_name=dish_name).data()
        
        if not result or not result[0].get('steps'):
            return {
                'dish': dish_name,
                'error': '未找到该菜品的制作步骤',
                'suggestion': '请尝试搜索其他菜品'
            }
        
        steps_data = result[0]['steps']
        tips_data = result[0].get('tips', '')
        
        # 解析步骤（新格式是JSON）
        import json
        try:
            if isinstance(steps_data, str):
                steps_list = json.loads(steps_data)
            else:
                steps_list = steps_data
            
            # 提取步骤描述
            if isinstance(steps_list, list) and len(steps_list) > 0:
                if isinstance(steps_list[0], dict):
                    # 新格式：[{"step_number": 1, "description": "xxx", ...}, ...]
                    steps = [f"{s.get('step_number', i+1)}. {s.get('description', '')}" 
                            for i, s in enumerate(steps_list)]
                else:
                    # 旧格式：["步骤1", "步骤2", ...]
                    steps = [f"{i+1}. {s}" for i, s in enumerate(steps_list)]
            else:
                steps = []
            
            # 解析tips
            if isinstance(tips_data, str):
                tips_list = json.loads(tips_data) if tips_data else []
            else:
                tips_list = tips_data
            tips = '\n'.join(tips_list) if isinstance(tips_list, list) else str(tips_list)
        except:
            # 降级处理：作为纯文本
            import re
            steps = re.split(r'\n(?=\d+\.)', str(steps_data))
            steps = [s.strip() for s in steps if s.strip()]
            tips = str(tips_data)
        
        # 根据当前步骤描述判断进度
        current_step_index = 0
        if current_step:
            # 简单的关键词匹配
            keywords = {
                "切好": 0,
                "准备好": 0,
                "热锅": 1,
                "炒": 2,
                "调味": -2,
                "出锅": -1,
            }
            for keyword, offset in keywords.items():
                if keyword in current_step:
                    if offset < 0:
                        current_step_index = len(steps) + offset
                    else:
                        current_step_index = offset
                    break
        
        # 获取下一步
        next_step_index = current_step_index + 1
        if next_step_index >= len(steps):
            return {
                'dish': dish_name,
                'current_progress': f"{len(steps)}/{len(steps)}",
                'message': '🎉 恭喜！菜品已完成！',
                'tips': tips,
                'completed': True
            }
        
        return {
            'dish': dish_name,
            'current_step': current_step_index + 1,
            'total_steps': len(steps),
            'current_progress': f"{next_step_index}/{len(steps)}",
            'next_step': steps[next_step_index],
            'all_steps': steps,
            'tips': tips,
            'completed': False
        }
    
    def recommend_similar_with_explanation(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        功能4+5: 智能菜谱推荐 + 推荐解释
        
        基于用户历史找出相似菜谱，并解释推荐理由
        
        Args:
            user_id: 用户ID
            limit: 推荐数量
        
        Returns:
            List[Dict]: 包含推荐理由的菜品列表
        """
        cypher = """
        // 1. 找出用户做过的菜
        MATCH (u:User {user_id: $user_id})-[r:cooked|liked]->(d1:Dish)
        WITH u, d1, type(r) as action, r.rating as rating
        ORDER BY rating DESC, r.cooked_at DESC
        LIMIT 5
        
        // 2. 找出相似的菜（通过口味、食材、标签）
        MATCH (d1)-[:has_flavor]->(f:Flavor)<-[:has_flavor]-(d2:Dish)
        WHERE NOT (u)-[:cooked]->(d2)  // 排除已做过的
        WITH u, d1, d2, action, COLLECT(DISTINCT f.name) as common_flavors
        
        OPTIONAL MATCH (d1)-[:need_ingredient]->(i:Ingredient)<-[:need_ingredient]-(d2)
        WITH u, d1, d2, action, common_flavors, COLLECT(DISTINCT i.name) as common_ingredients
        
        OPTIONAL MATCH (d1)-[:has_tag]->(t:Tag)<-[:has_tag]-(d2)
        WITH u, d1, d2, action, common_flavors, common_ingredients, COLLECT(DISTINCT t.name) as common_tags
        
        // 3. 获取推荐菜品的详细信息
        OPTIONAL MATCH (d2)-[:has_flavor]->(f2:Flavor)
        WITH d1, d2, action, common_flavors, common_ingredients, common_tags,
             COLLECT(DISTINCT f2.name) as d2_flavors
        
        OPTIONAL MATCH (d2)-[:has_tag]->(t2:Tag)
        WITH d1, d2, action, common_flavors, common_ingredients, common_tags,
             d2_flavors, COLLECT(DISTINCT t2.name) as d2_tags,
             d2.difficulty as difficulty
        
        // 4. 计算相似度分数
        WITH d1, d2, action, common_flavors, common_ingredients, common_tags,
            d2_flavors, d2_tags, difficulty,
            (size(coalesce(common_flavors, [])) * 3 +
            size(coalesce(common_ingredients, [])) * 2 +
            size(coalesce(common_tags, []))) AS similarity_score
        WHERE similarity_score > 0

        WITH d1, d2, action, common_flavors, common_ingredients, common_tags,
            d2_flavors, d2_tags, difficulty, similarity_score
        ORDER BY similarity_score DESC, difficulty ASC
        LIMIT $limit

        
        RETURN d1.name as source_dish,
               d2.name as recommended_dish,
               action,
               common_flavors,
               common_ingredients,
               common_tags,
               d2_flavors,
               d2_tags,
               difficulty,
               similarity_score
        """
        
        result = self.g.run(cypher, user_id=user_id, limit=limit).data()
        
        # 生成详细的推荐解释
        for item in result:
            explanations = []
            
            # 基础推荐理由
            action_text = "做过" if item['action'] == 'cooked' else "喜欢"
            explanations.append(f"因为你之前{action_text}【{item['source_dish']}】")
            
            # 口味相似
            if item['common_flavors']:
                flavors = ', '.join(item['common_flavors'][:3])
                explanations.append(f"这道菜有相似的{flavors}风味")
            
            # 食材相似
            if item['common_ingredients']:
                ingredients = ', '.join(item['common_ingredients'][:3])
                explanations.append(f"使用了相同的{ingredients}")
            
            # 标签相似
            if item['common_tags']:
                tags = ', '.join(item['common_tags'][:2])
                explanations.append(f"同样是{tags}类型")
            
            # 难度对比
            if item['difficulty']:
                if item['difficulty'] <= 2:
                    explanations.append("而且更简单易做")
                elif item['difficulty'] >= 4:
                    explanations.append("适合进阶挑战")
            
            item['explanation'] = '，'.join(explanations)
            item['short_reason'] = f"与【{item['source_dish']}】相似"
        
        return result
    
    def get_recommendation_explanation(self, user_id: str, dish_name: str) -> str:
        """
        功能5: 为特定推荐生成解释
        
        Args:
            user_id: 用户ID
            dish_name: 推荐的菜品名
        
        Returns:
            str: 推荐解释
        """
        cypher = """
        // 找出用户历史与推荐菜品的关联
        MATCH (u:User {user_id: $user_id})-[:cooked|liked]->(d1:Dish)
        MATCH (d2:Dish {name: $dish_name})
        
        // 找出共同的口味
        OPTIONAL MATCH (d1)-[:has_flavor]->(f:Flavor)<-[:has_flavor]-(d2)
        WITH u, d1, d2, COLLECT(DISTINCT f.name) as common_flavors
        
        // 找出共同的食材
        OPTIONAL MATCH (d1)-[:need_ingredient]->(i:Ingredient)<-[:need_ingredient]-(d2)
        WITH u, d1, d2, common_flavors, COLLECT(DISTINCT i.name) as common_ingredients
        
        // 找出共同的标签
        OPTIONAL MATCH (d1)-[:has_tag]->(t:Tag)<-[:has_tag]-(d2)
        WITH d1, d2, common_flavors, common_ingredients, COLLECT(DISTINCT t.name) as common_tags
        
        WHERE size(coalesce(common_flavors, [])) > 0
            OR size(coalesce(common_ingredients, [])) > 0
            OR size(coalesce(common_tags, [])) > 0

        
        RETURN d1.name as source_dish,
               common_flavors,
               common_ingredients,
               common_tags
        ORDER BY SIZE(common_flavors) DESC
        LIMIT 1
        """
        
        result = self.g.run(cypher, user_id=user_id, dish_name=dish_name).data()
        
        if not result:
            return f"推荐【{dish_name}】给您尝试"
        
        item = result[0]
        explanations = [f"因为你之前做过【{item['source_dish']}】"]
        
        if item['common_flavors']:
            flavors = ', '.join(item['common_flavors'][:2])
            explanations.append(f"这道【{dish_name}】有相似的{flavors}风味")
        
        if item['common_ingredients']:
            ingredients = ', '.join(item['common_ingredients'][:2])
            explanations.append(f"使用了相同的{ingredients}")
        
        if item['common_tags']:
            tags = ', '.join(item['common_tags'][:2])
            explanations.append(f"同样是{tags}类型")
        
        return '，'.join(explanations)


if __name__ == '__main__':
    # 测试
    recommender = AdvancedRecommender()
    
    # 测试1: 未尝试推荐
    print("\n=== 测试1: 推荐未尝试的菜 ===")
    result = recommender.recommend_unexplored_dishes("alice", limit=3)
    for item in result:
        print(f"- {item['dish']}: {item['reason']}")
    
    # 测试2: 场景标签检索
    print("\n=== 测试2: 场景标签检索 ===")
    result = recommender.search_by_scene_tags("我今晚要熬夜加班", limit=3)
    for item in result:
        print(f"- {item['dish']}: {item['reason']}")
    
    # 测试3: 做菜助手
    print("\n=== 测试3: 做菜助手 ===")
    result = recommender.get_cooking_guidance("alice", "宫保鸡丁", "我切好了")
    print(f"进度: {result.get('current_progress')}")
    print(f"下一步: {result.get('next_step')}")
    
    # 测试4+5: 智能推荐+解释
    print("\n=== 测试4+5: 智能推荐+解释 ===")
    result = recommender.recommend_similar_with_explanation("alice", limit=3)
    for item in result:
        print(f"- {item['recommended_dish']}")
        print(f"  {item['explanation']}")
