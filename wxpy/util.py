#!/usr/bin/env python3
# coding: utf-8

import logging
from functools import wraps

from wxpy.bot import Robot
from wxpy.chats import Chats
from wxpy.response import ResponseError
from wxpy.user import User


def dont_raise_response_error(func):
    """
    装饰器：用于避免被装饰的函数在运行过程中抛出 ResponseError 错误
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ResponseError as e:
            logging.warning('{0.__class__.__name__}: {0}'.format(e))

    return wrapped


def mutual_friends(*args):
    """
    找到多个微信用户的共同好友

    :param args: 每个参数为一个微信用户的机器人(Robot)，或是聊天对象合集(Chats)
    :return: 共同的好友列表
    """

    class FuzzyUser(User):
        def __init__(self, user):
            super(FuzzyUser, self).__init__(user)

        def __hash__(self):
            return hash((self.nick_name, self.province, self.city, self['AttrStatus']))

    mutual = set()

    for arg in args:
        if isinstance(arg, Robot):
            friends = map(FuzzyUser, arg.friends)
        elif isinstance(arg, Chats):
            friends = map(FuzzyUser, arg)
        else:
            raise TypeError

        if mutual:
            mutual &= set(friends)
        else:
            mutual.update(friends)

    return Chats(mutual)


def ensure_one(found):
    """
    确保列表中仅有一个项，并返回这个项，否则抛出 `ValueError` 异常

    :param found: 列表
    :return: 唯一项
    """
    if not isinstance(found, list):
        raise TypeError('expected list, {} found'.format(type(found)))
    elif not found:
        raise ValueError('not found')
    elif len(found) > 1:
        raise ValueError('more than one found')
    else:
        return found[0]
