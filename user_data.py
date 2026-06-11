class Database:
    def __init__(self):
        self.userlist = []

    def add_user(self, name, password):
        user = {"username": name, "password": password}
        self.list.append(user)
    def read_database(self):
        print(self.userlist)
        