from wxpy.chat import Chat


class User(Chat):
    """
    好友(:class:`Friend`)、群聊成员(:class:`Member`)，和公众号(:class:`MP`) 的基础类
    """

    def __init__(self, response):
        super(User, self).__init__(response)

        self.alias = response.get('Alias')
        self.display_name = response.get('DisplayName')
        self.remark_name = response.get('RemarkName')
        self.sex = response.get('Sex')
        self.province = response.get('Province')
        self.city = response.get('City')
        self.signature = response.get('Signature')

    def add(self, verify_content=''):
        return self.robot.add_friend(verify_content=verify_content)

    def accept(self, verify_content=''):
        return self.robot.accept_friend(verify_content=verify_content)

    @property
    def is_friend(self):
        """
        判断当前用户是否为好友关系

        :return: 若为好友关系则为 True，否则为 False
        """
        if self.robot:
            return self in self.robot.friends()
