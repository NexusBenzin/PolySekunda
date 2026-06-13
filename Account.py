from user_data import Database

data = Database()


class Account:
    def __init__(self):
        self.name = None
        self.password = None
        self.bal = 0

    def create_account(self, name, password):
        self.name = name
        self.bal = 1000
        self.password = password
        data.add_user(self.name, self.password)

    def login(self, password):
        if password == self.password:
            return True
        else:
            return False
