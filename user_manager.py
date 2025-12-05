# coding = utf-8
"""
用户管理模块
动态创建和管理用户节点
"""

from py2neo import Graph, Node
import json
from datetime import datetime


class UserManager:
    """用户管理器 - 动态管理用户节点"""
    
    def __init__(self):
        self.g = Graph("bolt://127.0.0.1:7687", auth=("neo4j", "kurisu810975"))
        self.current_user = None
    
    def login_or_create_user(self, user_id, user_name=None, preferences=None):
        """
        用户登录或创建
        如果用户不存在，自动创建；如果存在，返回用户信息
        
        Args:
            user_id: 用户ID（必需）
            user_name: 用户名（可选，默认为user_id）
            preferences: 用户偏好（可选）
        
        Returns:
            Dict: 用户信息
        """
        # 检查用户是否存在
        user = self.g.nodes.match("User", user_id=user_id).first()
        
        if user:
            # 用户已存在
            print(f"欢迎回来，{user['name']}！")
            self.current_user = user_id
            
            # 获取用户统计
            stats = self.get_user_stats(user_id)
            
            return {
                'user_id': user_id,
                'name': user['name'],
                'preferences': json.loads(user.get('preferences', '{}')),
                'created_at': user.get('created_at'),
                'stats': stats,
                'is_new': False
            }
        else:
            # 创建新用户
            if not user_name:
                user_name = f"用户{user_id}"
            
            user = Node("User",
                       user_id=user_id,
                       name=user_name,
                       preferences=json.dumps(preferences or {}, ensure_ascii=False),
                       created_at=datetime.now().isoformat())
            
            self.g.create(user)
            self.current_user = user_id
            
            print(f"欢迎新用户：{user_name}！")
            
            return {
                'user_id': user_id,
                'name': user_name,
                'preferences': preferences or {},
                'created_at': user['created_at'],
                'stats': {'searched': 0, 'cooked': 0, 'liked': 0},
                'is_new': True
            }
    
    def get_user_stats(self, user_id):
        """
        获取用户统计信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 统计信息
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[s:searched]->()
        OPTIONAL MATCH (u)-[c:cooked]->()
        OPTIONAL MATCH (u)-[l:liked]->()
        RETURN 
            COUNT(DISTINCT s) as searched_count,
            COUNT(DISTINCT c) as cooked_count,
            COUNT(DISTINCT l) as liked_count,
            SUM(s.count) as total_searches
        """
        
        result = self.g.run(cypher, user_id=user_id).data()
        
        if result:
            data = result[0]
            return {
                'searched': data['searched_count'] or 0,
                'cooked': data['cooked_count'] or 0,
                'liked': data['liked_count'] or 0,
                'total_searches': data['total_searches'] or 0
            }
        
        return {'searched': 0, 'cooked': 0, 'liked': 0, 'total_searches': 0}
    
    def update_user_preferences(self, user_id, preferences):
        """
        更新用户偏好
        
        Args:
            user_id: 用户ID
            preferences: 新的偏好设置
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})
        SET u.preferences = $preferences
        """
        
        self.g.run(cypher, 
                  user_id=user_id, 
                  preferences=json.dumps(preferences, ensure_ascii=False))
        
        print(f"用户 {user_id} 的偏好已更新")
    
    def record_search(self, user_id, dish_name):
        """记录用户搜索"""
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:searched]->(d)
        ON CREATE SET r.count = 1, r.last_time = datetime()
        ON MATCH SET r.count = COALESCE(r.count, 0) + 1, r.last_time = datetime()
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name)
    
    def record_cooked(self, user_id, dish_name, rating=None):
        """记录用户做过的菜"""
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:cooked]->(d)
        SET r.rating = $rating, r.cooked_at = datetime()
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name, rating=rating)
        print(f"已记录：你做过【{dish_name}】")
    
    def record_liked(self, user_id, dish_name):
        """记录用户喜欢的菜"""
        cypher = """
        MATCH (u:User {user_id: $user_id}), (d:Dish {name: $dish_name})
        MERGE (u)-[r:liked]->(d)
        SET r.liked_at = datetime()
        """
        self.g.run(cypher, user_id=user_id, dish_name=dish_name)
        print(f"已记录：你喜欢【{dish_name}】")
    
    def get_user_history(self, user_id, limit=10):
        """
        获取用户历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            Dict: 用户历史
        """
        # 搜索历史
        search_cypher = """
        MATCH (u:User {user_id: $user_id})-[r:searched]->(d:Dish)
        RETURN d.name as dish, r.count as count, r.last_time as last_time
        ORDER BY r.count DESC, r.last_time DESC
        LIMIT $limit
        """
        
        # 做过的菜
        cooked_cypher = """
        MATCH (u:User {user_id: $user_id})-[r:cooked]->(d:Dish)
        RETURN d.name as dish, r.rating as rating, r.cooked_at as cooked_at
        ORDER BY r.cooked_at DESC
        LIMIT $limit
        """
        
        # 喜欢的菜
        liked_cypher = """
        MATCH (u:User {user_id: $user_id})-[r:liked]->(d:Dish)
        RETURN d.name as dish, r.liked_at as liked_at
        ORDER BY r.liked_at DESC
        LIMIT $limit
        """
        
        searched = self.g.run(search_cypher, user_id=user_id, limit=limit).data()
        cooked = self.g.run(cooked_cypher, user_id=user_id, limit=limit).data()
        liked = self.g.run(liked_cypher, user_id=user_id, limit=limit).data()
        
        return {
            'searched': searched,
            'cooked': cooked,
            'liked': liked
        }
    
    def delete_user(self, user_id):
        """
        删除用户及其所有关系
        
        Args:
            user_id: 用户ID
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})
        DETACH DELETE u
        """
        
        self.g.run(cypher, user_id=user_id)
        print(f"用户 {user_id} 已删除")
    
    def list_all_users(self):
        """列出所有用户"""
        cypher = """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[r]->()
        WITH u, COUNT(r) as activity_count
        RETURN u.user_id as user_id, u.name as name, 
               u.created_at as created_at, activity_count
        ORDER BY activity_count DESC
        """
        
        users = self.g.run(cypher).data()
        return users
    
    def auto_update_preferences(self, user_id, extracted_prefs):
        """
        根据提取的偏好自动更新用户信息
        
        Args:
            user_id: 用户ID
            extracted_prefs: 提取的偏好信息 {
                'dishes_cooked': [],
                'dishes_liked': [],
                'flavors': [],
                'tags': [],
                'ingredients': []
            }
        """
        # 1. 记录做过的菜
        for dish in extracted_prefs.get('dishes_cooked', []):
            self.record_cooked(user_id, dish)
            print(f"  ✅ 自动记录: {user_id} 做过 {dish}")
        
        # 2. 记录喜欢的菜
        for dish in extracted_prefs.get('dishes_liked', []):
            self.record_liked(user_id, dish)
            print(f"  ✅ 自动记录: {user_id} 喜欢 {dish}")
        
        # 3. 更新口味偏好
        flavors = extracted_prefs.get('flavors', [])
        if flavors:
            user = self.g.nodes.match("User", user_id=user_id).first()
            if user:
                prefs = json.loads(user.get('preferences', '{}'))
                if 'flavors' not in prefs:
                    prefs['flavors'] = []
                
                # 合并新口味（去重）
                for flavor in flavors:
                    if flavor not in prefs['flavors']:
                        prefs['flavors'].append(flavor)
                
                user['preferences'] = json.dumps(prefs, ensure_ascii=False)
                self.g.push(user)
                print(f"  ✅ 自动更新: {user_id} 的口味偏好 → {prefs['flavors']}")
        
        # 4. 更新生活习惯标签
        tags = extracted_prefs.get('tags', [])
        if tags:
            user = self.g.nodes.match("User", user_id=user_id).first()
            if user:
                prefs = json.loads(user.get('preferences', '{}'))
                if 'tags' not in prefs:
                    prefs['tags'] = []
                
                # 合并新标签（去重）
                for tag in tags:
                    if tag not in prefs['tags']:
                        prefs['tags'].append(tag)
                
                user['preferences'] = json.dumps(prefs, ensure_ascii=False)
                self.g.push(user)
                print(f"  ✅ 自动更新: {user_id} 的生活习惯标签 → {prefs['tags']}")
        
        # 5. 更新食材偏好
        ingredients = extracted_prefs.get('ingredients', [])
        if ingredients:
            user = self.g.nodes.match("User", user_id=user_id).first()
            if user:
                prefs = json.loads(user.get('preferences', '{}'))
                if 'ingredients' not in prefs:
                    prefs['ingredients'] = []
                
                # 合并新食材（去重）
                for ing in ingredients:
                    if ing not in prefs['ingredients']:
                        prefs['ingredients'].append(ing)
                
                user['preferences'] = json.dumps(prefs, ensure_ascii=False)
                self.g.push(user)
                print(f"  ✅ 自动更新: {user_id} 的食材偏好 → {prefs['ingredients']}")


if __name__ == "__main__":
    print("=" * 60)
    print("用户管理模块测试")
    print("=" * 60)
    
    manager = UserManager()
    
    # 测试1：创建新用户
    print("\n1. 创建新用户...")
    user_info = manager.login_or_create_user(
        user_id="test_user_001",
        user_name="测试用户",
        preferences={"dietary": "清淡", "skill": "新手"}
    )
    print(f"   用户信息: {user_info}")
    
    # 测试2：记录用户行为
    print("\n2. 记录用户行为...")
    manager.record_search("test_user_001", "番茄炒蛋")
    manager.record_search("test_user_001", "番茄炒蛋")  # 再次搜索
    manager.record_cooked("test_user_001", "番茄炒蛋", rating=5)
    manager.record_liked("test_user_001", "番茄炒蛋")
    
    # 测试3：获取用户历史
    print("\n3. 获取用户历史...")
    history = manager.get_user_history("test_user_001")
    print(f"   搜索历史: {history['searched']}")
    print(f"   做过的菜: {history['cooked']}")
    print(f"   喜欢的菜: {history['liked']}")
    
    # 测试4：再次登录（用户已存在）
    print("\n4. 再次登录...")
    user_info = manager.login_or_create_user("test_user_001")
    print(f"   用户统计: {user_info['stats']}")
    
    # 测试5：列出所有用户
    print("\n5. 列出所有用户...")
    all_users = manager.list_all_users()
    for user in all_users:
        print(f"   - {user['name']} ({user['user_id']}): {user['activity_count']} 条活动")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
