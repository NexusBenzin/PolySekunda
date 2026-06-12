class Database:
    def __init__(self):
        self.userlist = []

    def add_user(self, name, password):
        user = {"username": name, "password": password, "balance": 1000}
        self.userlist.append(user)

    def find_user(self, name):
        for user in self.userlist:
            if user["username"] == name:
                return user
        return None

    def read_database(self):
        print(self.userlist)
