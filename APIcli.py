import json
import requests
import ECMapi

# ---- Functions ----
# -------------------
def debug(text,db):
    if db == True:
        print(text)

def configcopy(text):
    """ Copy one config (indie or group) to a different device/group.
        copy [From ECM account] [-d:-g] name [To ECM account] [-d:-g] name [-rmwifi] [-pass password]"""
    command = text.split("")

def split(text,delim): # need to figure out how to adjust for single character vs a pair (like is needed for " )
    if delim in text:
            text = text.split(delim,2)
            return [text[0],text[1]] + split(text[2],delim)
    else:
            return [text]
# ------------------

print("For ECM access [1]\nFor router access [2] (future use)")
selection = input("selection:")

if selection == 1:
    baseurl = "https://www.cradlepointecm.com/api/v2/"
    headers,users = ECMapi.readECMkeys()
    print(headers)
    print(users)
    api = ECMapi.API(headers)
    
elif selection == 2:
    publicip = raw_input("Public IP: ")
    user = raw_input("Username: ")
    password = raw_input("Password: ")
    baseurl = "http://%s:8080/api/" % publicip
    headers = {
        'Content-Type': 'application/json'}
    requests.get(baseurl, auth=requests.auth.HTTPDigestAuth(user,password))


directory = ""
db = False # Debugging False
while True:
    prompt = raw_input("> ")
    try:
        if prompt == "ECM":
            val = users.keys()
        elif prompt[:4] == "ECM ":
            val = ECMapi.authECMuser(prompt[4:],users)
            if type(val) != str:
                val,api = "current user: "+val[0],ECMapi.API(val[1])

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
            print(baseurl+directory+prompt[4:])
            val = api.get(directory+prompt[4:])
            debug(baseurl+directory+prompt[4:],db) # Debug line
            
        elif prompt[0:6] == "patch ":
            print(prompt)
            val = api.patch(directory, prompt[6:])
            
        elif prompt[0:4] == "put ":
            val = api.put(directory, prompt[4:])
            debug(baseurl+directory+" "+prompt,db) # Debug line

        elif prompt[0:5] == "post ":
            val = api.post(directory,prompt[5:],headers=headers)
            debug(baseurl+directory+" "+prompt,db) # Debug line

        elif prompt[0:5] == "copy ":
            val = configcopy(prompt[5:])
            
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
    copy   --> Copy one config (indie or group) to a different device/group.
               copy [From ECM account] [-d:-g] name [To ECM account] [-d:-g] name [-rmwifi] [-pass password]
                        """
        else:
            debug(prompt,db)
            val = "Type help for more info."
    except ValueError as error:
        val = error
    except:
        val = "unkown error!"
    print(val)

