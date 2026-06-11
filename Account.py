from user-data import *
data = Database()


class Account:
    def __init__(self):
       pass   

   def create_account(self, name, password):
       self.name = name
       self.bal = 1000
       self.password = password
       data.add_user(self.name, self.password)
    
    def login(self, password):
        
        if password == self.password:
   print("LOGGED IN!")
else:
    print("Wrong password/username")


    