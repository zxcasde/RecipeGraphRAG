#!/usr/bin/env python3
# coding: utf-8
# File: parse_recipe_md.py
# Date: 2025-11-17

import os
import re
import json

class RecipeParser:
    def __init__(self, dishes_dir):
        self.dishes_dir = dishes_dir
        self.recipes = []
        
        # 主要食材关键词（优先级最高）
        self.main_ingredient_keywords = [
            '鱼', '虾', '蟹', '鸡', '鸭', '鹅', '猪', '牛', '羊', '肉',
            '排骨', '五花肉', '里脊', '鸡蛋', '豆腐', '面', '米', '粉',
            '土豆', '茄子', '黄瓜', '西红柿', '番茄', '白菜', '青菜'
        ]
        
        # 调料关键词
        self.condiment_keywords = [
            '食用油', '植物油', '花生油', '芝麻油', '香油',
            '盐', '食用盐', '酱油', '生抽', '老抽', '醋', '香醋', '陈醋',
            '糖', '白糖', '白砂糖', '冰糖', '料酒', '黄酒',
            '豆瓣酱', '郫县豆瓣', '蚝油', '味精', '鸡精',
            '花椒', '辣椒', '干辣椒', '小米椒', '八角', '桂皮', '香叶', '孜然',
            '葱花', '蒜末', '姜片', '姜丝', '蒜瓣', '大葱', '小葱', '香葱',
            '胡椒粉', '白胡椒粉', '黑胡椒粉', '十三香', '五香粉'
        ]
        
        # 工具关键词
        self.tool_keywords = [
            '锅', '刀', '碗', '盘', '筷', '勺', '铲', '器', 
            '打蛋器', '微波炉', '烤箱', '容器', '蒸锅', '炒锅',
            '砧板', '菜刀', '漏勺', '笊篱', '保鲜膜', '锡纸'
        ]
        
        # 烹饪方法关键词
        self.method_keywords = {
            '清蒸': '蒸', '红烧': '烧', '干煎': '煎', '油焖': '焖',
            '炒': '炒', '煮': '煮', '炖': '炖', '烤': '烤', '煎': '煎',
            '蒸': '蒸', '焖': '焖', '烧': '烧', '炸': '炸', '拌': '拌',
            '凉拌': '拌', '水煮': '煮', '油炸': '炸', '小炒': '炒'
        }
        
    def parse_all_recipes(self):
        """遍历所有MD文件（递归遍历所有子目录）"""
        print("开始解析菜谱文档...")
        print(f"扫描目录: {self.dishes_dir}\n")
        
        count = 0
        failed = 0
        all_md_files = []
        
        # 收集所有MD文件
        for root, dirs, files in os.walk(self.dishes_dir):
            for file in files:
                if file.endswith('.md') and file != 'README.md':
                    md_path = os.path.join(root, file)
                    all_md_files.append(md_path)
        
        print(f"发现 {len(all_md_files)} 个MD文件\n")
        
        # 解析每个文件
        for md_path in all_md_files:
            # 获取分类（从dishes/后的第一级目录）
            rel_path = os.path.relpath(md_path, self.dishes_dir)
            category = rel_path.split(os.sep)[0]
            
            try:
                recipe_data = self.parse_single_recipe(md_path, category)
                if recipe_data:
                    self.recipes.append(recipe_data)
                    count += 1
                    if count % 50 == 0:
                        print(f"已解析 {count}/{len(all_md_files)} 个菜谱...")
                else:
                    failed += 1
                    print(f"⚠️  解析为空: {os.path.basename(md_path)}")
            except Exception as e:
                failed += 1
                print(f"❌ 解析失败 {os.path.basename(md_path)}: {e}")
        
        print(f"\n{'='*60}")
        print(f"解析完成！")
        print(f"成功: {count} 个")
        print(f"失败: {failed} 个")
        print(f"总计: {len(all_md_files)} 个MD文件")
        print(f"{'='*60}\n")
        
        return self.recipes
    
    def parse_single_recipe(self, md_path, category):
        """解析单个MD文件"""
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取菜名
        name_match = re.search(r'^#\s+(.+?)的做法', content, re.MULTILINE)
        if not name_match:
            name_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
            if not name_match:
                return None
            dish_name = name_match.group(1).strip()
        else:
            dish_name = name_match.group(1).strip()
        
        difficulty = self.extract_difficulty(content)
        desc = self.extract_description(content)
        sections = self.split_sections(content)
        
        ingredients, condiments, tools = self.parse_ingredients(sections.get('必备原料和工具', ''))
        amounts = self.parse_amounts(sections.get('计算', ''))
        steps = self.parse_steps(sections.get('操作', ''))
        tips = self.parse_tips(sections.get('附加内容', ''))
        cooking_methods = self.extract_cooking_methods(dish_name, steps)
        
        return {
            'name': dish_name,
            'category': category,
            'difficulty': difficulty,
            'desc': desc,
            'ingredients': ingredients,
            'condiments': condiments,
            'tools': tools,
            'amounts': amounts,
            'steps': steps,
            'tips': tips,
            'cooking_methods': cooking_methods
        }
    
    def extract_difficulty(self, content):
        match = re.search(r'预估烹饪难度：(★+)', content)
        return len(match.group(1)) if match else 3
    
    def extract_description(self, content):
        lines = content.split('\n')
        desc_lines = []
        found_title = False
        
        for line in lines:
            if line.startswith('# '):
                found_title = True
                continue
            if found_title and line.startswith('##'):
                break
            if found_title and line.strip():
                if not line.startswith('!') and '预估烹饪难度' not in line:
                    cleaned = line.strip()
                    if cleaned:
                        desc_lines.append(cleaned)
        
        return ' '.join(desc_lines[:3])
    
    def split_sections(self, content):
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def parse_ingredients(self, content):
        ingredients = []
        condiments = []
        tools = []
        lines = content.split('\n')
        
        for line in lines:
            # 移除列表标记
            line = re.sub(r'^[-*]\s+', '', line.strip())
            if not line:
                continue
            
            # 跳过Markdown标题（###、####等）
            if line.startswith('#'):
                continue
            
            # 跳过引用块（以>开头的行）
            if line.startswith('>'):
                continue
            
            # 跳过包含冒号的标题行（如："原料："、"工具："、"调味料："）
            if line.endswith(('：', ':')) or line in ['原料', '工具', '调味料', '食材']:
                continue
            
            # 处理 "原料名：说明文字" 格式，只保留原料名
            if '：' in line or ':' in line:
                # 分割冒号，只取冒号前的部分
                colon_match = re.match(r'^([^：:]+)[：:](.+)$', line)
                if colon_match:
                    line = colon_match.group(1).strip()
                    # 如果冒号前的内容太短或为空，跳过
                    if not line or len(line) < 2:
                        continue
            
            # 先去除括号内的说明（括号内可能包含说明性文字）
            line_cleaned = re.sub(r'\（[^）]+\）|\([^)]+\)', '', line).strip()
            if not line_cleaned:
                continue
            # 对于单个字符，只保留中文字符（如"鱼"、"肉"等）
            if len(line_cleaned) == 1 and not re.match(r'[\u4e00-\u9fa5]', line_cleaned):
                continue
            
            # 跳过说明性文字（使用去除括号后的文本判断）
            skip_keywords = ['图片', '示例', '成品', '注意', '建议', '推荐', 
                           '材料都是', '计算得出', '可额外', 
                           '必备', '以下', '按照', '依照', '过程', '不要太', '温度',
                           '在这里', '下列', '下面的', '可根据', '根据自己', '供有',
                           '配料放入', '配料洗净', '食材原料', '口味偏好', '快速判断']
            if any(kw in line_cleaned for kw in skip_keywords) and len(line_cleaned) > 10:
                continue
            
            # 跳过HTML注释
            if line_cleaned.startswith('<!--') or line_cleaned.startswith('!'):
                continue
            
            # 跳过纯符号或特殊标记
            if re.match(r'^[!@#$%^&*\(\)\-\+=\[\]{}|\\:;"\'<>,.?/~`]+$', line_cleaned):
                continue
            
            # 跳过以数量开头的行（如"10g 吉利丁"、"250ml 椰树牌椰汁"）
            # 这些应该在amounts中，不应该在ingredients中
            if re.match(r'^\d+[\d\.\s]*(g|kg|ml|L|cm|厘米|毫升|升)', line_cleaned):
                continue
            
            # 使用清理后的文本
            line = line_cleaned
            
            # 特殊处理：如果是描述性的组合（如"黑鳕鱼，带皮"），不拆分
            # 判断标准：逗号后面不是独立的食材名，而是属性描述
            should_split = False
            if '、' in line:
                should_split = True  # 顿号通常表示并列，应该拆分
            elif '，' in line or ',' in line:
                # 检查逗号后的内容是否是属性描述
                parts = re.split(r'[，,]', line)
                # 如果拆分后的部分都比较长（>2字符），可能是并列关系，应该拆分
                # 如果有很短的部分（<=2字符），可能是属性描述，不拆分
                if all(len(p.strip()) > 2 for p in parts if p.strip()):
                    should_split = True
            
            if should_split:
                # 拆分成多个项目
                items = re.split(r'[、，,]', line)
                for item in items:
                    item = item.strip()
                    if not item or len(item) < 2:
                        continue
                    
                    # 分类（优先级：主要食材 > 工具 > 调料 > 其他食材）
                    if any(k in item for k in self.main_ingredient_keywords):
                        # 主要食材优先
                        if item not in ingredients:
                            ingredients.append(item)
                    elif any(k in item for k in self.tool_keywords):
                        if item not in tools:
                            tools.append(item)
                    elif any(k in item for k in self.condiment_keywords):
                        if item not in condiments:
                            condiments.append(item)
                    else:
                        # 默认归类为食材
                        if item not in ingredients:
                            ingredients.append(item)
            else:
                # 单个项目或不拆分的组合，直接分类
                if any(k in line for k in self.main_ingredient_keywords):
                    # 主要食材优先
                    if line not in ingredients:
                        ingredients.append(line)
                elif any(k in line for k in self.tool_keywords):
                    if line not in tools:
                        tools.append(line)
                elif any(k in line for k in self.condiment_keywords):
                    if line not in condiments:
                        condiments.append(line)
                else:
                    # 默认归类为食材
                    if line not in ingredients:
                        ingredients.append(line)
        
        return ingredients, condiments, tools
    
    def parse_amounts(self, content):
        """解析用量信息（从'计算'部分提取）"""
        amounts = {}
        lines = content.split('\n')
        
        for line in lines:
            # 跳过空行和标题
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 移除列表标记
            line = re.sub(r'^[-*]\s+', '', line)
            
            # 跳过纯说明性文字（不包含具体用量信息的行）
            # 这些行通常以"每"、"一份"等开头，且以冒号或句号结尾
            skip_patterns = [
                r'^每\s*\d*\s*份[：:：。]',  # 如：每 2 份：
                r'^每次制作.*[：:。]',
                r'^一份.*[：:。]',
                r'^总量[：:：。]',
                r'^按照.*[：:。]',
                r'^以下.*[：:。]',
            ]
            if any(re.match(pattern, line) for pattern in skip_patterns):
                continue
            
            # 跳过包含特定关键词的完整说明句子
            skip_keywords = [
                '注意', '建议', '推荐', '可以', '需要', '理论上', '默认',
                '使用上述', '依口味', '按比例', '计划做', '正好够'
            ]
            if any(kw in line for kw in skip_keywords) and len(line) > 20:
                # 如果包含标点符号，很可能是说明句子
                if any(punct in line for punct in ['。', '！', '，', '、']):
                    continue
            
            # 格式1: 食材名 = 用量 (如：手枪腿 = 1 支（约 350g）)
            match1 = re.search(r'^(.+?)\s*[=＝]\s*(.+)$', line)
            if match1:
                ingredient = match1.group(1).strip()
                amount = match1.group(2).strip()
                
                # 清理食材名中的括号说明
                ingredient_clean = re.sub(r'[（(][^）)]+[）)]', '', ingredient).strip()
                
                if ingredient_clean and amount and len(ingredient_clean) < 30:
                    amounts[ingredient_clean] = amount
                continue
            
            # 格式2: 食材名 空格 用量 (如：鲈鱼 一条)
            # 匹配：中文/英文 + 多个空格 + 数字/中文数量词
            match2 = re.search(r'^([^\s]+(?:\s+[^\s]+)?)\s{2,}(.+)$', line)
            if match2:
                ingredient = match2.group(1).strip()
                amount = match2.group(2).strip()
                
                # 清理食材名中的括号说明
                ingredient_clean = re.sub(r'[（(][^）)]+[）)]', '', ingredient).strip()
                
                if ingredient_clean and amount and len(ingredient_clean) < 30:
                    amounts[ingredient_clean] = amount
                continue
            
            # 格式3: 食材名 单个空格 用量 (更宽松的匹配)
            # 只有当行中包含明显的数量词时才匹配
            if re.search(r'\d+|一|二|三|四|五|六|七|八|九|十|[几若干适量少许]', line):
                parts = line.split(None, 1)  # 按第一个空白符分割
                if len(parts) == 2:
                    ingredient = parts[0].strip()
                    amount = parts[1].strip()
                    
                    # 清理食材名中的括号说明
                    ingredient_clean = re.sub(r'[（(][^）)]+[）)]', '', ingredient).strip()
                    
                    # 确保食材名不是纯数字或量词
                    if ingredient_clean and amount and len(ingredient_clean) < 30:
                        if not re.match(r'^[\d一二三四五六七八九十]+$', ingredient_clean):
                            amounts[ingredient_clean] = amount
        
        return amounts
    
    def parse_steps(self, content):
        steps = []
        lines = content.split('\n')
        
        for line in lines:
            line = re.sub(r'^[-*]\s+', '', line.strip())
            if not line or re.search(r'!\[', line) or line.startswith('#'):
                continue
            line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            if line and len(line) > 3:
                steps.append(line)
        
        return steps
    
    def parse_tips(self, content):
        tips = []
        lines = content.split('\n')
        
        for line in lines:
            line = re.sub(r'^[-*]\s+', '', line.strip())
            if '如果您遵循本指南' in line or re.search(r'https?://', line):
                continue
            line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            if re.search(r'!\[', line) or line.startswith('#'):
                continue
            if line and len(line) > 5:
                tips.append(line)
        
        return '\n'.join(tips)
    
    def extract_cooking_methods(self, dish_name, steps):
        methods = []
        for keyword, method in self.method_keywords.items():
            if keyword in dish_name and method not in methods:
                methods.append(method)
        
        steps_text = ' '.join(steps)
        for keyword, method in self.method_keywords.items():
            if keyword in steps_text and method not in methods:
                methods.append(method)
        
        return methods if methods else ['炒']
    
    def save_to_json(self, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for recipe in self.recipes:
                f.write(json.dumps(recipe, ensure_ascii=False) + '\n')
        print(f"数据已保存到: {output_path}")

if __name__ == '__main__':
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(cur_dir)
    dishes_dir = os.path.join(project_dir, 'dishes')
    output_path = os.path.join(cur_dir, 'data', 'recipes.json')
    
    parser = RecipeParser(dishes_dir)
    recipes = parser.parse_all_recipes()
    parser.save_to_json(output_path)
    
    print(f"\n解析完成！总菜谱数: {len(recipes)}")
