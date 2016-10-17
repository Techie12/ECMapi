
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

    def get(self,call,paginate=1,**filters):
        # basic GET call to the API
        # Allows two formats: ex.1 get("routers/?id=123")  ex.2 get("routers/",id="123")
        # If you need an expanded field, either use option 1 or you have to specify as follows: ex. get("net_devices/",special={"router.id":"123"})
        output = []
        if filters != {}: filters = buildfilters(**filters)
        else: filters = ""
        call = baseurl+call+filters
        while call != None:
            val = requests.get(call, headers=self.headers)
            if str(val) == "<Response [200]>":
                val = json.loads(val.content)
                if "data" in val: output.extend(val["data"])
                else: output = val
            else:
                print(val)
                raise ValueError(str(call)+"  -->  "+str(val)+":  "+str(val.content)) # helps debug bad calls
            if paginate == 1: break
            if paginate > 0:paginate -= 1
            call = val["meta"]["next"]
        return output

    def patch(self,call,data,**filters):
        if filters != {}: filters = buildfilters(**filters)
        else: filters = ""
        output = requests.patch(baseurl+call+filters, data=data, headers=self.headers)
        if str(output) == "<Response [202]>":
            output = json.loads(output.content),output
        else:
            print(output)
            raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
        return output

    def put(self,call,data,**filters):
        if filters != {}: filters = buildfilters(**filters)
        else: filters = ""
        output = requests.put(baseurl+call+filters, data=data, headers=self.headers)
        if str(output) == "<Response [202]>":
            output = json.loads(output.content),output
        else:
            print(output)
            raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
        return output

    def post(self,call,data,**filters):
        if filters != {}: filters = buildfilters(**filters)
        else: filters = ""
        output = requests.post(baseurl+call+filters, data=data, headers=self.headers)
        if str(output) == "<Response [201]>":
            output = json.loads(output.content),output
        else:
            print(output)
            raise ValueError(str(call)+"  -->  "+str(output)+":  "+str(output.content)) # helps debug bad calls
        return output 

    def delete(self,call,**filters):
        return output

    # ------- High level calls -------

    # Most high level calls can pass any special filters to the base level call

    def devices(self,**kwargs):
        output = {}
        val = self.get("routers/",fields="id,name,group.name,mac,state,account.name",limit="500",paginate=0,**kwargs) # max returned entries per page is 500. polls only the stats we care about
        output["devicelist"] = [[t["state"],stripurl(t["id"]),t["name"],t.get("group",{"name":None})["name"],stripurl(t["account"]["name"][0:8]),t["mac"]] for t in val]
        routerids = output["devicelist"]
        return output

    def stats(self):
        # home page stats generation 2 calls + the alerts below
        output = {}
        val = self.get("routers/",fields="config_status,state",limit="500") # this determines what devices in an account are online / offline
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
        val = self.get("net_devices/",fields="type,homecarrid,summary",mode="wan",limit="500") # and this shows what carriers, etc. are online / available / offline
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

    def activitylog(self,**kwargs):
        # pulls %limit number of logs. straigt forward, ECM activity log pulled down 
        output = {}
        val = self.get("activity_logs/",limit="5",**kwargs)
        output["%ACTIVITYLOG%"] =[[t["created_at"][:t["created_at"].find(".")].replace("T"," - "),t["attributes"]["actor"].get("username",t["attributes"]["actor"].get("name")),"%ACTIVITY"+str(t["activity_type"])+"%"] for t in val] 
        return(output)   

    def alerts(self,limit,**kwargs):
        # pulls a number of alerts for the account
        if len(routerids) < 1:
            routerids.extend([t["id"] for t in self.get("routers/",limit="500",paginate=0)]) # call for router IDs to enumerate through if they haven't been found before, this only occurs since 100 device IDs can be queried at once
        for t in range(0,len(routerids[1])/100+1,1):
            routerlist = ",".join([e for e in routerids[t*100:(t+1)*100]])
            val = self.get("router_alerts/",fields="detected_at,friendly_info,router",limit="500",router__in=routerlist,paginate=0,**kwargs)
        val.sort(reverse=True) # ordered and displayed by newest first
        output =[[t["detected_at"][:t["detected_at"].find(".")].replace("T"," - "),self.get("routers/",fields="name&id="+t["router"][t["router"].find("routers/")+8:-1])[0]["name"],t["friendly_info"]] for t in val[0:limit]]
        return(output)


class router:
    
    def __init__(self,MAC,api):
        self.MAC = MAC
        self.api = api
        output = self.api.get("routers/",mac=MAC,fields="account.id,account.name,group,id,name")[0] # account info for a device
        self.routerdetails = output

    def datausage(self,after_time,writefile=False,**kwargs):
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        output = {"history":[]}
        for t in self.api.get("net_devices",special={"router.id":self.routerdetails["id"]},mode="wan",fields="name,id"):
            val = self.api.get("net_device_usage_samples/",net_device=t["id"],limit="500",created_at__gt=after_time,fields="uptime,bytes_in,bytes_out,created_at",**kwargs)
            output["history"].append({"total":sum([e["bytes_in"]+e["bytes_out"] for e in val]),"name":t["name"] ,"history":val})
        output["total"] = [sum([t["total"] for t in output["history"]])]
        output["total"].insert(0,str(sum([t["total"] for t in output["history"]])/1000000)+"MB")
        if writefile:
            with open("datausagehistory.txt", 'wb') as f: f.write(json.dumps(output))
        return output
    
    def signalsamples(self):
        writefile = False
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        output = {}
        val = self.api.get("net_devices",special={"router.id":self.routerdetails["id"]},mode="wan",fields="id,summary") # find used interfaces for this router
        for t in val:
            if t["summary"] in ("disconnected", "configure error", "configureerror", "unplugged"):
                pass
            output[t["id"]] = self.api.get("net_device_signal_samples/",limit="24",net_device=t["id"]) # polls signal history, 1 call per interface
        if writefile:
            with open("signalhistory.txt", 'wb') as f: f.write(json.dumps(output))
        return output

    @property
    def config(self):
        writefile = False
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        output = self.api.get("configuration_managers/",special={"router.id":self.routerdetails["id"]},fields="suspended,configuration,pending,id")[0]
        self.configmanager = output["id"]
        del output["id"]
        if writefile:
            with open("routerconfig.txt", 'wb') as f: f.write(json.dumps(output))
        return output

    @config.setter
    def config(self,value):
        print("Check")
        if self.configmanager == "":
            self.configmanager = self.api.get("configuration_managers/",special={"router.id":self.routerdetails["id"]},fields="id")["id"]
        print("configID: ",self.configmanager)
        self.output = self.api.put("configuration_managers/"+str(self.configmanager)+"/",json.dumps(value))
        return self.output

    def logs(self,writefile=False,**kwargs):
        if self.routerdetails == {}: return("Must call router_setdetails first!")
        if "paginate" not in kwargs: paginate = 1
        else: paginate = kwargs['paginate']
        output = self.api.get("router_logs/",limit="500",router=self.routerdetails["id"],paginate=paginate)
        with open("routerlog.csv", 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(["time","level","source","message"])
            for t in output:
                writer.writerow([t["created_at"],t["level"],t["source"],t["message"]])
        return output
    
    def createcase(self):
        # this is for the "Create a Case" option. lots of calls here, but should be infrequent.
        output = {}
        output["routerdetails"] = self.routerdetails
        output["routerdetails"] = [[t for t in output["routerdetails"]],[stripurl(t) for t in output["routerdetails"].values()]]
        print(output["routerdetails"])
        output["config"] = self.readconfig(writefile=True)
        output["signalsamples"] = self.signalsamples(writefile=True) # polls signal history, 1 call per interface
        # This is very slow 
        output["logs"] = self.logs(writefile=True)
        return(output)

class config:
    def __init__(self,config):
        self.config = config
    def editPassword(self,password):
        for t in self.config["configuration"]:
            pass
    def recurse(self,structure,match):
        path = [""]
        for t in structure:
            if match in structure[t]:
                return [t]
            if type(t) == dict:
                return recurse(t,match)
            


def stripurl(url):
    # formats poorly returned values (API urls rather than just ID numbers)
    if type(url) == dict:
        # this joins dictionary values with a '-' as a quick fix to data called and returns dictionaries we didn't want
        return("-".join([t for t in url.values()]))
    try:
        v = url.rfind("/")
        v = [url[:v-1].rfind("/")+1,v]
        return(url[v[0]:v[1]])
    except:
        return(url)

def buildfilters(**kwargs):
    if kwargs.has_key("special"):
        kwargs.update(kwargs["special"])
        del kwargs["special"]
    return("?"+"&".join([t+"="+k for t,k in kwargs.items()]))

def readECMkeys():
    # reads the file for available ECM API keys and auutomatically selects the specified default
    with open("ECMkeys.txt", 'r') as f:
        users = [f.readline().replace("\n","").replace("\r",""),f.read()]
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
##        v = api.router_createcase("00304416ec94")
        r = router("00304416ec94",api)
        v = r.config
        print(v)
        r.config = {u'configuration': [{u'wan': {u'rules2': {u'00000005-a81d-3590-93ca-8b1fcfeb8e14': {u'priority': 2.25, u'trigger_name': u'Modem-1ebb3902', u'_id_': u'00000005-a81d-3590-93ca-8b1fcfeb8e14', u'trigger_string': u'type|is|mdm%tech|is|lte/3g%uid|is|1ebb3902'}}}, u'system': {u'ui_activated': True, "gps": {"enabled":True}}}, []]}
    except: raise
