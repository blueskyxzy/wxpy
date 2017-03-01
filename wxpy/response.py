class Response(dict):
    """
    | 从 itchat 获得的网络请求返回结果，绑定所属的 Robot 属性。
    | ret_code 不为 0 时会抛出 :class:`ResponseError` 异常
    """

    def __init__(self, raw, robot):
        super(Response, self).__init__(raw)

        self.robot = robot

        self.base_response = self.get('BaseResponse', dict())
        self.ret_code = self.base_response.get('Ret')
        self.err_msg = self.base_response.get('ErrMsg')

        if self.ret_code:
            raise ResponseError('code: {0.ret_code}; msg: {0.err_msg}'.format(self))


class ResponseError(Exception):
    """
    当 :class:`Response` 的返回值不为 0 时抛出的异常
    """
    pass
