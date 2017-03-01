import datetime
import logging

from wxpy.chat import Chat
from wxpy.chats import Chats
from wxpy.group import Group
from wxpy.member import Member
from wxpy.user import User
from wxpy.utils.constants import MAP, CARD, FRIENDS, SYSTEM
from wxpy.utils.tools import ensure_list, wrap_user_name, match_name
from xml.etree import ElementTree as ETree


class MessageConfig(object):
    """
    单个消息注册配置
    """

    def __init__(
            self, robot, func, chats, msg_types,
            except_self, run_async, enabled
    ):
        self.robot = robot
        self.func = func

        self.chats = ensure_list(chats)
        self.msg_types = ensure_list(msg_types)
        self.except_self = except_self
        self.run_async = run_async

        self._enabled = None
        self.enabled = enabled

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        logging.info(self.__repr__())

    def __repr__(self):
        return '<{}: {}: {} ({}{})>'.format(
            self.__class__.__name__,
            self.robot.self.name,
            self.func.__name__,
            'Async, ' if self.run_async else '',
            'Enabled' if self.enabled else 'Disabled',
        )


class MessageConfigs(list):
    """
    一个机器人(Robot)的所有消息注册配置
    """

    def __init__(self, robot):
        """
        初始化

        :param robot: 这些配置所属的机器人
        """
        super(MessageConfigs, self).__init__()
        self.robot = robot

    def get_func(self, msg):
        """
        获取给定消息的对应回复函数。每条消息仅匹配和执行一个回复函数，后注册的配置具有更高的匹配优先级。

        :param msg: 给定的消息
        :return: 回复函数 func，及是否异步执行 run_async
        """

        def ret(_conf=None):
            if _conf:
                return _conf.func, _conf.run_async
            else:
                return None, None

        for conf in self[::-1]:

            if not conf.enabled or (conf.except_self and msg.chat == self.robot.self):
                return ret()

            if conf.msg_types and msg.type not in conf.msg_types:
                continue
            elif not conf.msg_types and msg.type == SYSTEM:
                continue

            if not conf.chats:
                return ret(conf)

            for chat in conf.chats:
                if chat == msg.chat or (isinstance(chat, type) and isinstance(msg.chat, chat)):
                    return ret(conf)

        return ret()

    def get_config(self, func):
        """
        根据执行函数找到对应的配置

        :param func: 已注册的函数
        :return: 对应的配置
        """
        for conf in self:
            if conf.func is func:
                return conf

    def _change_status(self, func, enabled):
        if func:
            self.get_config(func).enabled = enabled
        else:
            for conf in self:
                conf.enabled = enabled

    def enable(self, func=None):
        """
        开启指定函数的对应配置。若不指定函数，则开启所有已注册配置。

        :param func: 指定的函数
        """
        self._change_status(func, True)

    def disable(self, func=None):
        """
        关闭指定函数的对应配置。若不指定函数，则关闭所有已注册配置。

        :param func: 指定的函数
        """
        self._change_status(func, False)

    def _check_status(self, enabled):
        ret = list()
        for conf in self:
            if conf.enabled == enabled:
                ret.append(conf)
        return ret

    @property
    def enabled(self):
        """
        检查处于开启状态的配置

        :return: 处于开启状态的配置
        """
        return self._check_status(True)

    @property
    def disabled(self):
        """
        检查处于关闭状态的配置

        :return: 处于关闭状态的配置
        """
        return self._check_status(False)


class Message(dict):
    """
    单条消息对象
    """

    def __init__(self, raw, robot):
        super(Message, self).__init__(raw)

        self.robot = robot
        self.type = self.get('Type')

        self.is_at = self.get('isAt')
        self.file_name = self.get('FileName')
        self.img_height = self.get('ImgHeight')
        self.img_width = self.get('ImgWidth')
        self.play_length = self.get('PlayLength')
        self.url = self.get('Url')
        self.voice_length = self.get('VoiceLength')
        self.id = self.get('NewMsgId')

        self.text = None
        self.get_file = None
        self.create_time = None
        self.location = None
        self.card = None

        text = self.get('Text')
        if callable(text):
            self.get_file = text
        else:
            self.text = text

        create_time = self.get('CreateTime')
        if isinstance(create_time, int):
            self.create_time = datetime.datetime.fromtimestamp(create_time)

        if self.type == MAP:
            try:
                self.location = ETree.fromstring(self['OriContent']).find('location').attrib
                try:
                    self.location['x'] = float(self.location['x'])
                    self.location['y'] = float(self.location['y'])
                    self.location['scale'] = int(self.location['scale'])
                    self.location['maptype'] = int(self.location['maptype'])
                except (KeyError, ValueError):
                    pass
                self.text = self.location.get('label')
            except (TypeError, KeyError, ValueError, ETree.ParseError):
                pass
        elif self.type in (CARD, FRIENDS):
            self.card = User(self.get('RecommendInfo'))
            self.text = self.card.get('Content')

        # 将 msg.chat.send* 方法绑定到 msg.reply*，例如 msg.chat.send_img => msg.reply_img
        for method in '', '_image', '_file', '_video', '_msg', '_raw_msg':
            setattr(self, 'reply' + method, getattr(self.chat, 'send' + method))

    def __hash__(self):
        return hash((Message, self.id))

    def __repr__(self):
        text = (str(self.text) or '').replace('\n', ' ')
        ret = '{0.chat.name}'
        if self.member:
            ret += ' -> {0.member.name}'
        ret += ': '
        if self.text:
            ret += '{1} '
        ret += '({0.type})'
        return ret.format(self, text)

    @property
    def raw(self):
        """原始数据"""
        return dict(self)

    @property
    def chat(self):
        """
        来自的聊天对象
        """
        user_name = self.get('FromUserName')
        if user_name:
            for _chat in self.robot.chats():
                if _chat.user_name == user_name:
                    return _chat
            _chat = Chat(wrap_user_name(user_name))
            _chat.robot = self.robot
            return _chat

    @property
    def member(self):
        """
        发送此消息的群聊成员 (若消息来自群聊)
        """
        if isinstance(self.chat, Group):
            actual_user_name = self.get('ActualUserName')
            for _member in self.chat:
                if _member.user_name == actual_user_name:
                    return _member
            return Member(dict(UserName=actual_user_name, NickName=self.get('ActualNickName')), self.chat)


class Messages(list):
    """
    多条消息的合集，可用于记录或搜索
    """

    def __init__(self, msg_list=None, robot=None, max_history=10000):
        if msg_list:
            super(Messages, self).__init__(msg_list)
        self.robot = robot
        self.max_history = max_history

    def __add__(self, other):
        return Chats(super(Messages, self).__add__(other))

    def append(self, msg):
        del self[:-self.max_history + 1]
        return super(Messages, self).append(msg)

    def search(self, text=None, **attributes):
        """
        搜索消息

        :param text:
        :param attributes:
        :return:
        """

        def match(msg):
            if not match_name(msg, text):
                return
            for attr, value in attributes.items():
                if (getattr(msg, attr, None) or msg.get(attr)) != value:
                    return
            return True

        if text:
            text = text.lower()
        return Chats(filter(match, self), self.robot)
