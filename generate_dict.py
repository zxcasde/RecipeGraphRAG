#!/usr/bin/env python3
# coding: utf-8
# File: generate_dict.py
# Date: 2025-11-17

import os
import json
import re

def normalize_condiment_name(name):
    """标准化调料名称"""
    if not name:
        return ""
    
    # 标准化映射表
    normalize_map = {
        # 糖类
        '白砂糖': '白糖',
        '绵白糖': '白糖',
        '红糖': '红糖',
        '冰糖': '冰糖',
        
        # 酱油类
        '生抽酱油': '生抽',
        '老抽酱油': '老抽',
        '味极鲜': '生抽',
        
        # 葱类
        '大葱': '葱',
        '小葱': '葱',
        '香葱': '葱',
        '洋葱': '洋葱',  # 洋葱单独保留
        
        # 油类
        '食用油': '油',
        '植物油': '油',
        '花生油': '花生油',
        '芝麻油': '香油',
        '香油': '香油',
        
        # 盐类
        '食用盐': '盐',
        '精盐': '盐',
        '海盐': '盐',
    }
    
    # 先尝试精确匹配
    if name in normalize_map:
        return normalize_map[name]
    
    # 模糊匹配（包含关系）
    for key, value in normalize_map.items():
        if key in name:
            return value
    
    return name

def extract_core_condiments(condiment):
    """从组合调料描述中提取核心调料名"""
    if not condiment:
        return []
    
    # 标准化分隔符
    condiment = condiment.replace('/', '、')
    condiment = condiment.replace(' or ', '、')
    condiment = condiment.replace(' + ', '、')
    condiment = condiment.replace('，', '、')
    condiment = condiment.replace(',', '、')
    
    # 去除数量描述（如"三小片"、"两勺"等）
    condiment = re.sub(r'[一二三四五六七八九十百千\d]+[大中小]?[片块勺滴把颗粒克g]', '', condiment)
    
    # 按顿号拆分
    items = condiment.split('、')
    
    core_items = []
    for item in items:
        item = item.strip()
        if not item or len(item) < 2:
            continue
        
        # 去除"等"、"等调味包"等后缀
        item = re.sub(r'等.*$', '', item)
        
        # 标准化常见调料名称
        item = normalize_condiment_name(item)
        
        if item and len(item) >= 2:
            core_items.append(item)
    
    return core_items

def clean_entity(entity):
    """清理实体名称，去除数量、括号说明等"""
    if not entity:
        return ""
    
    # 去除括号及其内容
    entity = re.sub(r'[（(][^）)]*[）)]', '', entity)
    entity = re.sub(r'\[.*?\]', '', entity)  # 去除方括号
    
    # 去除前缀符号（如 +、-、* 等）
    entity = re.sub(r'^[\+\-\*\s]+', '', entity)
    
    # 去除数量描述（包括数字+单位，以及数字+空格+单位）
    entity = re.sub(r'\s*\d+[\d\.\s]*(g|kg|ml|L|个|只|根|片|块|颗|粒|瓣|支|条|斤|两|克|毫升|升|盒|袋|包|双|°C)\s*$', '', entity)
    entity = re.sub(r'\s+\d+[\-\+]?\s*$', '', entity)  # 去除末尾的数字（如"大蒜 3-"）
    entity = re.sub(r'[一二三四五六七八九十百千]+[克个只条根片块颗粒斤两双个]$', '', entity)
    
    # 去除"一双"、"一个"等量词
    entity = re.sub(r'一双$|一个$|一口$', '', entity)
    
    # 去除"适量"、"少许"等模糊量词
    entity = re.sub(r'适量$|少许$|若干$|些许$', '', entity)
    
    # 去除"或"、"或者"、"or"后面的内容
    if '或' in entity:
        entity = entity.split('或')[0]
    if ' or ' in entity:
        entity = entity.split(' or ')[0]
    
    # 去除逗号后的描述（如"黑鳕鱼，带皮" → "黑鳕鱼"）
    if '，' in entity:
        parts = entity.split('，')
        # 如果第二部分是描述性的（如"带皮"），只保留第一部分
        if len(parts[1]) <= 3:
            entity = parts[0]
    
    # 去除"/"后的内容（如果是长描述或包含"任何"等词）
    if '/' in entity:
        parts = entity.split('/')
        # 如果第二部分很长（>10字符）或包含"任何"等词，说明是说明文字，只保留第一部分
        if len(parts) > 1 and (len(parts[1]) > 10 or '任何' in parts[1] or '牌子' in parts[1]):
            entity = parts[0]
        # 如果第一部分和第二部分都是短的食材名，保留（如"五花肉/瘦肉"）
    
    # 去除前后空格和特殊字符
    entity = entity.strip().strip('*').strip().strip('，').strip()
    
    return entity

def is_valid_entity(entity):
    """判断是否是有效的实体"""
    if not entity or len(entity) < 2:
        return False
    
    # 过滤HTML注释和链接
    if entity.startswith('<!--') or entity.startswith('!') or 'http' in entity.lower():
        return False
    
    # 过滤纯符号
    if re.match(r'^[!@#$%^&*\(\)\-\+=\[\]{}|\\:;"\'<>,.?/~`\s]+$', entity):
        return False
    
    # 过滤以数量开头的（如"10g 吉利丁"、"1 袋半成品薯条"、"1 盒"、"1 双"）
    if re.match(r'^\d+[\d\.\s]*(g|kg|ml|L|cm|厘米|毫升|升|个|只|根|片|袋|包|盒|双|颗|°C)', entity):
        return False
    
    # 过滤包含"直径"、"网孔"、"大小不限"等尺寸描述
    if re.search(r'直径|网孔|厘米以上|以上的|大小不限|°C', entity):
        return False
    
    # 过滤说明性文字（更全面）
    skip_keywords = ['以上配料', '下列原料', '下面的食材', '可根据口味', 
                    '在这里列出', '注意', '供有', '食材原料可以',
                    '其余配菜例如', '其他调味料', '准备时',
                    '每次制作', '需要分多次', '超过', '人需要', '情况下',
                    '例如带刻度', '例如', '等配料包', '等蔬菜类', '等蛋类',
                    '等熟肉', '等豆制品', '品牌不限', '别称', '指的是',
                    '可以参考', '参见', '请参考', '该配方', '填充后',
                    '能够将', '即可', '未过期', '如果附近', '没有',
                    '必须是', '要求必须', '尽量选择', '最好', '推荐',
                    '建议使用', '需要', '能放进', '一个装', '一口有点']
    if any(kw in entity for kw in skip_keywords):
        return False
    
    # 过滤工具和容器描述
    tool_keywords = ['一次性', '簸箕', '模具', '冰箱', '克数称', '克称', '塑料',
                    '杯子', '盆', '碟子', '手套', '纱布', '吸油纸', '锡箔纸',
                    '筛网', '滤网', '搅拌', '擀面杖', '刷子', '温度计', '秤',
                    '厨房纸', '厨房用', '烘焙纸', '过滤', '打火机', '秒表',
                    '量杯', '蒸架', '蒸笼', '蒸箱', '蒸篦', '电磁炉', '灶台',
                    '电饭煲', '电饼铛', '燃气灶', '披萝石', '轻食机',
                    '料理机', '榨汁机', '粉碎机', '调理机', '面包机',
                    '雪克杯', '雪克瓶', '调酒杯', '海波杯', '高球杯', '利口酒杯',
                    '密封袋', '保鲜', '吸管', '研杵', '捣药罐', '蒜臼']
    if any(kw in entity for kw in tool_keywords):
        return False
    
    # 过滤纯描述性词语
    pure_desc = ['主料', '辅料', '配菜', '原料', '必备', '必须材料', '工具',
                '可选', '可选工具', '调味料', '小料', '炒料', '汤料包',
                '风味调料', '面食材料', '菜码', '蘸料碟', '额外的',
                '喜欢的沙拉酱', '放得下玉米的锅', '带脚', '摊鸡蛋皮',
                '面包本体', '煎蛋', '小斧头', '圆碟子', '大号的玻璃杯',
                '深一点的小铁盆', '洗菜盆', '遇水发光冰块', '打碎的冰块']
    if entity in pure_desc:
        return False
    
    # 过滤包含"额外"、"可选"等修饰的长描述
    if ('额外' in entity or '可选' in entity) and len(entity) > 8:
        return False
    
    # 过滤包含问号、感叹号等特殊标记
    if '?' in entity or '？' in entity or '!' in entity or '！' in entity:
        return False
    
    # 过滤包含"or"、"/"且长度较长的组合描述（但保留简单的如"五花肉/瘦肉"）
    if (' or ' in entity or '/' in entity) and len(entity) > 15:
        return False
    
    # 过滤包含多个调料的组合（如"盐 + 鸡精 + 十三香"）
    if '+' in entity or ('，' in entity and len(entity) > 20):
        return False
    
    # 过滤重复表述（如"牛腱子"和"牛腱子肉"应只保留"牛腱子"）
    # 这个在后续的normalize中处理
    
    return True

def normalize_similar_entities(entity):
    """标准化相似实体"""
    # 错别字修正
    typo_map = {
        '胡箩卜': '胡萝卜',
        '内脂豆腐': '内酯豆腐',
    }
    if entity in typo_map:
        return typo_map[entity]
    
    # 去除"带皮"、"去皮"等前缀（统一到基础食材）
    if entity.startswith('带皮'):
        base = entity[2:]
        if len(base) >= 2:
            return base
    if entity.startswith('去皮'):
        base = entity[2:]
        if len(base) >= 2:
            return base
    
    # 去除"冷冻"前缀
    if entity.startswith('冷冻'):
        base = entity[2:]
        if len(base) >= 2:
            return base
    
    return entity

def should_keep_entity(entity, all_entities):
    """判断是否应该保留该实体（去除冗余的长表述）"""
    # 如果存在更短的同义词，则不保留
    # 例如："牛腱子肉" vs "牛腱子"，保留"牛腱子"
    for other in all_entities:
        if other != entity and other in entity and len(other) >= 2:
            # 如果other是entity的子串，且差异只是"肉"、"片"、"条"、"薄片"等后缀
            if entity == other + '肉' or entity == other + '片' or entity == other + '条' or entity == other + '薄片':
                return False
            # 如果差异是"水"后缀（如"凉白开"vs"凉白开水"）
            if entity == other + '水' and len(other) >= 3:
                return False
            # 工具类：去除修饰词前缀
            if entity.startswith('不粘') and other == entity[2:]:
                return False  # "不粘平底锅" vs "平底锅"
            if entity.startswith('普通的') and other == entity[3:]:
                return False  # "普通的炒锅" vs "炒锅"
            if entity.startswith('平底') and other == entity[2:] and '锅' in other:
                return False  # "平底煎锅" vs "煎锅"
            # 特殊处理：黑胡椒系列
            if other == '黑胡椒' and entity in ['黑胡椒碎', '黑胡椒粉', '黑胡椒粒']:
                return False
            # 特殊处理：烧烤料
            if other == '烧烤料' and entity == '烧烤撒料':
                return False
            # 特殊处理：猪肉末
            if other == '猪肉末' and entity.startswith('猪肉末（'):
                return False
    return True

def is_not_tool(entity):
    """判断是否不是工具（是食材或调料）"""
    # 这些明显不是工具
    not_tool_keywords = ['酒', '底料', '粉', '油', '酱', '醋', '糖', '盐']
    return any(kw in entity for kw in not_tool_keywords)

def normalize_entity(entities, is_condiment=False, is_tool=False):
    """标准化实体集合，去除重复"""
    cleaned = set()
    entity_map = {}  # 用于去重：标准化形式 -> 原始形式
    
    # 第一遍：收集所有有效实体
    valid_entities = []
    for entity in entities:
        # 先验证是否是有效实体
        if not is_valid_entity(entity):
            continue
        # 如果是工具类，过滤掉明显不是工具的
        if is_tool and is_not_tool(entity):
            continue
        valid_entities.append(entity)
    
    # 第二遍：处理每个实体
    for entity in valid_entities:
        # 如果是调料，先拆分组合调料
        if is_condiment:
            core_items = extract_core_condiments(entity)
            for item in core_items:
                cleaned_entity = clean_entity(item)
                if not cleaned_entity or len(cleaned_entity) < 2:
                    continue
                
                # 标准化：去除空格、统一标点
                normalized = cleaned_entity.replace(' ', '').replace('，', ',')
                
                # 如果已存在更短的形式，保留更短的
                if normalized in entity_map:
                    if len(cleaned_entity) < len(entity_map[normalized]):
                        entity_map[normalized] = cleaned_entity
                else:
                    entity_map[normalized] = cleaned_entity
        else:
            cleaned_entity = clean_entity(entity)
            if not cleaned_entity:
                continue
            
            # 标准化相似实体（错别字、前缀等）
            cleaned_entity = normalize_similar_entities(cleaned_entity)
            
            # 检查是否应该保留（去除冗余）
            if not should_keep_entity(cleaned_entity, valid_entities):
                continue
            
            # 标准化：去除空格、统一标点
            normalized = cleaned_entity.replace(' ', '').replace('，', ',')
            
            # 如果已存在更短的形式，保留更短的
            if normalized in entity_map:
                if len(cleaned_entity) < len(entity_map[normalized]):
                    entity_map[normalized] = cleaned_entity
            else:
                entity_map[normalized] = cleaned_entity
    
    return set(entity_map.values())

def generate_dict_from_json():
    """从recipes_llm.json生成词典文件"""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(cur_dir, 'data', 'recipes_llm.json')
    dict_dir = os.path.join(cur_dir, 'dict')
    
    # 确保dict目录存在
    os.makedirs(dict_dir, exist_ok=True)
    
    # 初始化集合
    dishes = set()
    ingredients = set()
    condiments = set()
    tools = set()
    categories = set()
    
    # 读取数据
    print("开始生成词典文件...")
    count = 0
    for line in open(data_path, 'r', encoding='utf-8'):
        count += 1
        data = json.loads(line)
        
        dishes.add(data['name'])
        categories.add(data.get('category', ''))
        
        for ing in data.get('ingredients', []):
            # 处理新格式：[{"name": "xxx", "amount": "xxx", "is_main": true}, ...]
            if isinstance(ing, dict):
                ingredients.add(ing.get('name', ''))
            else:
                ingredients.add(ing)
        
        for cond in data.get('condiments', []):
            # 处理新格式：[{"name": "xxx", "amount": "xxx"}, ...]
            if isinstance(cond, dict):
                condiments.add(cond.get('name', ''))
            else:
                condiments.add(cond)
        
        for tool in data.get('tools', []):
            # tools 在新格式中仍是字符串列表
            if isinstance(tool, dict):
                tools.add(tool.get('name', ''))
            else:
                tools.add(tool)
    
    # 移除空字符串
    categories.discard('')
    
    # 标准化和去重
    print("\n开始清理和去重...")
    ingredients = normalize_entity(ingredients, is_condiment=False, is_tool=False)
    condiments = normalize_entity(condiments, is_condiment=True, is_tool=False)
    tools = normalize_entity(tools, is_condiment=False, is_tool=True)
    
    print(f"清理后统计：")
    print(f"  食材: {len(ingredients)} 个")
    print(f"  调料: {len(condiments)} 个")
    print(f"  工具: {len(tools)} 个")
    
    # 写入文件
    def write_dict(filename, words):
        path = os.path.join(dict_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            for word in sorted(words):
                f.write(word + '\n')
        print(f"生成 {filename}: {len(words)} 个词")
    
    print("\n写入文件...")
    write_dict('dish.txt', dishes)
    write_dict('ingredient.txt', ingredients)
    write_dict('condiment.txt', condiments)
    write_dict('tool.txt', tools)
    write_dict('category.txt', categories)
    
    print("词典生成完成！")
    print(f"菜品: {len(dishes)}")
    print(f"食材: {len(ingredients)}")
    print(f"调料: {len(condiments)}")
    print(f"工具: {len(tools)}")
    print(f"分类: {len(categories)}")

if __name__ == '__main__':
    generate_dict_from_json()
