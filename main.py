import random
import re

from astrbot.api.all import *
from astrbot.api.event import filter
from astrbot.core.provider.entites import LLMResponse
import astrbot.api.message_components as Comp
import requests
import json

@register("QNA", "buding", "一个用于自动回答群聊问题的插件", "1.1.5", "https://github.com/zouyonghe/astrbot_plugin_qna")
class QNA(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 读取关键词列表
        question_keyword_list = self.config.get("question_keyword_list", "").split(";")
        self.question_pattern = None  # 默认值

        if question_keyword_list:
            self.question_pattern = r"(?i)(" + "|".join(map(re.escape, question_keyword_list)) + r")"

    def _in_qna_group_list(self, group_id: str) -> bool:
        qna_group_list = self.config.get("qna_group_list", [])
        return group_id in qna_group_list

    def _add_to_list(self, group_id: str):
        qna_group_list = self.config.get("qna_group_list", [])
        if not group_id or group_id == "":
            return
        if group_id in qna_group_list:
            return
        qna_group_list.append(group_id)
        self.config["qna_group_list"] = qna_group_list
        self.config.save_config()

    def _remove_from_list(self, group_id: str):
        qna_group_list = self.config.get("qna_group_list", [])
        if not group_id or group_id == "":
            return
        if group_id not in qna_group_list:
            return
        qna_group_list.remove(group_id)
        self.config["qna_group_list"] = qna_group_list
        self.config.save_config()

    async def search_cinema(self, event: AstrMessageEvent, messagestr: str):

        '''这是一个 搜 指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        user_id = event.get_sender_id() # 用户的id
        message_str = messagestr # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_str)
        message = ""
        if message_str.startswith('搜'):
            index = message_str.find("搜")
            if index != -1:
                message = message_str[index + len("搜"):]
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
            for index, item1 in enumerate(unique_data):
                if index == 9:
                    break
                question = item1.get('question')
                answer = item1.get('answer')
                result_str += f"{question}\n{answer}\n\n"
            # yield event.plain_result(f"[AT{user_id}] {user_name}, 搜索结果如下\n {result_str}!")  # 发送一条纯文本消息
            logger.info(user_id)
            at_component = At(qq=user_id)
            # 创建其他消息组件
            text = user_name + "搜索结果如下\n" + result_str
            plain_text = Plain(text=text)
            # 构建消息链
            message_chain = MessageChain([at_component, plain_text])
            # 创建消息事件结果
            yield event.chain_result(chain=message_chain)

    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def auto_answer(self, event: AstrMessageEvent):
        """自动回答群消息中的问题"""
        # 判定是否启用自动回复
        if not self.config.get("enable_qna", False):
            return

        if event.is_private_chat():
            return

        # # 判定不是主动唤醒
        # if event.is_at_or_wake_command:
        #     return

        # 判定不是自己的消息
        if event.get_sender_id() is event.get_self_id():
            return

        # 如果没有配置关键词或启用群组列表，直接返回
        if not self._in_qna_group_list(event.get_group_id()) or not self.question_pattern:
            return

        # 匹配提问关键词
        if not re.search(self.question_pattern, event.message_str):
            return

        # # 检测字数、LLM概率调用
        # if len(event.message_str) > 50 or random.random() > float(self.config.get("llm_answer_probability", 0.1)):
        #     return

        async for resp in self.search_cinema(event, event.message_str):
            yield resp


    @command_group("qna")
    def qna(self):
        pass

    @qna.command("enable")
    async def enable_qna(self, event: AstrMessageEvent):
        """开启自动解答"""
        try:
            if self.config.get("enable_qna", False):
                yield event.plain_result("✅ 自动解答已经是开启状态了")
                return

            self.config["enable_qna"] = True
            self.config.save_config()
            yield event.plain_result("📢 自动解答已开启")
        except Exception as e:
            logger.error(f"自动解答开启失败: {e}")
            yield event.plain_result("❌ 自动解答开启失败，请检查控制台输出")

    @qna.command("disable")
    async def disable_qna(self, event: AstrMessageEvent):
        """关闭自动解答"""
        try:
            if not self.config.get("enable_qna", False):
                yield event.plain_result("✅ 自动解答已经是关闭状态")
                return

            self.config["enable_qna"] = False
            self.config.save_config()
            yield event.plain_result("📢 自动解答已关闭")
        except Exception as e:
            logger.error(f"自动解答关闭失败: {e}")
            yield event.plain_result("❌ 自动解答关闭失败，请检查控制台输出")

    @qna.command("id")
    async def show_group_id(self, event: AstrMessageEvent):
        if event.is_private_chat():
            yield event.plain_result("检测到私聊，无群组ID。")
            return
        yield event.plain_result(event.get_group_id())

    @qna.group("group")
    def group(self):
        pass

    @group.command("list")
    async def show_qna_list(self, event: AstrMessageEvent):
        """获取启用解答的群号"""
        qna_group_list = self.config.get("qna_group_list", [])
        if not qna_group_list:
            yield event.plain_result("当前白名单列表为空")
            return

        # 格式化输出群号列表
        group_list_str = "\n".join(f"- {group}" for group in sorted(qna_group_list))
        result = f"当前启用 QNA 群组列表:\n{group_list_str}"
        yield event.plain_result(result)

    @group.command("add")
    async def add_to_qna_list(self, event: AstrMessageEvent, group_id: str):
        """添加群组到 QNA 列表"""
        try:
            # 检查群组ID格式是否正确，如果不合法，直接返回
            if not group_id.strip().isdigit():
                yield event.plain_result("⚠️ 群组ID必须为纯数字")
                return

            group_id = group_id.strip()

            # 添加到白名单
            self._add_to_list(group_id)
            yield event.plain_result(f"✅ 群组 {group_id} 已成功添加到自动解答白名单")
        except Exception as e:
            # 捕获并记录日志，同时通知用户
            logger.error(f"❌ 添加群组 {group_id} 到白名单失败，错误信息: {e}")
            yield event.plain_result("❌ 添加到白名单失败，请查看控制台日志")

    @group.command("del")
    async def remove_from_qna_list(self, event: AstrMessageEvent, group_id: str):
        """从 QNA 列表移除群组"""
        try:
            # 检查群组ID格式是否正确
            if not group_id.strip().isdigit():
                yield event.plain_result("⚠️ 群组ID必须为纯数字")
                return

            group_id = group_id.strip()

            # 移除群组
            self._remove_from_list(group_id)
            yield event.plain_result(f"✅ 群组 {group_id} 已成功从自动解答白名单中移除")
        except Exception as e:
            # 捕获其他异常，记录日志并告知用户
            logger.error(f"❌ 移除群组 {group_id} 时发生错误：{e}")
            yield event.plain_result("❌ 从白名单中移除失败，请查看控制台日志")

    @filter.on_llm_response()
    async def remove_null_message(self, event: AstrMessageEvent, resp: LLMResponse):
        """
        如果结果为 `NULL` 则删除消息
        """
        if resp.role == 'assistant':
            # 检测是否为NULL
            if resp.completion_text.strip().upper() == "NULL":
                logger.debug(f"Found 'NULL' in LLM response: {resp.completion_text}")
                event.stop_event()


class MessageHandler:
    def handle_message(self, message):
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
                response = self.send_request(url, message, token)
                try:
                    # 尝试将响应内容解析为 JSON
                    data = json.loads(response)
                    if len(data["list"]) != 0:
                        for item in data["list"]:
                            all_responses.append(item)
                except json.JSONDecodeError:
                    # 若解析失败，将原始响应添加到 all_responses
                    # all_responses.append(response)
                    continue
            except requests.RequestException as e:
                # all_responses.append(f"请求 {url} 出现错误: {e}")
                continue
        return all_responses

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