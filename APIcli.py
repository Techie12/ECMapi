import json
import requests

# ---- Functions ----
# -------------------
def debug(text,db):
    if db == True:
        print(text)

def readECMkeys():
    with open("ECMkeys.txt", 'r') as f:
        users = [f.readline().replace("\n",""),f.read()]
        users[1] = json.loads(users[1])
        users[0] = users[1][users[0]]
        return(users)

def authECMuser(user,userbase):
    password = ""
    if user.find(":") != -1:
        user,password = user.split(":")
    if userbase.has_key(user):
        try:
            if type(userbase[user]) == dict:
                return user,userbase[user]
            elif userbase[user][0] == password:
                return user,userbase[user][1]
            else:
                return("Bad Password")
        except:
            raise ValueError("USER auth type Error")
    else:
        return("No ECM User Found!")

# ------------------

print("For ECM access [1]\nFor router access [2]")
selection = input("selection:")

if selection == 1:
    baseurl = "https://www.cradlepointecm.com/api/v2/"
    headers,users = readECMkeys()
    print(headers)
    print(users)
    
elif selection == 2:
    publicip = raw_input("Public IP: ")
    user = raw_input("Username: ")
    password = raw_input("Password: ")
    baseurl = "http://"+publicip+":8080/api/"
    headers = {
        'Content-Type': 'application/json'}
    requests.get(baseurl, auth=requests.auth.HTTPDigestAuth(user,password))


directory = ""
db = False # Debugging False
while True:
    prompt = raw_input("> ")

    if prompt == "ECM":
        val = users.keys()
    elif prompt[:4] == "ECM ":
        val = authECMuser(prompt[4:],users)
        if type(val) != str:
            val,headers = "current user: "+val[0],val[1]

    elif prompt == "debug":
        val = "debugging!!"
        db = True # Set debugging True
        
    elif prompt[0:3] == 'cd ':
        directory = prompt[3:]
        debug(prompt,db) # Debug line
        val = directory # Debug line

    elif prompt[0:4] == "val ":
        debug(prompt[4:],db)
        if type(val) == str:
            val = json.loads(val)
        try:
            try:
                val = val[int(prompt[4:])]
            except:
                val = val[prompt[4:]]
        except:
            print("value error")
        
    elif prompt[0:4] == "get ":
        print(baseurl+directory+prompt[4:],headers)
        rg = requests.get(baseurl+directory+prompt[4:],headers=headers)
        debug(baseurl+directory+prompt[4:],db) # Debug line
        val = rg.content
        
    elif prompt[0:6] == "patch ":
        prompt = prompt[6:]
        print(prompt)
        rp = requests.patch(baseurl+directory, data=prompt, headers=headers)
        print(rp)
        print(rp.content)
        val = rp
        
    elif prompt[0:4] == "put ":
        prompt = prompt[4:]
        rp = requests.put(baseurl+directory,data=prompt,headers=headers)
        debug(baseurl+directory+" "+prompt,db) # Debug line
        print(rp.content)
        val = rp

    elif prompt[0:5] == "post ":
        prompt = prompt[5:]
        rp = requests.post(baseurl+prompt.split(" ")[0],data=prompt.split(" ")[1],headers=headers)
        print(rp,"--->",rp.content)
        val = rp
        
    elif prompt == "exit":
        break

    elif prompt == "help":
        val = """available commands:
cd     --> changes the directory URL
get    --> performs a get command on the provided URL
set    --> performs a set command on on the given URL
put    --> performs a put command at the previously set directory with the argument as the data
patch  --> performs a patch command on the previously set directory with the argument as the data
ECM    --> sets the ECM user for API access (users are defined in ECMkeys.txt) Alone it specifies available accounts
val    --> provides the details of an object or dictionary value from the previously run get command
exit   --> exits the application
help   --> displays this information
debug  --> enables debug output
                    """
    else:
        debug(prompt,db)
        val = "Type help for more info."

    print(val)

