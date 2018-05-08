import traceback
from pprint import pformat
from threading import Thread

import itchat
import logging

from wxpy.chat import Chat
from wxpy.chats import Chats
from wxpy.friend import Friend
from wxpy.group import Group
from wxpy.message import MessageConfigs, Messages, Message, MessageConfig
from wxpy.mp import MP
from wxpy.response import ResponseError
from wxpy.user import User
from wxpy.utils.constants import SYSTEM
from wxpy.utils.tools import handle_response, get_user_name, wrap_user_name, ensure_list

logger = logging.getLogger('wxpy')


class Robot(object):
    """
    机器人对象，用于登陆和操作微信账号，涵盖大部分 Web 微信的功能
    """

    def __init__(
            self, save_path=None, console_qr=False, qr_path=None,
            qr_callback=None, login_callback=None, logout_callback=None
    ):
        # 在初始化时便会执行登陆操作，需要手机扫描登陆。
        """
        :param save_path:
            | 用于保存或载入登陆状态的文件路径，例如: 'wxpy.pkl'，为空则不尝试载入。
            | 填写本参数后，可在短时间内重新载入登陆状态，避免重复扫码，失效时会重新要求登陆
        :param console_qr: 在终端中显示登陆二维码，需要安装 Pillow 模块
        :param qr_path: 保存二维码的路径
        :param qr_callback: 获得二维码时的回调，接收参数: uuid, status, qrcode
        :param login_callback: 登陆时的回调，接收参数同上
        :param logout_callback: 登出时的回调，接收参数同上
        """

        self.core = itchat.Core()
        itchat.instanceList.append(self)

        self.core.auto_login(
            hotReload=bool(save_path), statusStorageDir=save_path,
            enableCmdQR=console_qr, picDir=qr_path, qrCallback=qr_callback,
            loginCallback=login_callback, exitCallback=logout_callback
        )

        self.message_configs = MessageConfigs(self)
        self.messages = Messages(robot=self)

        self.file_helper = Chat(wrap_user_name('filehelper'))
        self.file_helper.robot = self
        self.file_helper.nick_name = '文件传输助手'

        self.self = Chat(self.core.loginInfo['User'])
        self.self.robot = self

        self.save_path = save_path

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.self.name)

    @handle_response()
    def logout(self):
        """
        登出当前账号
        """

        return self.core.logout()

    @property
    def alive(self):
        """
        当前的登陆状态

        :return: 若为登陆状态，则为 True，否则为 False
        """

        return self.core.alive

    @alive.setter
    def alive(self, value):
        self.core.alive = value

    def dump_login_status(self, save_path=None):
        return self.core.dump_login_status(save_path or self.save_path)

    # chats

    def except_self(self, chats_or_dicts):
        """
        从聊天对象合集或用户字典列表中排除自身

        :param chats_or_dicts: 聊天对象合集或用户字典列表
        :return: 排除自身后的列表
        """
        return list(filter(lambda x: get_user_name(x) != self.self.user_name, chats_or_dicts))

    def chats(self, update=False):
        """
        获取所有聊天对象

        :param update: 是否更新
        :return: 聊天对象合集
        """
        return Chats(self.friends(update) + self.groups(update) + self.mps(update), self)

    def friends(self, update=False):
        """
        获取所有好友

        :param update: 是否更新
        :return: 聊天对象合集
        """

        @handle_response(Friend)
        def do():
            return self.core.get_friends(update=update)

        ret = do()
        ret.source = self

        return ret

    @handle_response(Group)
    def groups(self, update=False, contact_only=False):
        """
        获取所有群聊

        :param update: 是否更新
        :param contact_only: 是否限于保存为联系人的群聊
        :return: 群聊合集
        """
        return self.core.get_chatrooms(update=update, contactOnly=contact_only)

    @handle_response(MP)
    def mps(self, update=False):
        """
        获取所有公众号

        :param update: 是否更新
        :return: 聊天对象合集
        """
        return self.core.get_mps(update=update)

    @handle_response(User)
    def user_details(self, user_or_users, chunk_size=50):
        """
        获取单个或批量获取多个用户的详细信息(地区、性别、签名等)，但不可用于群聊成员

        :param user_or_users: 单个或多个用户对象或 user_name
        :param chunk_size: 分配请求时的单批数量，目前为 50
        :return: 单个或多个用户用户的详细信息
        """

        def chunks():
            total = ensure_list(user_or_users)
            for i in range(0, len(total), chunk_size):
                yield total[i:i + chunk_size]

        @handle_response()
        def process_one_chunk(_chunk):
            return self.core.update_friend(userName=get_user_name(_chunk))

        if isinstance(user_or_users, (list, tuple)):
            ret = list()
            for chunk in chunks():
                chunk_ret = process_one_chunk(chunk)
                if isinstance(chunk_ret, list):
                    ret += chunk_ret
                else:
                    ret.append(chunk_ret)
            return ret
        else:
            return process_one_chunk(user_or_users)

    def search(self, name=None, **attributes):
        """
        在所有类型的聊天对象中进行搜索

        :param name: 名称 (可以是昵称、备注等)
        :param attributes: 属性键值对，键可以是 sex(性别), province(省份), city(城市) 等。例如可指定 province='广东'
        :return: 匹配的聊天对象合集
        """

        return self.chats().search(name, **attributes)

    # add / create

    @handle_response()
    def add_friend(self, user, verify_content=''):
        """
        添加用户为好友

        :param user: 用户对象或用户名
        :param verify_content: 验证说明信息
        """
        return self.core.add_friend(
            userName=get_user_name(user),
            status=2,
            verifyContent=verify_content,
            autoUpdate=True
        )

    @handle_response()
    def accept_friend(self, user, verify_content=''):
        """
        接受用户为好友

        :param user: 用户对象或用户名
        :param verify_content: 验证说明信息
        """

        # Todo: 验证好友接口可用性，并在接受好友时直接返回新好友

        return self.core.add_friend(
            userName=get_user_name(user),
            status=3,
            verifyContent=verify_content,
            autoUpdate=True
        )

    def create_group(self, users, topic=None):
        """
        创建一个新的群聊

        :param users: 用户列表
        :param topic: 群名称
        :return: 若建群成功，返回一个新的群聊对象
        """

        @handle_response()
        def request():
            return self.core.create_chatroom(
                memberList=wrap_user_name(users),
                topic=topic or ''
            )

        ret = request()
        user_name = ret.get('ChatRoomName')
        if user_name:
            return Group(self.core.update_chatroom(userName=user_name))
        else:
            raise ResponseError('Failed to create group:\n{}'.format(pformat(ret)))

    # messages

    def _process_message(self, msg):
        """
        处理接收到的消息
        """

        if not self.alive:
            return

        func, run_async = self.message_configs.get_func(msg)

        if not func:
            return

        def process():
            # noinspection PyBroadException
            try:
                ret = func(msg)
                if ret is not None:
                    if isinstance(ret, (tuple, list)):
                        self.core.send(
                            msg=str(ret[0]),
                            toUserName=msg.chat.user_name,
                            mediaId=ret[1]
                        )
                    else:
                        self.core.send(
                            msg=str(ret),
                            toUserName=msg.chat.user_name
                        )
            except:
                logger.warning(
                    'An error occurred in registered function, '
                    'use `Robot().start(debug=True)` to show detailed information')
                logger.debug(traceback.format_exc())

        if run_async:
            Thread(target=process).start()
        else:
            process()

    def register(
            self, chats=None, msg_types=None,
            except_self=True, run_async=True, enabled=True
    ):
        """
        装饰器：用于注册消息配置

        :param chats: 单个或列表形式的多个聊天对象或聊天类型，为空时匹配所有聊天对象
        :param msg_types: 单个或列表形式的多个消息类型，为空时匹配所有消息类型 (SYSTEM 类消息除外)
        :param except_self: 排除自己在手机上发送的消息
        :param run_async: 异步执行配置的函数，可提高响应速度
        :param enabled: 当前配置的默认开启状态，可事后动态开启或关闭
        """

        def register(func):
            self.message_configs.append(MessageConfig(
                robot=self, func=func, chats=chats, msg_types=msg_types,
                except_self=except_self, run_async=run_async, enabled=enabled
            ))

            return func

        return register

    def start(self, block=True):
        """
        开始监听和处理消息

        :param block: 是否堵塞线程，为 False 时将在新的线程中运行
        """

        def listen():

            logger.info('{} Auto-reply started.'.format(self))
            try:
                while self.alive:
                    msg = Message(self.core.msgList.get(), self)
                    if msg.type is not SYSTEM:
                        self.messages.append(msg)
                    self._process_message(msg)
            except KeyboardInterrupt:
                logger.info('KeyboardInterrupt received, ending...')
                self.alive = False
                if self.core.useHotReload:
                    self.dump_login_status()
                logger.info('Bye.')

        if block:
            listen()
        else:
            t = Thread(target=listen, daemon=True)
            t.start()
