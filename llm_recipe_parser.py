#!/usr/bin/env python3
# coding: utf-8
# File: llm_recipe_parser.py
# Date: 2025-11-18
"""
基于LLM的菜谱解析器 - 高质量知识图谱构建
使用DeepSeek API提取结构化信息
"""

import os
import json
import re
from openai import OpenAI
from typing import Dict, List, Optional
import time

class LLMRecipeParser:
    def __init__(self, api_key: str):
        """初始化LLM解析器"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-chat"
        
        # 定义标准化的JSON Schema
        self.schema = {
            "name": "菜品名称",
            "category": "菜系分类（如：川菜、粤菜、湘菜、家常菜等）",
            "difficulty": "难度等级（1-5，1最简单，5最难）",
            "time": "烹饪时间（如：30分钟）",
            "desc": "菜品简介",
            "flavors": ["口味列表（如：辣、甜、咸、酸、鲜、香、麻、苦、清淡）"],
            "tags": ["标签列表（如：快手菜、下饭菜、营养、健身、熬夜等）"],
            "ingredients": [
                {
                    "name": "食材名称",
                    "amount": "用量",
                    "is_main": "是否主料（true/false）"
                }
            ],
            "condiments": [
                {
                    "name": "调料名称",
                    "amount": "用量"
                }
            ],
            "tools": ["所需工具列表"],
            "steps": [
                {
                    "step_number": "步骤序号",
                    "description": "步骤描述",
                    "time": "所需时间（可选）",
                    "temperature": "火候（可选，如：大火、中火、小火）"
                }
            ],
            "tips": ["烹饪技巧和注意事项"],
            "nutrition": {
                "calories": "热量（可选）",
                "protein": "蛋白质含量（可选）",
                "benefits": ["营养价值和功效"]
            }
        }
    
    def create_extraction_prompt(self, md_content: str) -> str:
        """创建提取prompt"""
        prompt = f"""你是一个专业的菜谱信息提取专家。请仔细阅读以下菜谱文档，提取所有关键信息，并按照指定的JSON格式输出，其用于neo4j构建高质量知识图谱。
你应该尽可能只凭借文档提取信息，例如除非文档中没有说明菜品flavors的任何信息，你才可以根据你的经验进行补充，但是补充的信息一定要准确。

**重要规则：**
1. **口味(flavors)**：必须从以下标准口味中选择：辣、甜、咸、酸、鲜、香、麻、苦、清淡。可以多选。
2. **菜系分类(category)**：不要自己推断，留空即可，会由系统自动填充。
3. **标签(tags)**：包括但不限于：
   - 场景：家常菜、快手菜、下饭菜、下酒菜、宴客菜、夜宵、早餐、午餐、晚餐
   - 功能：营养、减肥、健身、养胃、补血、熬夜、清热、滋补
   - 烹饪方式：蒸菜、炒菜、炖菜、煮菜、烤菜、煎菜、炸菜、凉菜
   - 食材类型：海鲜、肉类、素菜、汤羹、主食、甜品
3. **食材分类**：主料(is_main=true)和辅料(is_main=false)要明确区分
4. **调料**：盐、油、酱油等调味品单独列出
5. **难度**：根据步骤复杂度、技巧要求、时间长短综合判断（1-5级）
6. **步骤**：每个步骤要清晰，包含具体操作、时间、火候
7. **技巧**：提取关键的烹饪技巧、注意事项、常见错误

**输出格式：**
请严格按照以下JSON格式输出，不要添加任何其他文字：

```json
{{
  "name": "菜品名称",
  "category": "",
  "difficulty": 3,
  "time": "30分钟",
  "desc": "菜品简介",
  "flavors": ["辣", "鲜"],
  "tags": ["川菜", "下饭菜", "家常菜"],
  "ingredients": [
    {{"name": "主料名", "amount": "300g", "is_main": true}},
    {{"name": "辅料名", "amount": "适量", "is_main": false}}
  ],
  "condiments": [
    {{"name": "盐", "amount": "适量"}},
    {{"name": "酱油", "amount": "15ml"}}
  ],
  "tools": ["炒锅", "菜刀", "砧板"],
  "steps": [
    {{
      "step_number": 1,
      "description": "具体操作描述",
      "time": "5分钟",
      "temperature": "大火"
    }}
  ],
  "tips": [
    "技巧1：...",
    "注意事项：..."
  ],
  "nutrition": {{
    "calories": "约300卡/份",
    "protein": "高",
    "benefits": ["补充蛋白质", "增强免疫力"]
  }}
}}
```

**菜谱文档内容：**
{md_content}

请开始提取并输出JSON："""
        
        return prompt
    
    def extract_json_from_response(self, response: str) -> Optional[Dict]:
        """从LLM响应中提取JSON"""
        # 尝试提取```json```代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试提取{}包裹的内容
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {response[:500]}...")
            return None
    
    def parse_recipe_with_llm(self, md_content: str, retry=3) -> Optional[Dict]:
        """使用LLM解析单个菜谱"""
        prompt = self.create_extraction_prompt(md_content)
        
        for attempt in range(retry):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的菜谱信息提取专家，擅长从非结构化文本中提取结构化信息。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # 降低温度以获得更稳定的输出
                    max_tokens=2000
                )
                
                result = response.choices[0].message.content
                recipe_data = self.extract_json_from_response(result)
                
                if recipe_data:
                    # 验证必需字段
                    if self.validate_recipe_data(recipe_data):
                        return recipe_data
                    else:
                        print(f"数据验证失败，重试 {attempt + 1}/{retry}")
                else:
                    print(f"JSON提取失败，重试 {attempt + 1}/{retry}")
                
                time.sleep(1)  # 避免API限流
                
            except Exception as e:
                print(f"API调用失败: {e}，重试 {attempt + 1}/{retry}")
                time.sleep(2)
        
        return None
    
    def validate_recipe_data(self, data: Dict) -> bool:
        """验证提取的数据是否完整"""
        required_fields = ['name', 'flavors', 'tags', 'ingredients', 'steps']
        
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"缺少必需字段: {field}")
                return False
        
        # 验证口味是否在标准列表中
        valid_flavors = ['辣', '甜', '咸', '酸', '鲜', '香', '麻', '苦', '清淡']
        for flavor in data.get('flavors', []):
            if flavor not in valid_flavors:
                print(f"非标准口味: {flavor}")
                # 不返回False，只是警告
        
        return True
    
    def parse_all_recipes(self, dishes_dir: str, output_path: str, start_from: int = 0):
        """批量解析所有菜谱"""
        print("="*60)
        print("开始使用LLM解析菜谱...")
        print(f"输入目录: {dishes_dir}")
        print(f"输出文件: {output_path}")
        print("="*60)
        
        # 收集所有MD文件
        all_md_files = []
        for root, dirs, files in os.walk(dishes_dir):
            for file in files:
                if file.endswith('.md') and file != 'README.md':
                    md_path = os.path.join(root, file)
                    all_md_files.append(md_path)
        
        print(f"\n发现 {len(all_md_files)} 个MD文件")
        
        # 如果输出文件已存在，读取已解析的数据
        existing_recipes = []
        if os.path.exists(output_path) and start_from > 0:
            with open(output_path, 'r', encoding='utf-8') as f:
                for line in f:
                    existing_recipes.append(json.loads(line))
            print(f"已加载 {len(existing_recipes)} 个已解析的菜谱")
        
        # 打开输出文件（追加模式）
        mode = 'a' if start_from > 0 else 'w'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        success_count = len(existing_recipes)
        failed_count = 0
        failed_files = []
        
        with open(output_path, mode, encoding='utf-8') as f:
            for idx, md_path in enumerate(all_md_files[start_from:], start=start_from):
                filename = os.path.basename(md_path)
                print(f"\n[{idx+1}/{len(all_md_files)}] 解析: {filename}")
                
                try:
                    # 读取MD文件
                    with open(md_path, 'r', encoding='utf-8') as mf:
                        md_content = mf.read()
                    
                    # 从文件路径提取category（只取一级目录）
                    rel_path = os.path.relpath(md_path, dishes_dir)
                    path_parts = rel_path.split(os.sep)
                    category_folder = path_parts[0] if len(path_parts) > 0 else ''
                    
                    # 使用LLM解析
                    recipe_data = self.parse_recipe_with_llm(md_content)
                    
                    if recipe_data:
                        # 设置category为文件夹名
                        recipe_data['category'] = category_folder
                        
                        # 写入文件
                        f.write(json.dumps(recipe_data, ensure_ascii=False) + '\n')
                        f.flush()  # 立即写入磁盘
                        
                        success_count += 1
                        print(f"✅ 成功: {recipe_data['name']}")
                        print(f"   口味: {', '.join(recipe_data.get('flavors', []))}")
                        print(f"   标签: {', '.join(recipe_data.get('tags', []))}")
                    else:
                        failed_count += 1
                        failed_files.append(filename)
                        print(f"❌ 失败: {filename}")
                    
                    # 每10个菜谱显示一次进度
                    if (idx + 1) % 10 == 0:
                        print(f"\n--- 进度: {idx+1}/{len(all_md_files)}, 成功: {success_count}, 失败: {failed_count} ---")
                    
                    # API限流控制
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_count += 1
                    failed_files.append(filename)
                    print(f"❌ 异常: {filename} - {e}")
        
        # 输出统计信息
        print("\n" + "="*60)
        print("解析完成！")
        print(f"总文件数: {len(all_md_files)}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"成功率: {success_count/(success_count+failed_count)*100:.1f}%")
        
        if failed_files:
            print(f"\n失败文件列表:")
            for f in failed_files:
                print(f"  - {f}")
        
        print("="*60)
        
        return success_count, failed_count


def main():
    """主函数"""
    # 配置
    API_KEY = "sk-c3c8709965474f6f908d0d11d849d2a6"  # 请替换为你的DeepSeek API Key
    
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(cur_dir)
    dishes_dir = os.path.join(project_dir, 'dishes')
    output_path = os.path.join(cur_dir, 'data', 'recipes_llm.json')
    
    # 创建解析器
    parser = LLMRecipeParser(api_key=API_KEY)
    
    # 解析所有菜谱
    # start_from参数可用于断点续传
    parser.parse_all_recipes(dishes_dir, output_path, start_from=0)


if __name__ == '__main__':
    main()
