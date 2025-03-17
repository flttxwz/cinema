from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests
import json

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        '''这是一个 hello world 指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_str)
        message = ""
        if message_str.startswith('helloworld'):
            index = message_str.find("helloworld")
            if index != -1:
                message = message_str[index + len("helloworld"):]
        logger.info(message_chain)
        logger.info(message)
        # message不为空就搜索
        if message != "":
            plugin = CinemaPlugin()
            # 定义测试消息
            # 调用 process_message 方法处理消息
            # 用于存储去重后的结果
            unique_data = []
            result = plugin.process_message(message)
            if result:
                # 若有结果，打印返回内容
                print("返回内容:", result)
                # 做去重处理
                seen_answers = set()
                for item in result:
                    answer = item['answer']
                    if answer not in seen_answers:
                        # 如果 answer 未出现过，则添加到 unique_data 并记录
                        unique_data.append(item)
                        seen_answers.add(answer)
            logger.info(unique_data)
            # 将结果拼接成字符串
            result_str = ""
            for item1 in unique_data:
                question = item1.get('question')
                answer = item1.get('answer')
                result_str += f"{question}\n{answer}\n\n"
            yield event.plain_result(f"Hello, {user_name}, 给您找到的电影资源 {result_str}!")  # 发送一条纯文本消息

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''


class MessageHandler:
    def handle_message(self, message):
        # 检查消息是否以 "找" 开头
        if message.startswith("helloworld"):
            # 提取关键词，去掉 "找" 字
            keyword = message[1:]
            try:
                # 调用 get_tokens 方法获取令牌
                tokens = self.get_tokens()
            except requests.RequestException as e:
                # 若获取令牌时出现请求异常，返回错误信息
                return f"获取 token 出现错误: {e}"
            # 定义需要请求的 URL 列表
            urls = [
                "http://y.kkkob.com/v/api/getXiaoyu",
                "http://y.kkkob.com/v/api/search",
                "http://y.kkkob.com/v/api/getDJ",
                "http://y.kkkob.com/v/api/getJuzi",
                "http://uukk6.cn/v/api/getTop",
                "http://uukk6.cn/v/api/getDyfx",
                "http://uukk6.cn/v/api/getTTZJB",
                "http://uukk6.cn/v/api/getGirls",
                # "http://uukk6.cn/v/api/getXiaoy",
                # "http://uukk6.cn/v/api/getJuzi",
                "http://uukk6.cn/v/api/getGGang"
            ]
            # 用于存储所有请求的响应结果
            all_responses = []
            for url in urls:
                token = tokens["y.kkkob.com"] if "y.kkkob.com" in url else tokens["uukk6.cn"]
                try:
                    response = self.send_request(url, keyword, token)
                    try:
                        # 尝试将响应内容解析为 JSON
                        data = json.loads(response)
                        if len(data["list"]) != 0:
                            for item in data["list"]:
                                all_responses.append(item)
                    except json.JSONDecodeError:
                        # 若解析失败，将原始响应添加到 all_responses
                        all_responses.append(response)
                except requests.RequestException as e:
                    all_responses.append(f"请求 {url} 出现错误: {e}")
            return all_responses
        # 若消息不以 "找" 开头，返回 None
        return None

    def get_tokens(self):
        # 定义不同域名对应的获取令牌的 URL
        token_urls = {
            "y.kkkob.com": "http://y.kkkob.com/v/api/getToken",
            "uukk6.cn": "http://uukk6.cn/v/api/gettoken"
        }
        # 用于存储不同域名对应的令牌
        tokens = {}
        # 遍历 token_urls 字典
        for domain, url in token_urls.items():
            # 发送 GET 请求获取令牌
            response = requests.get(url)
            # 检查响应状态码，若状态码不是 200，抛出异常
            response.raise_for_status()
            # 从响应的 JSON 数据中提取 token 并存储到 tokens 字典中
            tokens[domain] = response.json().get('token')
        # 返回存储令牌的字典
        return tokens

    def send_request(self, url, keyword, token):
        # 定义请求的数据，包含关键词和令牌
        data = {
            "name": keyword,
            "token": token
        }
        # 发送 POST 请求，携带数据
        response = requests.post(url, data=data)
        # 检查响应状态码，若状态码不是 200，抛出异常
        response.raise_for_status()
        # 返回响应的文本内容
        return response.text

# 影院插件类，用于处理用户消息
class CinemaPlugin:
    def __init__(self):
        # 初始化 MessageHandler 类的实例
        self.message_handler = MessageHandler()

    def process_message(self, message):
        # 调用 MessageHandler 实例的 handle_message 方法处理消息
        return self.message_handler.handle_message(message)
