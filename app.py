# coding = utf-8
"""
RecipeQA 图RAG系统 - Streamlit前端
基于知识图谱的智能菜谱问答与推荐系统
"""

import streamlit as st
from typing import List, Dict, Optional
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph_rag_system import GraphRAGSystem
from user_manager import UserManager
from subgraph_viewer import render_subgraph_viewer


# 页面配置
st.set_page_config(
    page_title="RecipeQA 智能菜谱助手",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4ECDC4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .user-info {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stat-box {
        background-color: #e8f4f8;
        padding: 0.8rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #FF6B6B;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def load_graph_rag_system(use_vector=True, use_deepseek=False):
    """加载图RAG系统（缓存）"""
    try:
        if use_deepseek:
            # 使用DeepSeek API
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            if not api_key:
                st.error("❌ 请设置环境变量 DEEPSEEK_API_KEY")
                return None
            
            system = GraphRAGSystem(
                use_vector=use_vector,
                use_deepseek=True,
                api_key=api_key
            )
        else:
            # 使用本地模拟服务
            system = GraphRAGSystem(
                model_url="http://localhost:3001/generate",
                use_vector=use_vector
            )
        return system
    except Exception as e:
        st.error(f"系统加载失败：{e}")
        return None


def init_session_state():
    """初始化会话状态"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()
    
    if 'last_retrieval_results' not in st.session_state:
        st.session_state.last_retrieval_results = None


def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.markdown("## 🍳 RecipeQA")
    st.sidebar.markdown("### 智能菜谱助手")
    
    # 用户登录区域
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 用户登录")
    
    if st.session_state.user_id is None:
        # 未登录状态
        user_id = st.sidebar.text_input("用户ID", placeholder="输入您的用户ID")
        user_name = st.sidebar.text_input("昵称（可选）", placeholder="输入您的昵称")
        
        if st.sidebar.button("登录", type="primary"):
            if user_id:
                try:
                    user_info = st.session_state.user_manager.login_or_create_user(
                        user_id, 
                        user_name if user_name else None
                    )
                    st.session_state.user_id = user_id
                    st.session_state.user_info = user_info
                    
                    # 添加欢迎消息
                    welcome_msg = f"欢迎{'回来' if not user_info['is_new'] else ''}，{user_info['name']}！"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": welcome_msg
                    })
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"登录失败：{e}")
            else:
                st.sidebar.warning("请输入用户ID")
    else:
        # 已登录状态
        user_info = st.session_state.user_info
        
        st.sidebar.markdown(f"""
        <div class="user-info">
            <h4>👤 {user_info['name']}</h4>
            <p>ID: {user_info['user_id']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 用户统计
        stats = st.session_state.user_manager.get_user_stats(st.session_state.user_id)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{stats['searched']}</div>
                <div class="stat-label">搜索过</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{stats['cooked']}</div>
                <div class="stat-label">做过</div>
            </div>
            """, unsafe_allow_html=True)
        
        col3, col4 = st.sidebar.columns(2)
        with col3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{stats['liked']}</div>
                <div class="stat-label">喜欢</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{stats['total_searches']}</div>
                <div class="stat-label">总搜索</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 退出登录
        if st.sidebar.button("退出登录"):
            st.session_state.user_id = None
            st.session_state.user_info = None
            st.session_state.messages = []
            st.rerun()
    
    # 功能说明
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 使用提示")
    st.sidebar.markdown("""
    **提问示例：**
    - 我今天加班熬夜，推荐一些快速的菜
    - 鸡肉可以做什么菜？
    - 宫保鸡丁怎么做？
    - 有什么清淡的汤？
    
    **快捷命令：**
    - `cooked:菜名` - 记录做过的菜
    - `liked:菜名` - 记录喜欢的菜
    - `history` - 查看历史记录
    """)
    
    # 系统配置
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ 系统配置")
    
    # LLM配置（默认使用DeepSeek）
    use_deepseek = True
    
    if os.environ.get('DEEPSEEK_API_KEY'):
        st.sidebar.success("✅ DeepSeek API 已配置")
    else:
        st.sidebar.error("❌ 请设置环境变量 DEEPSEEK_API_KEY")
        st.sidebar.code("set DEEPSEEK_API_KEY=your_key_here", language="bash")
        use_deepseek = False  # 如果没有API密钥，回退到本地模式
    
    # 检查向量检索状态
    vector_status = "✅ 已启用" if os.path.exists("data/vector_index.pkl") else "❌ 未启用"
    st.sidebar.markdown(f"**向量检索：** {vector_status}")
    
    # LLM服务状态
    if not use_deepseek:
        try:
            import requests
            response = requests.get("http://localhost:3001", timeout=1)
            llm_status = "✅ 运行中"
        except:
            llm_status = "❌ 未启动"
        st.sidebar.markdown(f"**本地LLM：** {llm_status}")
    
    # 显示RAG检索信息（调试用）
    if st.session_state.last_retrieval_results:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 RAG检索信息")
        
        results = st.session_state.last_retrieval_results
        
        # 显示优化后的查询
        if results.get('optimized'):
            with st.sidebar.expander("📝 查询优化", expanded=False):
                opt = results['optimized']
                st.write(f"**原始查询：** {results.get('query', '')}")
                st.write(f"**优化查询：** {opt.get('optimized_query', '')}")
                st.write(f"**意图：** {opt.get('intent', '')}")
                if opt.get('entities'):
                    st.json(opt['entities'])
        
        # 显示检索结果
        if results.get('combined_results'):
            with st.sidebar.expander("🎯 检索结果", expanded=False):
                for i, (dish, score, reason) in enumerate(results['combined_results'][:5], 1):
                    st.write(f"**{i}. {dish}**")
                    st.write(f"相关度: {score:.3f}")
                    st.write(f"理由: {reason}")
                    st.write("---")
        
        # 显示传递给LLM的完整RAG信息
        if results.get('context'):
            with st.sidebar.expander("📄 传递给LLM的RAG信息", expanded=True):
                for dish_name, info in list(results['context'].items())[:3]:
                    st.markdown(f"### 【{dish_name}】")
                    
                    # 食材
                    if info.get('ingredients'):
                        st.markdown("**食材：**")
                        st.text('\n'.join([f"- {ing}" for ing in info['ingredients'][:10]]))
                    
                    # 调料
                    if info.get('condiments'):
                        st.markdown("**调料：**")
                        st.text('\n'.join([f"- {cond}" for cond in info['condiments'][:10]]))
                    
                    # 步骤
                    if info.get('steps'):
                        st.markdown("**步骤：**")
                        st.text(info['steps'][:500] + "..." if len(info['steps']) > 500 else info['steps'])
                    
                    # 技巧
                    if info.get('tips'):
                        st.markdown("**技巧：**")
                        st.text(info['tips'][:300] + "..." if len(info['tips']) > 300 else info['tips'])
                    
                    st.markdown("---")
        
        # 显示用户历史
        if results.get('user_data'):
            with st.sidebar.expander("👤 用户历史", expanded=False):
                user_data = results['user_data']
                if user_data.get('history'):
                    st.write("**做过的菜：**")
                    for h in user_data['history'][:5]:
                        st.write(f"- {h['dish']}")
                if user_data.get('preferences'):
                    st.write("**偏好：**")
                    st.json(user_data['preferences'])
    
    return use_deepseek


def handle_special_commands(user_input: str) -> Optional[str]:
    """处理特殊命令"""
    if not st.session_state.user_id:
        return "请先登录后再使用此功能"
    
    user_mgr = st.session_state.user_manager
    user_id = st.session_state.user_id
    
    # 记录做过的菜
    if user_input.startswith("cooked:"):
        parts = user_input.split(":")
        dish = parts[1].strip()
        rating = None
        if len(parts) > 2:
            try:
                rating = int(parts[2].strip())
            except:
                pass
        
        user_mgr.record_cooked(user_id, dish, rating)
        return f"✅ 已记录：你做过【{dish}】" + (f"，评分：{'⭐' * rating}" if rating else "")
    
    # 记录喜欢的菜
    if user_input.startswith("liked:"):
        dish = user_input.split(":")[1].strip()
        user_mgr.record_liked(user_id, dish)
        return f"✅ 已记录：你喜欢【{dish}】"
    
    # 查看历史
    if user_input.lower() == "history":
        history = user_mgr.get_user_history(user_id)
        
        result = "### 📊 您的历史记录\n\n"
        
        if history['searched']:
            result += "**搜索过的菜：**\n"
            for h in history['searched'][:10]:
                result += f"- {h['dish']} (搜索{h['count']}次)\n"
            result += "\n"
        
        if history['cooked']:
            result += "**做过的菜：**\n"
            for h in history['cooked'][:10]:
                rating_str = f" {'⭐' * h['rating']}" if h.get('rating') else ""
                result += f"- {h['dish']}{rating_str}\n"
            result += "\n"
        
        if history['liked']:
            result += "**喜欢的菜：**\n"
            for h in history['liked'][:10]:
                result += f"- {h['dish']}\n"
        
        return result if (history['searched'] or history['cooked'] or history['liked']) else "暂无历史记录"
    
    return None


def main():
    """主函数"""
    init_session_state()
    
    # 标题
    st.markdown('<div class="main-header">🍳 RecipeQA 智能菜谱助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">基于知识图谱的智能问答与推荐系统</div>', unsafe_allow_html=True)
    
    # 渲染侧边栏（获取DeepSeek选项）
    use_deepseek = render_sidebar()
    
    # 加载系统
    with st.spinner("正在加载图RAG系统..."):
        system = load_graph_rag_system(use_vector=True, use_deepseek=use_deepseek)
    
    if system is None:
        st.error("系统加载失败，请检查Neo4j和LLM服务是否启动")
        return
    
    # 显示历史消息
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # 在助手回答后添加子图查看器组件（使用消息索引作为唯一ID）
            if message["role"] == "assistant":
                # 获取该消息对应的检索结果
                retrieval_results = message.get("retrieval_results")
                render_subgraph_viewer(
                    unique_id=f"msg_{idx}",
                    retrieval_results=retrieval_results
                )
    
    # 聊天输入
    if prompt := st.chat_input("请输入您的问题或命令..."):
        # 立即显示用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 处理特殊命令
        special_response = handle_special_commands(prompt)
        
        if special_response:
            # 特殊命令响应
            st.session_state.messages.append({"role": "assistant", "content": special_response})
            with st.chat_message("assistant"):
                st.markdown(special_response)
                # 添加子图查看器（使用最新消息索引）
                render_subgraph_viewer(unique_id=f"msg_{len(st.session_state.messages)-1}")
            
            # 更新统计
            st.rerun()
        else:
            # 正常问答 - 使用流式显示
            with st.chat_message("assistant"):
                # 创建占位符用于显示消息
                message_placeholder = st.empty()
                
                try:
                    # 显示等待消息
                    message_placeholder.markdown("🤔 **正在思考中...**\n\n⏳ 正在优化查询...")
                    
                    # 步骤1：检索
                    retrieval_results = system.retrieve(
                        prompt,
                        user_id=st.session_state.user_id,
                        top_k=5
                    )
                    
                    # 保存检索结果到session state（用于侧边栏显示）
                    st.session_state.last_retrieval_results = retrieval_results
                    
                    # 更新等待消息
                    message_placeholder.markdown("🤔 **正在思考中...**\n\n✅ 查询优化完成\n✅ 知识图谱检索完成\n⏳ 正在生成回答...")
                    
                    # 步骤2：流式生成答案
                    full_answer = ""
                    token_count = 0
                    
                    # 使用流式生成
                    print(f"[DEBUG] 开始流式生成答案...")
                    
                    stream_generator = system.generate_answer_stream(
                        prompt,
                        retrieval_results,
                        user_id=st.session_state.user_id
                    )
                    
                    print(f"[DEBUG] 生成器已创建: {type(stream_generator)}")
                    
                    for token in stream_generator:
                        full_answer += token
                        token_count += 1
                        
                        # 实时更新显示（每收到token就更新）
                        message_placeholder.markdown(full_answer + "▌")
                        
                        # 调试：每10个token打印一次
                        if token_count % 10 == 0:
                            print(f"[DEBUG] 已接收 {token_count} 个 token，当前长度: {len(full_answer)}")
                    
                    print(f"[DEBUG] 流式生成完成！总共 {token_count} 个 token")
                    
                    # 显示最终答案（移除光标）
                    message_placeholder.markdown(full_answer)
                    
                    # 保存消息和对应的检索结果
                    msg_idx = len(st.session_state.messages)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": full_answer,
                        "retrieval_results": retrieval_results  # 保存检索结果
                    })
                    
                    # 添加子图查看器（传递检索结果）
                    render_subgraph_viewer(
                        unique_id=f"msg_{msg_idx}",
                        retrieval_results=retrieval_results
                    )
                    
                    # 自动记录搜索行为
                    if st.session_state.user_id:
                        st.session_state.user_manager.record_search(
                            st.session_state.user_id,
                            prompt
                        )
                    
                    # 刷新页面以显示侧边栏的RAG信息
                    st.rerun()
                
                except Exception as e:
                    error_msg = f"❌ 发生错误：{str(e)}\n\n```\n{e}\n```"
                    message_placeholder.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
