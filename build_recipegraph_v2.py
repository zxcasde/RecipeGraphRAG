#!/usr/bin/env python3
# coding: utf-8
# File: build_recipegraph_v2.py
# Date: 2025-11-18
"""
高质量知识图谱构建器 V2
基于LLM解析的标准化数据构建完整的知识图谱
"""

import os
import json
from py2neo import Graph, Node, Relationship
from typing import Dict, List, Set
import time

class RecipeGraphBuilderV2:
    def __init__(self, neo4j_uri="bolt://127.0.0.1:7687", 
                 neo4j_user="neo4j", 
                 neo4j_password="kurisu810975"):
        """初始化图谱构建器"""
        self.g = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.data_path = 'data/recipes_llm.json'
        
        # 统计信息
        self.stats = {
            'dishes': 0,
            'flavors': 0,
            'tags': 0,
            'ingredients': 0,
            'condiments': 0,
            'tools': 0,
            'relationships': 0
        }
    
    def clear_database(self):
        """清空数据库（可选）"""
        print("⚠️  警告：即将清空数据库...")
        confirm = input("确认清空？(yes/no): ")
        if confirm.lower() == 'yes':
            self.g.run("MATCH (n) DETACH DELETE n")
            print("✅ 数据库已清空")
        else:
            print("❌ 取消清空操作")
    
    def read_recipes(self) -> List[Dict]:
        """读取LLM解析的菜谱数据"""
        recipes = []
        if not os.path.exists(self.data_path):
            print(f"❌ 数据文件不存在: {self.data_path}")
            return recipes
        
        with open(self.data_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    recipe = json.loads(line)
                    recipes.append(recipe)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON解析错误: {e}")
        
        print(f"✅ 读取 {len(recipes)} 个菜谱")
        return recipes
    
    def extract_entities(self, recipes: List[Dict]) -> Dict[str, Set]:
        """提取所有实体"""
        entities = {
            'flavors': set(),
            'tags': set(),
            'ingredients': set(),
            'condiments': set(),
            'tools': set()
        }
        
        for recipe in recipes:
            # 口味
            for flavor in recipe.get('flavors', []):
                if flavor:
                    entities['flavors'].add(flavor)
            
            # 标签
            for tag in recipe.get('tags', []):
                if tag:
                    entities['tags'].add(tag)
            
            # 食材
            for ing in recipe.get('ingredients', []):
                if isinstance(ing, dict):
                    name = ing.get('name', '')
                elif isinstance(ing, str):
                    name = ing
                else:
                    continue
                if name:
                    entities['ingredients'].add(name)
            
            # 调料
            for cond in recipe.get('condiments', []):
                if isinstance(cond, dict):
                    name = cond.get('name', '')
                elif isinstance(cond, str):
                    name = cond
                else:
                    continue
                if name:
                    entities['condiments'].add(name)
            
            # 工具
            for tool in recipe.get('tools', []):
                if tool:
                    entities['tools'].add(tool)
        
        return entities
    
    def create_nodes(self, recipes: List[Dict], entities: Dict[str, Set]):
        """创建所有节点"""
        print("\n" + "="*60)
        print("开始创建节点...")
        print("="*60)
        
        # 1. 创建菜品节点
        print(f"\n[1/6] 创建菜品节点: {len(recipes)} 个")
        for idx, recipe in enumerate(recipes, 1):
            try:
                node = Node("Dish",
                           name=recipe.get('name', ''),
                           category=recipe.get('category', ''),
                           difficulty=recipe.get('difficulty', 3),
                           time=recipe.get('time', ''),
                           desc=recipe.get('desc', ''),
                           steps=json.dumps(recipe.get('steps', []), ensure_ascii=False),
                           tips=json.dumps(recipe.get('tips', []), ensure_ascii=False),
                           nutrition=json.dumps(recipe.get('nutrition', {}), ensure_ascii=False))
                
                self.g.create(node)
                self.stats['dishes'] += 1
                
                if idx % 50 == 0:
                    print(f"  进度: {idx}/{len(recipes)}")
            except Exception as e:
                print(f"  ❌ 创建菜品节点失败: {recipe.get('name', 'Unknown')} - {e}")
        
        print(f"✅ 菜品节点创建完成: {self.stats['dishes']} 个")
        
        # 2. 创建口味节点
        print(f"\n[2/6] 创建口味节点: {len(entities['flavors'])} 个")
        for flavor in entities['flavors']:
            try:
                node = Node("Flavor", name=flavor)
                self.g.create(node)
                self.stats['flavors'] += 1
            except Exception as e:
                print(f"  ❌ 创建口味节点失败: {flavor} - {e}")
        print(f"✅ 口味节点创建完成: {self.stats['flavors']} 个")
        
        # 3. 创建标签节点
        print(f"\n[3/6] 创建标签节点: {len(entities['tags'])} 个")
        for tag in entities['tags']:
            try:
                node = Node("Tag", name=tag)
                self.g.create(node)
                self.stats['tags'] += 1
            except Exception as e:
                print(f"  ❌ 创建标签节点失败: {tag} - {e}")
        print(f"✅ 标签节点创建完成: {self.stats['tags']} 个")
        
        # 4. 创建食材节点
        print(f"\n[4/6] 创建食材节点: {len(entities['ingredients'])} 个")
        for idx, ing in enumerate(entities['ingredients'], 1):
            try:
                node = Node("Ingredient", name=ing)
                self.g.create(node)
                self.stats['ingredients'] += 1
                
                if idx % 100 == 0:
                    print(f"  进度: {idx}/{len(entities['ingredients'])}")
            except Exception as e:
                print(f"  ❌ 创建食材节点失败: {ing} - {e}")
        print(f"✅ 食材节点创建完成: {self.stats['ingredients']} 个")
        
        # 5. 创建调料节点
        print(f"\n[5/6] 创建调料节点: {len(entities['condiments'])} 个")
        for cond in entities['condiments']:
            try:
                node = Node("Condiment", name=cond)
                self.g.create(node)
                self.stats['condiments'] += 1
            except Exception as e:
                print(f"  ❌ 创建调料节点失败: {cond} - {e}")
        print(f"✅ 调料节点创建完成: {self.stats['condiments']} 个")
        
        # 6. 创建工具节点
        print(f"\n[6/6] 创建工具节点: {len(entities['tools'])} 个")
        for tool in entities['tools']:
            try:
                node = Node("Tool", name=tool)
                self.g.create(node)
                self.stats['tools'] += 1
            except Exception as e:
                print(f"  ❌ 创建工具节点失败: {tool} - {e}")
        print(f"✅ 工具节点创建完成: {self.stats['tools']} 个")
        
        print("\n" + "="*60)
        print("节点创建完成！")
        print("="*60)
    
    def create_relationships(self, recipes: List[Dict]):
        """创建所有关系"""
        print("\n" + "="*60)
        print("开始创建关系...")
        print("="*60)
        
        total_recipes = len(recipes)
        
        for idx, recipe in enumerate(recipes, 1):
            dish_name = recipe.get('name', '')
            if not dish_name:
                continue
            
            try:
                # 1. 菜品-口味关系
                for flavor in recipe.get('flavors', []):
                    if flavor:
                        self.create_relationship_safe(
                            'Dish', 'Flavor',
                            dish_name, flavor,
                            'has_flavor', '具有口味'
                        )
                
                # 2. 菜品-标签关系
                for tag in recipe.get('tags', []):
                    if tag:
                        self.create_relationship_safe(
                            'Dish', 'Tag',
                            dish_name, tag,
                            'has_tag', '具有标签'
                        )
                
                # 3. 菜品-食材关系
                for ing in recipe.get('ingredients', []):
                    if isinstance(ing, dict):
                        ing_name = ing.get('name', '')
                        amount = ing.get('amount', '')
                        is_main = ing.get('is_main', False)
                    elif isinstance(ing, str):
                        ing_name = ing
                        amount = ''
                        is_main = False
                    else:
                        continue
                    
                    if ing_name:
                        self.create_relationship_safe(
                            'Dish', 'Ingredient',
                            dish_name, ing_name,
                            'need_ingredient', '需要食材',
                            {'amount': amount, 'is_main': is_main}
                        )
                
                # 4. 菜品-调料关系
                for cond in recipe.get('condiments', []):
                    if isinstance(cond, dict):
                        cond_name = cond.get('name', '')
                        amount = cond.get('amount', '')
                    elif isinstance(cond, str):
                        cond_name = cond
                        amount = ''
                    else:
                        continue
                    
                    if cond_name:
                        self.create_relationship_safe(
                            'Dish', 'Condiment',
                            dish_name, cond_name,
                            'need_condiment', '需要调料',
                            {'amount': amount}
                        )
                
                # 5. 菜品-工具关系
                for tool in recipe.get('tools', []):
                    if tool:
                        self.create_relationship_safe(
                            'Dish', 'Tool',
                            dish_name, tool,
                            'need_tool', '需要工具'
                        )
                
                if idx % 50 == 0:
                    print(f"  进度: {idx}/{total_recipes}, 已创建关系: {self.stats['relationships']}")
            
            except Exception as e:
                print(f"  ❌ 创建关系失败: {dish_name} - {e}")
        
        print("\n" + "="*60)
        print(f"✅ 关系创建完成: {self.stats['relationships']} 条")
        print("="*60)
    
    def create_relationship_safe(self, start_label: str, end_label: str,
                                 start_name: str, end_name: str,
                                 rel_type: str, rel_name: str,
                                 properties: Dict = None):
        """安全地创建关系（带错误处理）"""
        try:
            # 转义单引号
            start_name_escaped = start_name.replace("'", "\\'")
            end_name_escaped = end_name.replace("'", "\\'")
            
            # 构建属性字符串
            prop_str = f"name:'{rel_name}'"
            if properties:
                for key, value in properties.items():
                    if isinstance(value, bool):
                        prop_str += f", {key}:{str(value).lower()}"
                    elif isinstance(value, (int, float)):
                        prop_str += f", {key}:{value}"
                    else:
                        value_escaped = str(value).replace("'", "\\'")
                        prop_str += f", {key}:'{value_escaped}'"
            
            query = f"""
            MATCH (p:{start_label} {{name:'{start_name_escaped}'}}), 
                  (q:{end_label} {{name:'{end_name_escaped}'}})
            MERGE (p)-[r:{rel_type} {{{prop_str}}}]->(q)
            """
            
            self.g.run(query)
            self.stats['relationships'] += 1
            
        except Exception as e:
            print(f"    ⚠️  关系创建失败: {start_name} -> {end_name} ({rel_type}): {e}")
    
    def create_indexes(self):
        """创建索引以提高查询性能"""
        print("\n" + "="*60)
        print("创建索引...")
        print("="*60)
        
        indexes = [
            "CREATE INDEX dish_name IF NOT EXISTS FOR (d:Dish) ON (d.name)",
            "CREATE INDEX flavor_name IF NOT EXISTS FOR (f:Flavor) ON (f.name)",
            "CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.name)",
            "CREATE INDEX ingredient_name IF NOT EXISTS FOR (i:Ingredient) ON (i.name)",
            "CREATE INDEX condiment_name IF NOT EXISTS FOR (c:Condiment) ON (c.name)",
            "CREATE INDEX tool_name IF NOT EXISTS FOR (t:Tool) ON (t.name)",
            "CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.user_id)"
        ]
        
        for idx_query in indexes:
            try:
                self.g.run(idx_query)
                print(f"  ✅ {idx_query.split('FOR')[1].split('ON')[0].strip()}")
            except Exception as e:
                print(f"  ⚠️  索引创建失败: {e}")
        
        print("="*60)
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("知识图谱统计信息")
        print("="*60)
        print(f"菜品节点:   {self.stats['dishes']:>6} 个")
        print(f"口味节点:   {self.stats['flavors']:>6} 个")
        print(f"标签节点:   {self.stats['tags']:>6} 个")
        print(f"食材节点:   {self.stats['ingredients']:>6} 个")
        print(f"调料节点:   {self.stats['condiments']:>6} 个")
        print(f"工具节点:   {self.stats['tools']:>6} 个")
        print(f"关系总数:   {self.stats['relationships']:>6} 条")
        print("="*60)
    
    def build(self, clear_db=False):
        """构建完整的知识图谱"""
        start_time = time.time()
        
        print("\n" + "="*60)
        print("高质量知识图谱构建器 V2")
        print("="*60)
        
        # 1. 清空数据库（可选）
        if clear_db:
            self.clear_database()
        
        # 2. 读取数据
        recipes = self.read_recipes()
        if not recipes:
            print("❌ 没有可用的菜谱数据")
            return
        
        # 3. 提取实体
        print("\n提取实体...")
        entities = self.extract_entities(recipes)
        print(f"  口味: {len(entities['flavors'])} 种")
        print(f"  标签: {len(entities['tags'])} 个")
        print(f"  食材: {len(entities['ingredients'])} 种")
        print(f"  调料: {len(entities['condiments'])} 种")
        print(f"  工具: {len(entities['tools'])} 种")
        
        # 4. 创建节点
        self.create_nodes(recipes, entities)
        
        # 5. 创建关系
        self.create_relationships(recipes)
        
        # 6. 创建索引
        self.create_indexes()
        
        # 7. 打印统计
        self.print_statistics()
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 知识图谱构建完成！耗时: {elapsed_time:.2f} 秒")


def main():
    """主函数"""
    builder = RecipeGraphBuilderV2(
        neo4j_uri="bolt://127.0.0.1:7687",
        neo4j_user="neo4j",
        neo4j_password="kurisu810975"  # 请修改为你的密码
    )
    
    # 构建知识图谱
    # clear_db=True 会清空现有数据库
    builder.build(clear_db=True)


if __name__ == '__main__':
    main()
