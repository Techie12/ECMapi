
import json
import requests
import csv

baseurl="https://www.cradlepointecm.com/api/v2/"
routerids = []

# ------ Base level calls -------

class API:

    def __init__(self, headers):
        self.headers = headers
        self.routerdetails = {}

    def get(self,call,filters,paginate=1):
        # basic GET call to the API
        output = []
        call = baseurl+call+"?"+filters
        while call != None:
            val = requests.get(call, headers=self.headers)
            if str(val) == "<Response [200]>":
                val = json.loads(val.content)
                output.extend(val["data"])
            else:
                print(val)
                raise ValueError(str(call)+"  -->  "+str(val)+":  "+str(val.content)) # helps debug bad calls
            if paginate == 1: break
            if paginate > 0:paginate -= 1
            call = val["meta"]["next"]
        return output

    def patch(self,call,filters,data):
        # for future implementations
        output = requests.patch(baseurl+call+"?"+filters, data=data, headers=self.headers)
        if str(output) == "<Response [200]>":
            output = json.loads(output.content)
        else:
            print(output)
            raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
        return output

    def put(self,call,filters,data):
        # for future implementations
        output = requests.put(baseurl+call+"?"+filters, data=data, headers=self.headers)
        if str(output) == "<Response [200]>":
            output = json.loads(output.content)
        else:
            print(output)
            raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
        return output

    def delete(self,call,filters):
        return output

    # ------- High level calls -------

    # Most high level call can pass any special filters to the base level call

    def devices(self,**kwargs):
        filters = buildfilters({"fields":"id,name,group.name,mac,state,account.name", "limit": "500"},**kwargs)
        output = {}
        val = self.get("routers/",filters,paginate=0) # max returned entries per page is 500. polls only the stats we care about
        output["devicelist"] = [[t["state"],stripurl(t["id"]),t["name"],t.get("group",{"name":None})["name"],stripurl(t["account"]["name"][0:8]),t["mac"]] for t in val]
        routerids = output["devicelist"]
        return output

    def stats(self):
        # home page stats generation 2 calls + the alerts below
        output = {}
        val = self.get("routers/","fields=config_status,state&limit=500") # this determines what devices in an account are online / offline
        n=[0,0,0,0]
        for t in val:
            if t["state"] == "online":
                n[0]+=1
            if t["state"] == "offline":
                n[1]+=1
            elif t["config_status"] == "synch_suspended":
                n[3]+=1
        n[2] = n[0]+n[1]
        output["RouterState"] = [n]
        val = self.get("net_devices/","fields=type,homecarrid,summary&mode=wan&limit=500") # and this shows what carriers, etc. are online / available / offline
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
        output["CarrierState"] = [[a]+b for a,b in n.items()]
        return(output)

    def alerts(self,limit,**kwargs):
        # pulls a number of alerts for the account
        output = {}
        if len(routerids) < 1:
            routerids.extend([t["id"] for t in self.get("routers/","limit=500",paginate=0)]) # call for router IDs to enumerate through if they haven't been found before, this only occurs since 100 device IDs can be queried at once
        for t in range(0,len(routerids[1])/100+1,1):
            routerlist = ",".join([e[1] for e in routerids[t*100:(t+1)*100]])
            filters = buildfilters({"fields":"detected_at,friendly_info,router","limit":"500","router__in":routerlist},**kwargs)
            val = self.get("router_alerts/",filters,paginate=0)
        val.sort(reverse=True) # ordered and displayed by newest first
        output["%ALERTS%"] =[[t["detected_at"][:t["detected_at"].find(".")].replace("T"," - "),self.get("routers/","fields=name&id="+t["router"][t["router"].find("routers/")+8:-1])[0]["name"],t["friendly_info"]] for t in val[0:limit]]
        return(output)

    def activitylog(self,**kwargs):
        # pulls %limit number of logs. straigt forward, ECM activity log pulled down 
        output = {}
        filters = buildfilters({"limit":"5"},**kwargs)
        val = self.get("activity_logs/",filters)
        print(val)
        output["%ACTIVITYLOG%"] =[[t["created_at"][:t["created_at"].find(".")].replace("T"," - "),t["attributes"]["actor"].get("username",t["attributes"]["actor"].get("name")),"%ACTIVITY"+str(t["activity_type"])+"%"] for t in val] 
        return(output)   

    def router_setdetails(self,MAC):
        # used to set the variable for router details so we don't have to make this call all the time for the other operations
        output = self.get("routers/","mac="+MAC+"&fields=account.id,account.name,group,id,name")[0] # account info for a device
        self.routerdetails = output
        return output
    
    def router_signalsamples(self,writefile=False):
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        output = {}
        val = self.get("net_devices","router.id="+self.routerdetails["id"]+"&mode=wan&fields=id,summary") # find used interfaces for this router
        for t in val:
            if t["summary"] in ("disconnected", "configure error", "configureerror", "unplugged"):
                pass
            output[t["id"]] = self.get("net_device_signal_samples/","limit=24&net_device="+t["id"]) # polls signal history, 1 call per interface
        if writefile:
            with open("signalhistory.txt", 'wb') as f: f.write(json.dumps(output))
        return output

    def router_readconfig(self,writefile=False):
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        output = self.get("configuration_managers/","router.id="+self.routerdetails["id"]+"&fields=suspended,configuration,pending")[0]
        if writefile:
            with open("routerconfig.txt", 'wb') as f: f.write(json.dumps(output))
        return output

    def router_logs(self,writefile=False,**kwargs):
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        if "paginate" not in kwargs: paginate = 1
        else: paginate = kwargs['paginate']
        output = self.get("router_logs/","limit=500&router="+self.routerdetails["id"],paginate=paginate)
        with open("routerlog.csv", 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(["time","level","source","message"])
            for t in output:
                writer.writerow([t["created_at"],t["level"],t["source"],t["message"]])
        return output
    
    def router_createcase(self,MAC):
        # this is for the "Create a Case" option. lots of calls here, but should be infrequent.
        output = {}
        output["routerdetails"] = self.router_setdetails(MAC)
        output["routerdetails"] = [[t for t in output["routerdetails"]],[stripurl(t) for t in output["routerdetails"].values()]]
        print(output["routerdetails"])
        output["config"] = self.router_readconfig(writefile=True)
        output["signalsamples"] = self.router_signalsamples(writefile=True) # polls signal history, 1 call per interface
        # This is very slow 
        output["logs"] = self.router_logs(writefile=True)
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
    headers = readECMkeys()[0]
    api = API(headers)
    try:
##        v = api.devices()
##        v = api.stats()
##        v = api.alerts(5)
##        v = api.activitylog()
        v = api.router_createcase("00304416ec94")
    except: raise
