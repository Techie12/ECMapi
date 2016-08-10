
import json
import requests
import csv

baseurl="https://www.cradlepointecm.com/api/v2/"
routerids = []

# ------ Base level calls -------

def get(call,filters,headers,paginate=False):
    # basic GET call to the API
    output = requests.get(baseurl+call+"?"+filters, headers=headers)
    if str(output) == "<Response [200]>":
        output = json.loads(output.content)
    else:
        print(output)
        raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
    return output

def patch(call,data,headers):
    # for future implementations
    output = requests.patch(baseurl+call, data=data, headers=headers)
    if str(output) == "<Response [200]>":
        output = json.loads(output.content)
    else:
        print(output)
        raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
    return output

def put(call,data,headers):
    return output

def delete(call,data,headers):
    return output

# ------- High level calls -------

# Every high level call can pass any special filters to the base level call

def devices(headers,**kwargs):
    filters = buildfilters({"fields":"id,name,group.name,mac,state,account.name", "limit": "500"},kwargs)
    output = {}
    val = get("routers/",filters,headers,paginate=True)['data'] # max returned entries per page is 500. polls only the stats we care about
    routerids.extend([t["id"] for t in val if not t["id"] in routerids])
    output["devicelist"] = [["%"+t["state"].upper()+"%",stripurl(t["id"]),t["name"],t.get("group",{"name":None})["name"],stripurl(t["account"]["name"][0:8]),"%CREATE%"+t["mac"]+"""'"/>"""] for t in val]
    length = len(output["devicelist"])
    chunk = 25 # used to control number of entries displayed at a time
    for t in range(0,length+1,chunk):
        output["%DEVICE"+str((t/chunk)+1)+"%"] = output["devicelist"][t:t+chunk]
    return output

def stats(headers):
    # home page stats generation 2 calls + the alerts below
    output = {}
    val = get("routers/?fields=config_status,state&limit=500",headers)['data'] # this determines what devices in an account are online / offline
    n=[0,0,0,0]
    for t in val:
        if t["state"] == "online":
            n[0]+=1
        if t["state"] == "offline":
            n[1]+=1
        elif t["config_status"] == "synch_suspended":
            n[3]+=1
    n[2] = n[0]+n[1]
    output["%ROUTERSTATE%"] = [n]
    val = get("net_devices/?fields=type,homecarrid,summary&mode=wan&limit=500",headers)['data'] # and this shows what carriers, etc. are online / available / offline
    n = {}
    for t in [e for e in val if not e["summary"] in ("disconnected", "configure error", "configureerror", "unplugged")]:
        print(t)
        if t["type"] == "ethernet":
            t["homecarrid"] = "Ethernet"
        if not n.has_key(t["homecarrid"]):
            n[t["homecarrid"]] = [0,0,0]
        if t["summary"] == "connected": n[t["homecarrid"]][0]+=1
        elif t["summary"] == "available": n[t["homecarrid"]][1]+=1
        else: n[t["homecarrid"]][2]+=1
    output["%CARRIERSTATS%"] = [[a]+b for a,b in n.items()]
    return(output)

def alerts(limit,headers):
    # pulls %limit number of alerts for the account
    output = {}
    if len(routerids) < 1:
        routerids.extend([t["id"] for t in get("routers/?fields=id&limit=500",headers)["data"]]) # call for router IDs to enumerate through if they haven't been found before, this only occurs since 100 device IDs can be queried at once
    val = []
    for t in range(0,len(routerids)/100+1,1):
        routerlist = ",".join([e for e in routerids[t*100:(t+1)*100]])
        val.extend(get("router_alerts/?fields=detected_at,friendly_info,router&limit="+str(limit)+"&router__in="+routerlist,headers)['data'])
    val.sort(reverse=True) # ordered and displayed by newest first
    output["%ALERTS%"] =[[t["detected_at"][:t["detected_at"].find(".")].replace("T"," - "),get("routers/?fields=name&id="+t["router"][t["router"].find("routers/")+8:-1],headers)['data'][0]["name"],t["friendly_info"]] for t in val[0:limit]]
    return(output)

def activitylog(limit,headers):
    # pulls %limit number of logs. straigt forward, ECM activity log pulled down 
    output = {}
    val = get("activity_logs/?limit="+str(limit),headers)['data']
    print(val)
    output["%ACTIVITYLOG%"] =[[t["created_at"][:t["created_at"].find(".")].replace("T"," - "),t["attributes"]["actor"].get("username",t["attributes"]["actor"].get("name")),"%ACTIVITY"+str(t["activity_type"])+"%"] for t in val] 
    return(output)

def createcase(MAC,headers):
    # this is for the "Create a Case" option. lots of calls here, but should be infrequent.
    output = {"signalsamples":{},"logs":{}}
    output["routerdetails"] = get("routers/?mac="+MAC+"&fields=account.id,account.name,group,id,name",headers)["data"][0] # account info for a device
    routerid = output["routerdetails"]["id"]
    output["routerdetails"] = [[t for t in output["routerdetails"]],[stripurl(t) for t in output["routerdetails"].values()]]
    print(output["routerdetails"])
    output["config"] = get("configuration_managers/?router.id="+routerid+"&fields=suspended,configuration,pending",headers)['data'][0] # pulls config for the specified device
    with open("routerconfig.txt", 'wb') as f: f.write(json.dumps(output["config"]))
    val = get("net_devices?router.id="+routerid+"&mode=wan&fields=id,summary",headers)['data'] # find used interfaces for this router
    for t in val:
        if t["summary"] in ("disconnected", "configure error", "configureerror", "unplugged"):
            pass
        output["signalsamples"][t["id"]] = get("net_device_signal_samples/?limit=24&net_device="+t["id"],headers)['data'] # polls signal history, 1 call per interface
    with open("signalhistory.txt", 'wb') as f: f.write(json.dumps(output["signalsamples"]))
    # This is all commented out due to slowness (demo reasons, but does work!). only use of pagination here
##    nextcall = "router_logs/?limit=500&router="+routerid
##    with open("routerlog.csv", 'wb') as f:
##        writer = csv.writer(f)
##        writer.writerow(["time","level","source","message"])
##        n=1 # This is a temporary addition to only pull n*500 lines of the log since it is sooo slow from api
##        while nextcall != None:
##            if n <= 0:
##                break
##            n-=1
##            val = get(nextcall,headers)
##            output["logs"].update(val['data'][0])
##            for t in val['data']:
##                writer.writerow([t["created_at"],t["level"],t["source"],t["message"]])
##            if not nextcall == None:
##                nextcall = val['meta']['next'][38:]
##            print(nextcall)
    return(output)

def stripurl(url):
    # formats poorly returned values (API urls rather than just ID nuumbers)
    if type(url) == dict:
        # this joins dictionary values with a '-' as a quick fix to data called and returns dictionaries we didn't want
        return("-".join([t for t in url.values()]))
    try:
        v = url.rfind("/")
        v = [url[:v-1].rfind("/")+1,v]
        return(url[v[0]:v[1]])
    except:
        return(url)

def buildfilters(defaults,**kwargs):
    [kwargs.update({t:k}) for t,k in defaults.items() if not kwargs.has_key(t)]
    return("&".join([t+"="+k for t,k in kwargs.items()]))

def readECMkeys():
    # reads the file for available ECM API keys and auutomatically selects the specified default
    with open("ECMkeys.txt", 'r') as f:
        users = [f.readline().replace("\n",""),f.read()]
        users[1] = json.loads(users[1])
        users[0] = users[1][users[0]]
        return(users)

def authECMuser(user,userbase):
    # method for switching the current ECM API keys being used (allows "password" protection)
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

if __name__ == "__main__":
    # debug for above commands
    headers = reeadECMkeys()[0]
    print(devices(headers))
