# coding = utf-8
"""
用户个性化推荐系统 - 知识图谱模型设计

节点类型：
1. User（用户）
2. Dish（菜品）- 已有
3. Tag（标签）- 新增
4. Flavor（口味）- 新增
5. Scene（场景）- 新增

关系类型：
1. searched（用户搜索过的菜品）
2. cooked（用户做过的菜品）
3. liked（用户喜欢的菜品）
4. has_tag（菜品有标签）
5. has_flavor（菜品有口味）
6. suitable_for（菜品适合场景）
7. prefers_flavor（用户偏好口味）
8. prefers_tag（用户偏好标签）
9. similar_to（菜品相似）
"""

from py2neo import Graph, Node, Relationship
import json


class UserGraphModel:
    """用户图谱模型"""
    
    def __init__(self):
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
        
        # 标签分类
        self.tags = {
            "难度": ["简单", "中等", "困难", "新手友好", "需要技巧"],
            "时间": ["快手", "10分钟", "30分钟", "1小时", "费时"],
            "场合": ["家常", "宴客", "聚餐", "便当", "夜宵"],
            "健康": ["低脂", "低糖", "高蛋白", "素食", "清淡"],
            "特色": ["下饭", "下酒", "开胃", "暖身", "解腻"]
        }
        
        # 口味分类
        self.flavors = {
            "味道": ["酸", "甜", "苦", "辣", "咸", "鲜", "香"],
            "风格": ["酸甜", "麻辣", "香辣", "清淡", "浓郁", "鲜香"]
        }
        
        # 场景分类
        self.scenes = {
            "工作": ["加班", "熬夜", "工作日", "快速早餐", "便携午餐"],
            "休闲": ["周末", "朋友聚会", "家庭聚餐", "独自享用"],
            "健康": ["减肥", "健身", "养生", "病后调理"],
            "季节": ["春季", "夏季", "秋季", "冬季"],
            "心情": ["压力大", "疲劳", "想吃好的", "清淡养胃"]
        }
        
    def create_user_node(self, user_id, user_name, preferences=None):
        """创建用户节点"""
        user = Node("User", 
                   user_id=user_id, 
                   name=user_name,
                   preferences=json.dumps(preferences or {}, ensure_ascii=False))
        self.g.merge(user, "User", "user_id")
        return user
    
    def create_tag_nodes(self):
        """创建标签节点"""
        for category, tags in self.tags.items():
            for tag in tags:
                tag_node = Node("Tag", name=tag, category=category)
                self.g.merge(tag_node, "Tag", "name")
        print(f"创建标签节点完成")
    
    def create_flavor_nodes(self):
        """创建口味节点"""
        for category, flavors in self.flavors.items():
            for flavor in flavors:
                flavor_node = Node("Flavor", name=flavor, category=category)
                self.g.merge(flavor_node, "Flavor", "name")
        print(f"创建口味节点完成")
    
    def create_scene_nodes(self):
        """创建场景节点"""
        for category, scenes in self.scenes.items():
            for scene in scenes:
                scene_node = Node("Scene", name=scene, category=category)
                self.g.merge(scene_node, "Scene", "name")
        print(f"创建场景节点完成")
    
    def link_dish_tags(self, dish_name, tags):
        """关联菜品和标签"""
        dish = self.g.nodes.match("Dish", name=dish_name).first()
        if not dish:
            return
        
        for tag in tags:
            tag_node = self.g.nodes.match("Tag", name=tag).first()
            if tag_node:
                rel = Relationship(dish, "has_tag", tag_node)
                self.g.merge(rel)
    
    def link_dish_flavors(self, dish_name, flavors):
        """关联菜品和口味"""
        dish = self.g.nodes.match("Dish", name=dish_name).first()
        if not dish:
            return
        
        for flavor in flavors:
            flavor_node = self.g.nodes.match("Flavor", name=flavor).first()
            if flavor_node:
                rel = Relationship(dish, "has_flavor", flavor_node)
                self.g.merge(rel)
    
    def link_dish_scenes(self, dish_name, scenes):
        """关联菜品和场景"""
        dish = self.g.nodes.match("Dish", name=dish_name).first()
        if not dish:
            return
        
        for scene in scenes:
            scene_node = self.g.nodes.match("Scene", name=scene).first()
            if scene_node:
                rel = Relationship(dish, "suitable_for", scene_node)
                self.g.merge(rel)
    
    def record_user_search(self, user_id, dish_name):
        """记录用户搜索"""
        # 使用Cypher直接操作，更可靠
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:searched]->(d)
        ON CREATE SET r.count = 1
        ON MATCH SET r.count = COALESCE(r.count, 0) + 1
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name)
    
    def record_user_cooked(self, user_id, dish_name, rating=None):
        """记录用户做过的菜"""
        # 使用Cypher直接操作
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:cooked]->(d)
        SET r.rating = $rating
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name, rating=rating)
    
    def record_user_liked(self, user_id, dish_name):
        """记录用户喜欢的菜"""
        # 使用Cypher直接操作
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:liked]->(d)
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name)
    
    def calculate_dish_similarity(self):
        """计算菜品相似度（基于共同的食材、调料、口味）"""
        # 这个方法会比较耗时，建议离线计算
        cypher = """
        MATCH (d1:Dish)-[:need_ingredient]->(i:Ingredient)<-[:need_ingredient]-(d2:Dish)
        WHERE d1.name < d2.name
        WITH d1, d2, COUNT(i) as common_ingredients
        WHERE common_ingredients >= 2
        MERGE (d1)-[r:similar_to]-(d2)
        SET r.score = common_ingredients
        RETURN COUNT(r) as created
        """
        result = self.g.run(cypher).data()
        print(f"创建相似关系: {result[0]['created']}条")


# 示例：菜品标签映射
DISH_TAG_MAPPING = {
    "宫保鸡丁": {
        "tags": ["中等", "30分钟", "家常", "下饭"],
        "flavors": ["辣", "咸", "香辣"],
        "scenes": ["工作日", "家庭聚餐"]
    },
    "番茄炒蛋": {
        "tags": ["简单", "10分钟", "家常", "新手友好"],
        "flavors": ["酸", "甜", "酸甜"],
        "scenes": ["快速早餐", "工作日", "独自享用"]
    },
    "清蒸鲈鱼": {
        "tags": ["中等", "30分钟", "宴客", "清淡"],
        "flavors": ["鲜", "清淡"],
        "scenes": ["家庭聚餐", "养生"]
    },
    "麻婆豆腐": {
        "tags": ["简单", "30分钟", "家常", "下饭"],
        "flavors": ["辣", "麻辣", "浓郁"],
        "scenes": ["工作日", "想吃好的"]
    },
    "小龙虾": {
        "tags": ["困难", "1小时", "聚餐", "夜宵"],
        "flavors": ["辣", "香辣", "鲜"],
        "scenes": ["朋友聚会", "周末"]
    },
    "可乐鸡翅": {
        "tags": ["简单", "30分钟", "家常", "新手友好"],
        "flavors": ["甜", "咸", "浓郁"],
        "scenes": ["家庭聚餐", "独自享用"]
    },
    "红烧肉": {
        "tags": ["中等", "1小时", "宴客", "下饭"],
        "flavors": ["甜", "咸", "浓郁"],
        "scenes": ["家庭聚餐", "想吃好的"]
    },
    "凉拌黄瓜": {
        "tags": ["简单", "10分钟", "家常", "清淡"],
        "flavors": ["酸", "清淡", "鲜"],
        "scenes": ["快速早餐", "减肥", "夏季"]
    }
}


if __name__ == "__main__":
    model = UserGraphModel()
    
    print("=" * 60)
    print("开始构建用户个性化推荐图谱基础设施...")
    print("=" * 60)
    
    # 1. 创建标签、口味、场景节点（这些是静态的，只需创建一次）
    print("\n1. 创建标签节点...")
    model.create_tag_nodes()
    
    print("\n2. 创建口味节点...")
    model.create_flavor_nodes()
    
    print("\n3. 创建场景节点...")
    model.create_scene_nodes()
    
    # 2. 关联菜品和标签（这些是静态的，只需创建一次）
    print("\n4. 关联菜品标签...")
    for dish_name, attrs in DISH_TAG_MAPPING.items():
        model.link_dish_tags(dish_name, attrs.get("tags", []))
        model.link_dish_flavors(dish_name, attrs.get("flavors", []))
        model.link_dish_scenes(dish_name, attrs.get("scenes", []))
        print(f"   - {dish_name}")
    
    # 3. 计算菜品相似度（这是静态的，只需计算一次）
    print("\n5. 计算菜品相似度...")
    model.calculate_dish_similarity()
    
    print("\n" + "=" * 60)
    print("用户个性化推荐图谱基础设施构建完成！")
    print("=" * 60)
    print("\n提示：")
    print("- 用户节点会在用户首次登录时自动创建")
    print("- 用户行为会在使用系统时动态记录")
    print("- 不需要预先创建示例用户")
    print("\n使用示例：")
    print("  from user_graph_model import UserGraphModel")
    print("  model = UserGraphModel()")
    print("  model.create_user_node('user123', '用户名', {'dietary': '清淡'})")
    print("  model.record_user_search('user123', '番茄炒蛋')")
    print("=" * 60)
