# coding = utf-8
"""
子图展示组件（Streamlit版本）
为RecipeQA系统提供可视化子图查询功能
"""

import streamlit as st
from typing import Dict, Any, Optional
import streamlit.components.v1 as components
from subgraph_api import SubgraphAPI


class SubgraphViewer:
    """子图展示组件"""
    
    # 子图类型配置
    SUBGRAPH_TYPES = {
        "Dish": {
            "label": "Dish 子图",
            "placeholder": "请输入菜品名称（如：宫保鸡丁）",
            "description": "查看菜品的食材、调料、标签、口味等信息"
        },
        "Ingredient": {
            "label": "Ingredient 子图",
            "placeholder": "请输入食材名称（如：鸡肉）",
            "description": "查看该食材可以做哪些菜"
        },
        "Tag": {
            "label": "Tag 子图",
            "placeholder": "请输入标签名称（如：快手菜、熬夜）",
            "description": "查看具有该标签的菜品"
        },
        "Flavor": {
            "label": "Flavor 子图",
            "placeholder": "请输入口味名称（如：清淡、麻辣）",
            "description": "查看具有该口味的菜品"
        },
        "Similar": {
            "label": "Similar Dish 子图",
            "placeholder": "请输入菜品名称（如：番茄炒蛋）",
            "description": "查找与该菜品相似的其他菜品"
        },
        "UserPreference": {
            "label": "User Preference 子图",
            "placeholder": "请输入 user_id（如：user123）",
            "description": "查看用户的历史记录和偏好"
        },
        "MultiHop": {
            "label": "Multi-hop 子图",
            "placeholder": "请输入起点实体或多节点描述",
            "description": "多跳图谱查询（实验性功能）"
        }
    }
    
    def __init__(self, unique_id: str = "default", retrieval_results: dict = None):
        self.api = SubgraphAPI()
        self.unique_id = unique_id
        self.retrieval_results = retrieval_results or {}
        
        # 初始化session state
        if 'subgraph_visible' not in st.session_state:
            st.session_state.subgraph_visible = {}
        if 'subgraph_data' not in st.session_state:
            st.session_state.subgraph_data = {}
    
    def _extract_entities(self):
        """从检索结果中提取实体"""
        entities = {
            'dishes': [],
            'ingredients': [],
            'tags': [],
            'flavors': []
        }
        
        if not self.retrieval_results:
            return entities
        
        # 从优化后的查询中提取实体
        optimized = self.retrieval_results.get('optimized', {})
        if optimized:
            opt_entities = optimized.get('entities', {})
            entities['dishes'] = opt_entities.get('dishes', [])
            entities['ingredients'] = opt_entities.get('ingredients', [])
            entities['tags'] = opt_entities.get('scenes', [])  # scenes 对应 tags
            entities['flavors'] = opt_entities.get('flavors', [])
        
        # 从检索结果中提取菜品
        combined_results = self.retrieval_results.get('combined_results', [])
        for dish, score, reason in combined_results[:5]:
            if dish and dish not in entities['dishes']:
                entities['dishes'].append(dish)
        
        return entities
    
    def render(self):
        """渲染子图查询组件"""
        
        # 提取实体
        entities = self._extract_entities()
        
        # 如果没有实体，不显示组件
        if not any(entities.values()):
            return
        
        # 添加分隔线
        st.markdown("---")
        
        # 组件标题
        st.markdown("### 🔍 子图探索")
        
        # 显示可用实体
        st.markdown("**📌 本次对话涉及的实体：**")
        
        # 创建实体按钮网格
        entity_buttons = []
        
        # 菜品实体
        if entities['dishes']:
            st.markdown(f"**🍽️ 菜品** ({len(entities['dishes'])}个)")
            cols = st.columns(min(len(entities['dishes']), 5))
            for idx, dish in enumerate(entities['dishes'][:10]):
                with cols[idx % 5]:
                    if st.button(f"📊 {dish}", key=f"dish_btn_{self.unique_id}_{idx}", help="查看菜品子图"):
                        self._query_and_show_subgraph("Dish", dish)
        
        # 食材实体
        if entities['ingredients']:
            st.markdown(f"**🥩 食材** ({len(entities['ingredients'])}个)")
            cols = st.columns(min(len(entities['ingredients']), 5))
            for idx, ingredient in enumerate(entities['ingredients'][:10]):
                with cols[idx % 5]:
                    if st.button(f"🔍 {ingredient}", key=f"ing_btn_{self.unique_id}_{idx}", help="查看食材子图"):
                        self._query_and_show_subgraph("Ingredient", ingredient)
        
        # 标签实体
        if entities['tags']:
            st.markdown(f"**🏷️ 标签** ({len(entities['tags'])}个)")
            cols = st.columns(min(len(entities['tags']), 5))
            for idx, tag in enumerate(entities['tags'][:10]):
                with cols[idx % 5]:
                    if st.button(f"🔖 {tag}", key=f"tag_btn_{self.unique_id}_{idx}", help="查看标签子图"):
                        self._query_and_show_subgraph("Tag", tag)
        
        # 口味实体
        if entities['flavors']:
            st.markdown(f"**🌶️ 口味** ({len(entities['flavors'])}个)")
            cols = st.columns(min(len(entities['flavors']), 5))
            for idx, flavor in enumerate(entities['flavors'][:10]):
                with cols[idx % 5]:
                    if st.button(f"👅 {flavor}", key=f"flavor_btn_{self.unique_id}_{idx}", help="查看口味子图"):
                        self._query_and_show_subgraph("Flavor", flavor)
        
        # 显示子图弹窗
        if st.session_state.subgraph_visible.get(self.unique_id, False) and st.session_state.subgraph_data.get(self.unique_id):
            self._render_subgraph_modal()
    
    def _query_and_show_subgraph(self, subgraph_type: str, entity: str):
        """查询并显示子图"""
        with st.spinner(f"正在查询 {subgraph_type} 子图..."):
            # 调用API查询
            result = self.api.query_subgraph(subgraph_type, entity, depth=1)
            
            if result.get('error'):
                st.error(f"查询失败: {result['error']}")
                return
            
            if not result.get('nodes'):
                st.warning("未找到相关数据")
                return
            
            # 保存数据并显示（使用unique_id作为key）
            st.session_state.subgraph_data[self.unique_id] = {
                'type': subgraph_type,
                'entity': entity,
                'result': result
            }
            st.session_state.subgraph_visible[self.unique_id] = True
            st.rerun()
    
    def _render_subgraph_modal(self):
        """渲染子图可视化弹窗"""
        data = st.session_state.subgraph_data.get(self.unique_id)
        
        if not data:
            return
        
        # 使用expander作为可关闭的弹窗
        with st.expander(
            f"📊 {data['type']} 子图: {data['entity']}", 
            expanded=True
        ):
            # 关闭按钮（使用唯一key）
            if st.button("❌ 关闭", key=f"close_subgraph_btn_{self.unique_id}"):
                st.session_state.subgraph_visible[self.unique_id] = False
                st.session_state.subgraph_data[self.unique_id] = None
                st.rerun()
            
            # 显示统计信息
            result = data['result']
            col1, col2 = st.columns(2)
            with col1:
                st.metric("节点数", len(result['nodes']))
            with col2:
                st.metric("边数", len(result['edges']))
            
            # 渲染图可视化
            self._render_graph(result)
    
    def _render_graph(self, graph_data: Dict[str, Any]):
        """渲染图可视化（使用vis-network）"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        if not nodes:
            st.info("没有可显示的节点")
            return
        
        # 生成vis-network HTML
        html_content = self._generate_vis_network_html(nodes, edges)
        
        # 使用Streamlit components渲染
        components.html(html_content, height=600, scrolling=False)
    
    def _generate_vis_network_html(self, nodes: list, edges: list) -> str:
        """生成vis-network的HTML代码"""
        
        # 定义节点颜色映射
        color_map = {
            "dish": "#FF6B6B",
            "ingredient": "#4ECDC4",
            "condiment": "#95E1D3",
            "tag": "#F38181",
            "flavor": "#AA96DA",
            "user": "#FCBAD3",
            "feature": "#FFFFD2"
        }
        
        # 转换节点数据
        nodes_json = []
        for node in nodes:
            color = color_map.get(node.get('group', 'default'), "#CCCCCC")
            nodes_json.append({
                "id": node['id'],
                "label": node['label'],
                "color": color,
                "font": {"size": 14, "color": "#333333"},
                "shape": "dot",
                "size": 20 if node.get('type') == 'Dish' else 15
            })
        
        # 转换边数据
        edges_json = []
        for edge in edges:
            edges_json.append({
                "from": edge['from'],
                "to": edge['to'],
                "label": edge.get('label', ''),
                "arrows": "to",
                "font": {"size": 10, "align": "middle"}
            })
        
        # 生成HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <style type="text/css">
                #mynetwork {{
                    width: 100%;
                    height: 550px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background-color: #fafafa;
                }}
            </style>
        </head>
        <body>
            <div id="mynetwork"></div>
            <script type="text/javascript">
                var nodes = new vis.DataSet({nodes_json});
                var edges = new vis.DataSet({edges_json});
                
                var container = document.getElementById('mynetwork');
                var data = {{
                    nodes: nodes,
                    edges: edges
                }};
                
                var options = {{
                    nodes: {{
                        borderWidth: 2,
                        borderWidthSelected: 3,
                        shadow: true
                    }},
                    edges: {{
                        width: 2,
                        color: {{color: '#848484', highlight: '#FF6B6B'}},
                        smooth: {{
                            type: 'continuous',
                            roundness: 0.5
                        }}
                    }},
                    physics: {{
                        enabled: true,
                        stabilization: {{
                            iterations: 200
                        }},
                        barnesHut: {{
                            gravitationalConstant: -8000,
                            centralGravity: 0.3,
                            springLength: 150,
                            springConstant: 0.04
                        }}
                    }},
                    interaction: {{
                        hover: true,
                        tooltipDelay: 200,
                        navigationButtons: true,
                        keyboard: true
                    }}
                }};
                
                var network = new vis.Network(container, data, options);
                
                // 节点点击事件
                network.on("click", function(params) {{
                    if (params.nodes.length > 0) {{
                        var nodeId = params.nodes[0];
                        var node = nodes.get(nodeId);
                        console.log("Clicked node:", node);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html.replace("{nodes_json}", str(nodes_json).replace("'", '"')) \
                   .replace("{edges_json}", str(edges_json).replace("'", '"'))


def render_subgraph_viewer(unique_id: str = "default", retrieval_results: dict = None):
    """便捷函数：渲染子图查看器
    
    Args:
        unique_id: 唯一标识符，用于区分多个实例
        retrieval_results: 检索结果，包含识别的实体信息
    """
    viewer = SubgraphViewer(unique_id=unique_id, retrieval_results=retrieval_results)
    viewer.render()


if __name__ == "__main__":
    # 测试组件
    st.set_page_config(page_title="子图查看器测试", layout="wide")
    st.title("子图查看器测试")
    
    render_subgraph_viewer()
