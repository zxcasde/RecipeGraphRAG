# coding = utf-8
"""
图RAG系统 - 整合向量检索、图谱检索和LLM
真正基于Neo4j知识图谱的RAG系统
"""

from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import os

try:
    from vector_retriever import VectorRetriever, SENTENCE_TRANSFORMERS_AVAILABLE
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from llm_server import ModelAPI
from query_optimizer import QueryOptimizer
from vector_retriever import VectorRetriever
from graph_retriever import GraphRetriever
from user_manager import UserManager
from advanced_recommender import AdvancedRecommender
from preference_extractor import PreferenceExtractor


class GraphRAGSystem:
    """图RAG系统"""
    
    def __init__(self, model_url="http://localhost:3001/generate", use_vector=True, 
                 use_deepseek=False, api_key=None):
        """
        初始化图RAG系统
        
        Args:
            model_url: LLM服务地址
            use_vector: 是否使用向量检索
            use_deepseek: 是否使用DeepSeek API
            api_key: DeepSeek API密钥
        """
        if use_deepseek:
            self.model = ModelAPI(use_deepseek=True, api_key=api_key)
            self.query_optimizer = QueryOptimizer(use_deepseek=True, api_key=api_key)
            self.preference_extractor = PreferenceExtractor(use_deepseek=True, api_key=api_key)
        else:
            self.model = ModelAPI(MODEL_URL=model_url)
            self.query_optimizer = QueryOptimizer(model_url=model_url)
            self.preference_extractor = PreferenceExtractor(use_deepseek=False)
        self.graph_retriever = GraphRetriever()
        self.advanced_recommender = AdvancedRecommender()  # 高级推荐模块
        self.user_manager = UserManager()  # 用户管理器
        
        # 向量检索（可选）
        self.use_vector = use_vector and SENTENCE_TRANSFORMERS_AVAILABLE
        if self.use_vector:
            try:
                self.vector_retriever = VectorRetriever()
                # 尝试加载索引
                if os.path.exists("data/vector_index.pkl"):
                    self.vector_retriever.load_index()
                    print("向量索引已加载")
                else:
                    print("警告：向量索引未找到，请先运行 vector_retriever.py 构建索引")
                    self.use_vector = False
            except Exception as e:
                print(f"向量检索初始化失败: {e}")
                self.use_vector = False
        else:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("提示：未安装sentence-transformers，将仅使用图谱检索")
            self.vector_retriever = None
    
    def retrieve(self, query, user_id=None, top_k=5):
        """
        混合检索：向量检索 + 图谱检索
        
        Args:
            query: 用户查询
            user_id: 用户ID（可选）
            top_k: 返回Top-K结果
        
        Returns:
            Dict: 检索结果
        """
        results = {
            'query': query,
            'optimized': None,
            'vector_results': [],
            'graph_results': [],
            'combined_results': [],
            'context': {}
        }
        
        # 1. 查询优化
        print("Step 1: 查询优化...")
        optimization = self.query_optimizer.optimize_query(query)
        results['optimized'] = optimization
        optimized_query = optimization.get('optimized_query', query)
        intent = optimization.get('intent', 'query_dish')
        entities = optimization.get('entities', {})
        
        print(f"  优化后查询: {optimized_query}")
        print(f"  意图: {intent}")
        print(f"  实体: {entities}")
        
        # 2. 特殊处理：如果是查询做法且已识别菜品名，直接返回该菜品
        if intent == 'how_to_cook' and entities.get('dishes'):
            print("\nStep 2: 直接查询菜品详情（做法查询）...")
            graph_hits = []
            for dish in entities['dishes']:
                info = self.graph_retriever.search_by_dish(dish, depth=1)
                # 检查是否真的找到了菜品（有步骤或食材信息）
                if info and (info.get('steps') or info.get('ingredients')):
                    results['context'][dish] = info
                    graph_hits.append((dish, 1.0, f"直接查询:{dish}"))
                    print(f"  ✅ 找到菜品: {dish}")
                else:
                    print(f"  ❌ 未找到菜品: {dish}，尝试模糊搜索...")
                    # 如果精确查询失败，尝试向量检索找相似菜品
                    if self.use_vector and self.vector_retriever:
                        try:
                            vector_hits = self.vector_retriever.search(dish, top_k=3)
                            results['vector_results'] = vector_hits
                            print(f"    找到 {len(vector_hits)} 个相似菜品")
                        except Exception as e:
                            print(f"    向量检索失败: {e}")
            
            results['graph_results'] = graph_hits
            # 如果没有找到任何菜品，使用向量检索
            if not graph_hits and not results.get('vector_results'):
                results['vector_results'] = []
        else:
            # 正常的推荐流程
            # 2. 向量检索
            if self.use_vector and self.vector_retriever:
                print("\nStep 2: 向量检索...")
                try:
                    vector_hits = self.vector_retriever.search(optimized_query, top_k=top_k*2)
                    results['vector_results'] = vector_hits
                    print(f"  找到 {len(vector_hits)} 个向量匹配")
                except Exception as e:
                    print(f"  向量检索失败: {e}")
            
            # 3. 图谱检索
            print("\nStep 3: 图谱检索...")
            graph_hits = []
            
            # 3.1 根据实体类型检索
            # 如果是查询特定菜品且有明确菜品名，跳过食材检索（避免泛化匹配）
            skip_ingredient_search = (intent in ['query_dish', 'how_to_cook'] and entities.get('dishes'))
            
            if entities.get('ingredients') and not skip_ingredient_search:
                for ing in entities['ingredients']:
                    dishes = self.graph_retriever.search_by_ingredient(ing, limit=5)
                    for d in dishes:
                        graph_hits.append((d['dish'], 0.9, f"包含食材:{ing}"))
            
            if entities.get('scenes'):
                for scene in entities['scenes']:
                    # 使用 Tag 替代 Scene
                    dishes = self.graph_retriever.search_by_tag(scene, limit=5)
                    for d in dishes:
                        graph_hits.append((d['dish'], 0.8, f"适合场景:{scene}"))
            
            # 如果是查询特定菜品且有明确菜品名，跳过口味检索（避免泛化匹配）
            skip_flavor_search = (intent in ['query_dish', 'how_to_cook'] and entities.get('dishes'))
            
            if entities.get('flavors') and not skip_flavor_search:
                for flavor in entities['flavors']:
                    dishes = self.graph_retriever.search_by_flavor(flavor, limit=10)
                    for d in dishes:
                        graph_hits.append((d['dish'], 0.95, f"口味:{flavor}"))
            
            # 3.2 如果有菜品名，获取详细信息
            if entities.get('dishes'):
                print(f"  检测到菜品名: {entities['dishes']}")
                for dish in entities['dishes']:
                    info = self.graph_retriever.search_by_dish(dish, depth=1)
                    if info:
                        print(f"    ✅ 找到菜品: {dish}")
                        results['context'][dish] = info
                        # 如果是查询类意图，给予高权重
                        if intent in ['query_dish', 'query_ingredient']:
                            graph_hits.append((dish, 1.0, f"直接查询:{dish}"))
                    else:
                        print(f"    ❌ 未找到菜品: {dish} (可能是模糊名称)")
            
            results['graph_results'] = graph_hits
            print(f"  找到 {len(graph_hits)} 个图谱匹配")
        
        # 3.5 用户个性化检索（在融合前执行！）
        if user_id:
            print("\nStep 3.5: 用户个性化检索...")
            
            # 自动提取用户偏好
            print("  提取用户偏好...")
            extracted_prefs = self.preference_extractor.extract_from_query(query)
            print(f"  提取结果: {extracted_prefs}")
            if extracted_prefs.get('has_preference'):
                print("  ✅ 检测到偏好信息，自动更新用户画像...")
                print(f"    - 做过的菜: {extracted_prefs.get('dishes_cooked', [])}")
                print(f"    - 喜欢的菜: {extracted_prefs.get('dishes_liked', [])}")
                print(f"    - 口味偏好: {extracted_prefs.get('flavors', [])}")
                print(f"    - 生活习惯: {extracted_prefs.get('tags', [])}")
                print(f"    - 食材偏好: {extracted_prefs.get('ingredients', [])}")
                self.user_manager.auto_update_preferences(user_id, extracted_prefs)
                print("  ✅ 用户画像更新完成")
            else:
                print("  ℹ️  未检测到偏好信息（这是正常的查询）")
            
            # 获取用户历史数据
            user_data = self.graph_retriever.get_user_preference_dishes(user_id)
            results['user_data'] = user_data
            print(f"  用户历史: {len(user_data.get('history', []))} 条")
            
            # 智能利用用户画像增强检索
            prefs = user_data.get('preferences', {})
            print(f"  用户偏好数据: {prefs}")
            
            # 检测是否是明确的用户偏好查询
            user_preference_keywords = ['我的口味', '符合我', '适合我', '我的偏好', '我的习惯']
            is_explicit_preference_query = any(kw in query for kw in user_preference_keywords)
            print(f"  是否明确偏好查询: {is_explicit_preference_query} (查询: '{query}')")
            
            # 检测是否是推荐查询且没有明确指定口味/标签
            is_general_recommend = (intent == 'recommend' and 
                                   not entities.get('flavors') and 
                                   not entities.get('tags') and
                                   not entities.get('ingredients'))
            print(f"  是否一般性推荐: {is_general_recommend} (intent={intent}, entities={entities})")
            
            # 在以下情况使用用户画像增强检索：
            # 1. 明确的用户偏好查询（"推荐符合我口味的"）
            # 2. 一般性推荐查询且用户有偏好（"推荐一些菜"）
            should_use_profile = is_explicit_preference_query or (is_general_recommend and (prefs.get('flavors') or prefs.get('tags')))
            print(f"  是否应用用户画像: {should_use_profile}")
            
            if should_use_profile:
                if is_explicit_preference_query:
                    print("  ✅ 检测到明确的用户偏好查询，使用历史偏好...")
                else:
                    print("  ✅ 一般性推荐查询，自动应用用户画像...")
                
                # 根据用户偏好的口味检索
                if prefs.get('flavors'):
                    print(f"    🌶️  应用口味偏好: {prefs['flavors']}")
                    for flavor in prefs['flavors']:
                        dishes = self.graph_retriever.search_by_flavor(flavor, limit=5)
                        print(f"      找到 {len(dishes)} 道 {flavor}味 菜品")
                        for d in dishes:
                            # 明确查询时权重更高
                            weight = 0.98 if is_explicit_preference_query else 0.88
                            reason = f"符合你的口味偏好:{flavor}" if is_explicit_preference_query else f"推荐(你喜欢{flavor}味)"
                            graph_hits.append((d['dish'], weight, reason))
                
                # 根据用户偏好的标签检索
                if prefs.get('tags'):
                    print(f"    🏷️  应用习惯标签: {prefs['tags']}")
                    for tag in prefs['tags']:
                        # 使用 Tag 检索
                        try:
                            dishes = self.graph_retriever.search_by_tag(tag, limit=3)
                            print(f"      找到 {len(dishes)} 道适合 {tag} 的菜品")
                            for d in dishes:
                                weight = 0.92 if is_explicit_preference_query else 0.82
                                reason = f"符合你的习惯:{tag}" if is_explicit_preference_query else f"推荐(适合{tag})"
                                graph_hits.append((d['dish'], weight, reason))
                        except Exception as e:
                            print(f"      标签 {tag} 检索失败: {e}")
                
                # 根据用户偏好的食材检索（仅在明确查询时）
                if is_explicit_preference_query and prefs.get('ingredients'):
                    print(f"    🥬 应用食材偏好: {prefs['ingredients']}")
                    for ingredient in prefs['ingredients']:
                        dishes = self.graph_retriever.search_by_ingredient(ingredient, limit=3)
                        print(f"      找到 {len(dishes)} 道包含 {ingredient} 的菜品")
                        for d in dishes:
                            graph_hits.append((d['dish'], 0.85, f"包含你喜欢的食材:{ingredient}"))
                
                # 更新图谱结果
                results['graph_results'] = graph_hits
                print(f"  ✅ 基于用户画像检索到 {len(graph_hits)} 条结果")
            else:
                print(f"  ℹ️  不需要应用用户画像")
        
        # 3.6 场景标签检索（无需登录）
        scene_keywords = ["熬夜", "加班", "便当", "聚餐", "健身", "减脂"]
        if any(kw in query for kw in scene_keywords):
            print("\nStep 3.6: 场景标签检索...")
            scene_results = self.advanced_recommender.search_by_scene_tags(query, limit=5)
            if scene_results:
                results['scene_recommendations'] = scene_results
                # 将场景推荐加入图谱结果
                for item in scene_results:
                    graph_hits.append((item['dish'], 0.95, f"场景匹配:{item['reason']}"))
                results['graph_results'] = graph_hits
                print(f"  场景推荐: {len(scene_results)} 个")
        
        # 4. 结果融合
        print("\nStep 4: 结果融合...")
        
        # 检测是否是用户偏好查询（用于调整权重）
        is_preference_query = user_id and any(kw in query for kw in ['符合我', '适合我', '我的口味', '我的偏好'])
        
        # 检测是否包含明确菜品类型（用于调整权重）
        has_dish_type = bool(entities.get('dishes'))
        
        combined = self._combine_results(
            results['vector_results'],
            results['graph_results'],
            top_k=top_k,
            prefer_graph=is_preference_query,  # 偏好查询时优先图谱结果
            has_dish_type=has_dish_type  # 有菜品类型时优先向量结果
        )
        results['combined_results'] = combined
        print(f"  融合后 Top-{len(combined)} 结果 (偏好查询模式: {is_preference_query})")
        
        # 5. 获取详细信息
        for dish_name, score, reason in combined:
            if dish_name not in results['context']:
                info = self.graph_retriever.search_by_dish(dish_name, depth=1)
                results['context'][dish_name] = info
        
        # 6. 高级推荐功能（如果提供user_id）
        if user_id:
            print(f"\nStep 6: 高级推荐...")
            
            # 6.1 场景标签检索
            scene_keywords = ["熬夜", "加班", "便当", "聚餐", "健身", "减脂"]
            if any(kw in query for kw in scene_keywords):
                print("  检测到场景关键词，启用场景推荐...")
                scene_results = self.advanced_recommender.search_by_scene_tags(query, limit=3)
                if scene_results:
                    results['scene_recommendations'] = scene_results
                    print(f"  场景推荐: {len(scene_results)} 个")
            
            # 7.2 做菜助手检测
            cooking_keywords = ["切好了", "下一步", "接下来", "然后呢", "怎么继续"]
            if any(kw in query for kw in cooking_keywords):
                print("  检测到做菜助手请求...")
                # 尝试从上下文或实体中获取菜品名
                if entities.get('dishes'):
                    dish = entities['dishes'][0]
                    guidance = self.advanced_recommender.get_cooking_guidance(user_id, dish, query)
                    results['cooking_guidance'] = guidance
                    print(f"  做菜指导: {dish}")
            
            # 7.3 智能推荐（推荐意图时）
            if intent == 'recommend':
                print("  启用智能推荐...")
                # 推荐未尝试的菜
                unexplored = self.advanced_recommender.recommend_unexplored_dishes(user_id, limit=3)
                if unexplored:
                    results['unexplored_recommendations'] = unexplored
                    print(f"  未尝试推荐: {len(unexplored)} 个")
                
                # 推荐相似菜品（带解释）
                similar = self.advanced_recommender.recommend_similar_with_explanation(user_id, limit=3)
                if similar:
                    results['similar_recommendations'] = similar
                    print(f"  相似推荐: {len(similar)} 个")
        
        return results
    
    def _combine_results(self, vector_results, graph_results, top_k=5, prefer_graph=False, has_dish_type=False):
        """
        融合向量检索和图谱检索结果
        
        Args:
            vector_results: 向量检索结果 [(dish, score), ...]
            graph_results: 图谱检索结果 [(dish, score, reason), ...]
            top_k: 返回Top-K
            prefer_graph: 是否优先图谱结果（用于偏好查询）
            has_dish_type: 是否包含明确菜品类型（如"蛋糕"、"汤"等）
        
        Returns:
            List[Tuple[str, float, str]]: [(dish, score, reason), ...]
        """
        scores = defaultdict(lambda: {'score': 0.0, 'reasons': []})
        
        # 动态调整权重
        if prefer_graph:
            # 偏好查询：图谱权重0.85，向量权重0.15
            vector_weight = 0.15
            graph_weight = 0.85
            print(f"  [权重] 偏好查询模式 - 图谱:{graph_weight}, 向量:{vector_weight}")
        elif has_dish_type:
            # 有明确菜品类型：向量权重0.7，图谱权重0.3（向量检索更准确）
            vector_weight = 0.7
            graph_weight = 0.3
            print(f"  [权重] 菜品类型查询模式 - 向量:{vector_weight}, 图谱:{graph_weight}")
        else:
            # 普通查询：图谱权重0.6，向量权重0.4
            vector_weight = 0.4
            graph_weight = 0.6
            print(f"  [权重] 普通查询模式 - 图谱:{graph_weight}, 向量:{vector_weight}")
        
        # 向量结果
        if vector_results:
            max_vec_score = max(score for _, score in vector_results) if vector_results else 1.0
            for dish, score in vector_results:
                normalized_score = (score / max_vec_score) * vector_weight
                scores[dish]['score'] += normalized_score
                scores[dish]['reasons'].append(f"语义相似度:{score:.2f}")
        
        # 图谱结果
        if graph_results:
            max_graph_score = max(score for _, score, _ in graph_results) if graph_results else 1.0
            for dish, score, reason in graph_results:
                normalized_score = (score / max_graph_score) * graph_weight
                scores[dish]['score'] += normalized_score
                scores[dish]['reasons'].append(reason)
        
        # 转换为列表并排序
        combined = [
            (dish, data['score'], '; '.join(data['reasons']))
            for dish, data in scores.items()
        ]
        combined.sort(key=lambda x: x[1], reverse=True)
        
        # 打印Top结果用于调试
        print(f"  [融合] Top-{min(5, len(combined))} 结果:")
        for i, (dish, score, reason) in enumerate(combined[:5], 1):
            print(f"    {i}. {dish} (分数:{score:.3f}) - {reason[:50]}...")
        
        return combined[:top_k]
    
    def generate_answer(self, query, retrieval_results, user_id=None):
        """
        基于检索结果生成答案
        
        Args:
            query: 用户查询
            retrieval_results: 检索结果
            user_id: 用户ID（可选）
        
        Returns:
            str: 生成的答案
        """
        # 构建上下文
        context_parts = []
        
        # 添加检索到的菜品信息
        for dish_name, score, reason in retrieval_results['combined_results']:
            info = retrieval_results['context'].get(dish_name, {})
            
            parts = [f"【{dish_name}】"]
            parts.append(f"推荐理由: {reason}")
            parts.append(f"相关度: {score:.2f}")
            
            if info.get('difficulty'):
                parts.append(f"难度: {'★' * info['difficulty']}")
            
            if info.get('ingredients'):
                parts.append(f"主要食材: {', '.join(info['ingredients'][:5])}")
            
            if info.get('condiments'):
                parts.append(f"调料: {', '.join(info['condiments'][:5])}")
            
            if info.get('tags'):
                parts.append(f"标签: {', '.join(info['tags'])}")
            
            if info.get('flavors'):
                parts.append(f"口味: {', '.join(info['flavors'])}")
            
            if info.get('scenes'):
                parts.append(f"适合场景: {', '.join(info['scenes'])}")
            
            if info.get('steps'):
                parts.append(f"制作步骤:\n{info['steps']}")
            
            if info.get('tips'):
                parts.append(f"烹饪技巧:\n{info['tips']}")
            
            context_parts.append('\n'.join(parts))
        
        context_text = '\n\n'.join(context_parts)
        
        # 添加用户信息
        user_context = ""
        if user_id and 'user_data' in retrieval_results:
            user_data = retrieval_results['user_data']
            if user_data.get('history'):
                history_dishes = [h['dish'] for h in user_data['history'][:5]]
                user_context = f"\n用户历史: 做过 {', '.join(history_dishes)}"
            
            prefs = user_data.get('preferences', {})
            if prefs.get('flavors'):
                user_context += f"\n用户偏好口味: {', '.join(prefs['flavors'])}"
            if prefs.get('tags'):
                user_context += f"\n用户偏好标签: {', '.join(prefs['tags'])}"
        
        # 添加高级推荐信息
        advanced_context = ""
        
        # 场景推荐
        if retrieval_results.get('scene_recommendations'):
            scene_recs = retrieval_results['scene_recommendations']
            dishes = [f"{r['dish']}({r['reason']})" for r in scene_recs[:3]]
            advanced_context += f"\n\n场景推荐: {', '.join(dishes)}"
        
        # 做菜助手
        if retrieval_results.get('cooking_guidance'):
            guidance = retrieval_results['cooking_guidance']
            if not guidance.get('completed'):
                advanced_context += f"\n\n做菜指导:\n当前进度: {guidance['current_progress']}\n下一步: {guidance['next_step']}"
            else:
                advanced_context += f"\n\n做菜指导: {guidance['message']}"
        
        # 未尝试推荐
        if retrieval_results.get('unexplored_recommendations'):
            unexplored = retrieval_results['unexplored_recommendations']
            dishes = [f"{r['dish']}({r['reason']})" for r in unexplored[:3]]
            advanced_context += f"\n\n你还没试过的推荐: {', '.join(dishes)}"
        
        # 相似推荐（带解释）
        if retrieval_results.get('similar_recommendations'):
            similar = retrieval_results['similar_recommendations']
            recs = []
            for r in similar[:3]:
                recs.append(f"{r['recommended_dish']} - {r['explanation']}")
            advanced_context += f"\n\n智能推荐:\n" + '\n'.join(recs)
        
        # 判断查询意图
        intent = retrieval_results.get('optimized', {}).get('intent', 'query_dish')
        
        # 检查图谱检索结果数量
        graph_result_count = len(retrieval_results.get('graph_results', []))
        flavor_query = retrieval_results.get('optimized', {}).get('entities', {}).get('flavors', [])
        
        # 如果是口味查询但图谱结果很少，添加提示
        data_limitation_note = ""
        if flavor_query and graph_result_count < 3:
            if graph_result_count == 0:
                data_limitation_note = f"\n\n⚠️ 注意：知识图谱中暂无标注为'{','.join(flavor_query)}'口味的菜品。以下推荐基于语义相似度，可能不完全符合您的口味需求。"
            else:
                data_limitation_note = f"\n\n⚠️ 注意：知识图谱中仅有{graph_result_count}道标注为'{','.join(flavor_query)}'口味的菜品。其余推荐基于语义相似度。"
        
        # 构建prompt（根据意图调整）
        if intent == 'how_to_cook':
            # 做法查询：重点展示步骤和食材
            prompt = f"""你是一个专业的菜谱助手。用户询问菜品的做法，请基于知识图谱中的信息详细回答。

用户问题: {query}
{user_context}
{advanced_context}

知识图谱中的菜品信息:
{context_text}

请详细回答用户的做法问题。要求:
1. 如果找到了菜品信息，按以下格式回答：
   - 首先列出所需食材和调料
   - 然后详细说明制作步骤（保持原有步骤的完整性）
   - 最后给出烹饪技巧和注意事项
2. 如果有做菜指导信息，优先展示下一步操作
3. 如果没有找到该菜品，说明知识图谱中暂无该菜品信息
4. 语言要清晰、专业、易懂
5. 步骤要详细、具体、可操作

请回答:"""
        else:
            # 推荐查询：展示多个菜品
            prompt = f"""你是一个专业的菜谱助手，基于知识图谱和智能推荐系统回答用户问题。

用户问题: {query}
{user_context}
{advanced_context}

检索到的相关信息:
{context_text}
{data_limitation_note}

请根据以上信息详细回答用户问题。要求:
1. 如果有数据限制提示，必须在回答开头明确告知用户
2. 对于每道推荐的菜品，详细说明：
   - 推荐理由和亮点
   - 主要食材和调料
   - 关键制作步骤或技巧
   - 适合的场景或人群
3. 如果有智能推荐或场景推荐，优先使用这些结果
4. 推荐时要说明理由（如：因为你之前做过XX，这道菜风味相似）
5. 结合用户偏好给出个性化建议
6. 语言要自然、友好、专业，内容要丰富详实

请回答:"""

        # 调用LLM生成答案
        answer, _ = self.model.chat(query=prompt, history=[])
        return answer
    
    def generate_answer_stream(self, query, retrieval_results, user_id=None):
        """
        流式生成答案（用于Streamlit实时显示）
        
        Args:
            query: 用户查询
            retrieval_results: 检索结果
            user_id: 用户ID（可选）
        
        Yields:
            每个token的内容
        """
        # 构建上下文（与generate_answer相同）
        context = retrieval_results.get('context', {})
        
        # 构建上下文文本
        context_parts = []
        for dish_name, info in list(context.items())[:5]:
            parts = [f"【{dish_name}】"]
            
            if info.get('desc'):
                parts.append(f"简介: {info['desc']}")
            
            if info.get('ingredients'):
                ingredients_str = ', '.join(info['ingredients'][:15])
                parts.append(f"食材: {ingredients_str}")
            
            if info.get('condiments'):
                condiments_str = ', '.join(info['condiments'][:15])
                parts.append(f"调料: {condiments_str}")
            
            if info.get('steps'):
                parts.append(f"步骤:\n{info['steps'][:800]}")
            
            if info.get('tips'):
                parts.append(f"烹饪技巧:\n{info['tips']}")
            
            context_parts.append('\n'.join(parts))
        
        context_text = '\n\n'.join(context_parts)
        
        # 添加用户信息
        user_context = ""
        if user_id and 'user_data' in retrieval_results:
            user_data = retrieval_results['user_data']
            if user_data.get('history'):
                history_dishes = [h['dish'] for h in user_data['history'][:5]]
                user_context = f"\n用户历史: 做过 {', '.join(history_dishes)}"
            
            prefs = user_data.get('preferences', {})
            if prefs.get('flavors'):
                user_context += f"\n用户偏好口味: {', '.join(prefs['flavors'])}"
            if prefs.get('tags'):
                user_context += f"\n用户偏好标签: {', '.join(prefs['tags'])}"
        
        # 添加高级推荐信息
        advanced_context = ""
        
        # 场景推荐
        if retrieval_results.get('scene_recommendations'):
            scene_recs = retrieval_results['scene_recommendations']
            dishes = [f"{r['dish']}({r['reason']})" for r in scene_recs[:3]]
            advanced_context += f"\n\n场景推荐: {', '.join(dishes)}"
        
        # 做菜助手
        if retrieval_results.get('cooking_guidance'):
            guidance = retrieval_results['cooking_guidance']
            if not guidance.get('completed'):
                advanced_context += f"\n\n做菜指导:\n当前进度: {guidance['current_progress']}\n下一步: {guidance['next_step']}"
            else:
                advanced_context += f"\n\n做菜指导: {guidance['message']}"
        
        # 未尝试推荐
        if retrieval_results.get('unexplored_recommendations'):
            unexplored = retrieval_results['unexplored_recommendations']
            dishes = [f"{r['dish']}({r['reason']})" for r in unexplored[:3]]
            advanced_context += f"\n\n你还没试过的推荐: {', '.join(dishes)}"
        
        # 相似推荐（带解释）
        if retrieval_results.get('similar_recommendations'):
            similar = retrieval_results['similar_recommendations']
            recs = []
            for r in similar[:3]:
                recs.append(f"{r['recommended_dish']} - {r['explanation']}")
            advanced_context += f"\n\n智能推荐:\n" + '\n'.join(recs)
        
        # 判断查询意图
        intent = retrieval_results.get('optimized', {}).get('intent', 'query_dish')
        
        # 检查图谱检索结果数量
        graph_result_count = len(retrieval_results.get('graph_results', []))
        flavor_query = retrieval_results.get('optimized', {}).get('entities', {}).get('flavors', [])
        
        # 如果是口味查询但图谱结果很少，添加提示
        data_limitation_note = ""
        if flavor_query and graph_result_count < 3:
            if graph_result_count == 0:
                data_limitation_note = f"\n\n⚠️ 注意：知识图谱中暂无标注为'{','.join(flavor_query)}'口味的菜品。以下推荐基于语义相似度，可能不完全符合您的口味需求。"
            else:
                data_limitation_note = f"\n\n⚠️ 注意：知识图谱中仅有{graph_result_count}道标注为'{','.join(flavor_query)}'口味的菜品。其余推荐基于语义相似度。"
        
        # 构建prompt（根据意图调整）
        if intent == 'how_to_cook':
            # 做法查询：重点展示步骤和食材
            prompt = f"""你是一个专业的菜谱助手。用户询问菜品的做法，请基于知识图谱中的信息详细回答。

用户问题: {query}
{user_context}
{advanced_context}

知识图谱中的菜品信息:
{context_text}

请详细回答用户的做法问题。要求:
1. 如果找到了菜品信息，按以下格式回答：
   - 首先列出所需食材和调料
   - 然后详细说明制作步骤（保持原有步骤的完整性）
   - 最后给出烹饪技巧和注意事项
2. 如果有做菜指导信息，优先展示下一步操作
3. 如果没有找到该菜品，说明知识图谱中暂无该菜品信息
4. 语言要清晰、专业、易懂
5. 步骤要详细、具体、可操作

请回答:"""
        else:
            # 推荐查询：展示多个菜品
            prompt = f"""你是一个专业的菜谱助手，基于知识图谱和智能推荐系统回答用户问题。

用户问题: {query}
{user_context}
{advanced_context}

检索到的相关信息:
{context_text}
{data_limitation_note}

请根据以上信息详细回答用户问题。要求:
1. 如果有数据限制提示，必须在回答开头明确告知用户
2. 对于每道推荐的菜品，详细说明：
   - 推荐理由和亮点
   - 主要食材和调料
   - 关键制作步骤或技巧
   - 适合的场景或人群
3. 如果有智能推荐或场景推荐符合问题需求，优先使用这些结果
4. 推荐时要说明理由（如：因为你之前做过XX，这道菜风味相似）
5. 结合用户偏好给出个性化建议，但如果当前用户提问与偏好冲突，优先考虑回答用户问题
6. 语言要自然、友好、专业，内容要丰富详实

请回答:"""

        # 调用LLM流式生成答案
        for token in self.model.chat(query=prompt, history=[], stream=True):
            yield token
    
    def chat(self, query, user_id=None):
        """
        完整的问答流程
        
        Args:
            query: 用户查询
            user_id: 用户ID（可选）
        
        Returns:
            str: 答案
        """
        print("=" * 60)
        print(f"用户查询: {query}")
        print("=" * 60)
        
        # 检索
        results = self.retrieve(query, user_id=user_id, top_k=5)
        
        # 生成答案
        print("\nStep 6: 生成答案...")
        answer = self.generate_answer(query, results, user_id=user_id)
        
        return answer


if __name__ == "__main__":
    print("=" * 60)
    print("图RAG系统测试")
    print("=" * 60)
    
    # 初始化系统
    system = GraphRAGSystem(use_vector=True)
    
    # 测试查询
    test_queries = [
        "我今天加班熬夜，推荐一些快速的菜",
        "鸡肉可以做什么菜？",
        "宫保鸡丁怎么做？",
        "有什么清淡的汤？",
        "推荐一些简单的家常菜"
    ]
    
    for query in test_queries:
        print("\n" + "=" * 60)
        answer = system.chat(query)
        print("\n答案:")
        print(answer)
        print("=" * 60)
        input("\n按回车继续下一个测试...")
