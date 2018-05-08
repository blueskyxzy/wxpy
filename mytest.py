#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from wxpy import *
from wxpy.contrib.tuling import Tuling
robot = Robot()

my_friend = robot.friends().search('谢力')[0]

my_friend.send('Hello!，我是小溪机器人')

# @robot.register(my_friend)
# def reply_my_friend(msg):
#     # 回复 my_friend 的消息 (优先匹配后注册的函数!)
#     return 'received: {} ({})'.format(msg.text, msg.type)


tuling = Tuling(api_key='43c87509771848f997cd48fba195b2be')


@robot.register(my_friend)
# 使用图灵机器人自动与指定好友聊天
def reply_my_friend(msg):
    tuling.do_reply(msg)


# 开始监听和自动处理消息
robot.start()

# # 堵塞线程，并进入 Python 命令行
# embed()
