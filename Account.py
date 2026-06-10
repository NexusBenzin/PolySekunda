class Account:
    def __init__(self, name, password):
       self.name = name
       self.bal = 1000
       self.password = password
    
    def login(self):
        username = input("What is your username? ")
        password = input("What is you password? ")
        
        if password == self.password:
   print("LOGGED IN!")
else:
    print("Wrong password/username")


    