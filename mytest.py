#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from wxpy import *
#


robot = Robot()

my_friend = robot.friends().search('谢力')[0]

my_friend.send('Hello WeChat!，我是小溪机器人')


@robot.register(my_friend)
def reply_my_friend(msg):
    # 回复 my_friend 的消息 (优先匹配后注册的函数!)
    return 'received: {} ({})'.format(msg.text, msg.type)


# 开始监听和自动处理消息
robot.start()
