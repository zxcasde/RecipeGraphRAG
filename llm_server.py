# coding = utf-8
import os
import re
import requests
import json
import time


class ModelAPI():
    """
    LLM模型API封装
    支持两种模式：
    1. 本地模拟服务（MODEL_URL）
    2. DeepSeek API（use_deepseek=True）
    """
    
    def __init__(self, MODEL_URL=None, use_deepseek=False, api_key=None):
        """
        初始化LLM API
        
        Args:
            MODEL_URL: 本地模拟服务URL（如：http://localhost:3001/generate）
            use_deepseek: 是否使用DeepSeek API
            api_key: DeepSeek API密钥（如果use_deepseek=True）
        """
        self.use_deepseek = use_deepseek
        
        if use_deepseek:
            # 使用DeepSeek API
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=api_key or os.environ.get('DEEPSEEK_API_KEY'),
                    base_url="https://api.deepseek.com"
                )
                print("✅ 已连接到DeepSeek API")
            except ImportError:
                print("❌ 错误：请先安装OpenAI SDK: pip install openai")
                raise
            except Exception as e:
                print(f"❌ DeepSeek API初始化失败: {e}")
                raise
        else:
            # 使用本地模拟服务
            self.url = MODEL_URL
            print(f"✅ 已连接到本地LLM服务: {MODEL_URL}")

    def send_request(self, message, history):
        """发送请求到本地模拟服务"""
        data = json.dumps({"message": message, "history": history})
        headers = {'Content-Type': 'application/json'}
        try:
            res = requests.post(self.url, data=data, headers=headers)
            predict = json.loads(res.text)["output"][0]
            history = json.loads(res.text)["history"]
            return predict, history
        except Exception as e:
            print("request error", e)
            return "", []
    
    def chat_with_deepseek(self, query, history=[], stream=False):
        """
        使用DeepSeek API进行对话
        
        Args:
            query: 用户查询
            history: 对话历史
            stream: 是否使用流式生成（返回生成器）
        
        Returns:
            如果stream=False: (answer, new_history)
            如果stream=True: 生成器，yield每个token
        """
        if stream:
            # 流式模式：返回生成器
            return self._chat_stream_generator(query, history)
        else:
            # 非流式模式：返回完整答案
            try:
                # 构建消息列表
                messages = self._build_messages(query, history)
                
                # 调用DeepSeek API
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # 收集完整响应
                answer = ""
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        answer += chunk.choices[0].delta.content
                
                # 更新历史
                new_history = history + [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": answer}
                ]
                
                return answer, new_history
                
            except Exception as e:
                print(f"DeepSeek API调用失败: {e}")
                import traceback
                traceback.print_exc()
                return f"抱歉，API调用失败：{str(e)}", history
    
    def _build_messages(self, query, history):
        """构建消息列表"""
        messages = []
        
        # 添加系统提示
        messages.append({
            "role": "system",
            "content": "你是一个专业的菜谱助手，擅长推荐菜品、解答烹饪问题。回答要专业、友好、简洁。"
        })
        
        # 添加历史对话（如果有）
        for h in history:
            if isinstance(h, dict):
                messages.append(h)
        
        # 添加当前查询
        messages.append({
            "role": "user",
            "content": query
        })
        
        return messages
    
    def _chat_stream_generator(self, query, history):
        """流式生成器（独立方法，避免try-except中的yield问题）"""
        try:
            # 构建消息列表
            messages = self._build_messages(query, history)
            
            print(f"[DEBUG] 开始流式生成，查询长度: {len(query)}")
            
            # 调用DeepSeek API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )
            
            print(f"[DEBUG] API 调用成功，开始接收流式响应")
            
            # 流式返回
            token_count = 0
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    token_count += 1
                    yield content
            
            print(f"[DEBUG] 流式生成完成，共 {token_count} 个 token")
            
        except Exception as e:
            error_msg = f"\n\n❌ 流式传输错误: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            yield error_msg
    
    def _stream_response(self, response, query, history):
        """
        流式响应生成器
        
        Yields:
            每个token的内容
        """
        full_answer = ""
        try:
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_answer += content
                    yield content
            
            # 流结束后，更新历史（通过特殊标记）
            # 注意：调用方需要自己维护历史
            
        except Exception as e:
            yield f"\n\n❌ 流式传输错误: {str(e)}"

    def chat(self, query, history=[], stream=False):
        """
        统一的对话接口
        
        Args:
            query: 用户查询
            history: 对话历史
            stream: 是否使用流式生成（仅DeepSeek支持）
        
        Returns:
            如果stream=False: (response, history): 回答和更新后的历史
            如果stream=True: 生成器，yield每个token
        """
        if self.use_deepseek:
            # 使用DeepSeek API
            return self.chat_with_deepseek(query, history, stream=stream)
        else:
            # 使用本地模拟服务（带重试机制，不支持流式）
            if stream:
                raise NotImplementedError("本地模拟服务不支持流式生成")
            
            message = [{"role": "user", "content": query}]
            count = 0
            response = ''
            while count <= 10:
                try:
                    count += 1
                    response, history = self.send_request(message, history)
                    if response:
                        return response, history
                except Exception as e:
                    print('Exception:', e)
                    time.sleep(1)
            return response, history


if __name__ == '__main__':
    # 测试本地服务
    print("\n=== 测试本地模拟服务 ===")
    model_local = ModelAPI(MODEL_URL="http://localhost:3001/generate")
    res = model_local.chat(query="你好", history=[])
    print(f"回答: {res[0]}")
    
    # 测试DeepSeek API（需要设置环境变量 DEEPSEEK_API_KEY）
    if os.environ.get('DEEPSEEK_API_KEY'):
        print("\n=== 测试DeepSeek API ===")
        model_deepseek = ModelAPI(use_deepseek=True)
        res = model_deepseek.chat(query="推荐一道简单的家常菜", history=[])
        print(f"回答: {res[0]}")
    else:
        print("\n提示：设置环境变量 DEEPSEEK_API_KEY 以测试DeepSeek API")
