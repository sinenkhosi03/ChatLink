def add_user(username, password):
    with open("storage.txt", "a") as storage_file:
        print("Recieved", username, password)
        storage_file.write(f"{username} {password}\n")

def user_exist(user):
    with open("storage.txt", "r") as storage_file:
        for line in storage_file.readlines():
            line = line.split(" ")[0]
            if line==user:
                return True
    
    return False

def remove_user(user):
    app_users = []
    with open("storage.txt", "r") as storage_file:
        for line in storage_file.readlines():
            line = line.split(" ")
            if line[0]!=user:
                app_users.append(line)
    
    with open("storage.txt", "w") as newFile:
        for user in app_users:
            newFile.write(f"{user[0]} {user[1]}")


remove_user("max")