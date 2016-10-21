import ECMapi
import argparse
from json import dumps

def getdebug(text,debuglevel):
    if debuglevel:
        output = ["----------"*20,str(text),"----------"*20,"\n"]
        print("\n".join(output))

def get_account(ECM_Account, accounts):
    if ECM_Account != "":
        account = accounts[1][ECM_Account]
        return account
    else:
        account = accounts[0]
        return account
    raise Exception("No valid ECM Account")

def cleanconfig(config,options):
    try:
        del config["configuration"][0]["overlay"]
        print("Removed NetCloud Engine Gateway")
    except:
        print("-> No NetCloud Engine Gateway (overlay config) needs removed")
    return config

def main(ECM_Source_Account,ECM_Destination_Account,Source_Config,Destination_Config,Passwords="",Remove_Wifi=False,debug=False):
    print("\n--------------- Started ---------------\n")
    try: accounts = ECMapi.readECMkeys()
    except: raise Exception("Couldn't find ECMkeys.txt with valid ECM keys!")
    account = get_account(ECM_Source_Account, accounts)
    getdebug(account,debug)
    print("Loading ECM account %s" % ECM_Source_Account)
    api = ECMapi.API(account)
    getdebug(api,debug)
    try:
        config = api.get("groups/",name=Source_Config)[0]
        getdebug(config,debug)
        print("Got Config from %s Group\n" % Source_Config)
    except:
        config = api.get("configuration_managers/?fields=configuration,router.product,router.actual_firmware,router.account&router.name=%s" % Source_Config)[0]
        getdebug(config,debug)
        try:
            config.update(config["router"])
            getdebug(config,debug)
            print("Got Config from Router %s\n" % Source_Config)
        except:
            raise ValueError("Couldn't Find %s in Groups or Devices of %s ECM Account" % (Source_Config, ECM_Source_Account))

    print("Modifying Config ....")
    config = cleanconfig(config,{"Passwords":Passwords,"Remove_Wifi":Remove_Wifi})
    print("\n")
    getdebug(config,debug)

    if ECM_Source_Account != ECM_Destination_Account:
        account = get_account(ECM_Destination_Account, accounts)
        getdebug(account,debug)
        print("Loading ECM account %s" % ECM_Destination_Account)
        api = ECMapi.API(account)
        getdebug(api,debug)
    try:
        deviceID = api.get("configuration_managers/?fields=id&router.name=%s" % Destination_Config)[0]['id']
        getdebug(deviceID,debug)
        print("Found device with device ID: %s" % deviceID)
        var = api.put("configuration_managers/%s/" % deviceID, dumps({"configuration": config["configuration"]}))
        getdebug(var,debug)
        print("\nConfiguration Copied to %s" % Destination_Config)
    except:
        try:
            groupID = api.get("groups/?fields=id&name=%s" % Destination_Config)[0]["id"]
            getdebug(groupID,debug)
            print("Found group %s with group ID: %s" % (Destination_Config,groupID))
        except:
            #if ECM_Source_Account != ECM_Destination_Account:
                #config["account"] = api.get("account/fields=id&)
            if "actual_firmware" in config: config["target_firmware"] = config["actual_firmware"]
            groupID = api.creategroup(Destination_Config, config["product"], config["target_firmware"], config["account"])
            getdebug(groupID,debug)
            print("Couldn't find group %s, created group with ID: %s" % (Destination_Config,groupID))
        package = dumps({"configuration": config["configuration"]})
        getdebug(package,debug)
        var = api.put("groups/%s/" % groupID, package)
        getdebug(var,debug)
        print("\nConfiguration Copied to %s!" % Destination_Config)
    print("\n--------------- Finished ----------------\n")




if __name__ == "__main__":
    helper = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description='ECM config copyier',conflict_handler='resolve', formatter_class=helper)
    parser.add_argument("-e1","--ECM_Source", default="", dest="ECM_Source_Account", 
                        help="Specify the source ECM account for the copy operation as defined in ECMkeys.txt")
    parser.add_argument("Source_Config",
                        help="Specify the name of the Group or Device to copy the config from")
    parser.add_argument("-e2","--ECM_Destination", dest="ECM_Destination_Account", default="",
                        help="Specify the destination ECM account for the copy operation as defined in ECMkeys.txt")
    parser.add_argument("Destination_Config",
                        help="Specify the name of the Group or Device to copy the config to. Can be a device or "
                             "group regardless of the Source_Config, if neither exists create a group")
    parser.add_argument("-p","--Passwords", dest="Passwords", default="",
                        help="Specify a password to override all passwords set in the existing config "
                             "(required if passwords are not default but blank value restores defaults)")
    parser.add_argument("-rw","--Remove_Wifi", dest="Remove_Wifi", default=False, action="store_true",
                        help="Remove wifi config from the source to change products or avoid wifi issues")
    parser.add_argument("--debug", dest="debug", default=False, action="store_true", help="Get debug output")
    args = vars(parser.parse_args())

    getdebug(args,args["debug"])

    main(args["ECM_Source_Account"], args["ECM_Destination_Account"], args["Source_Config"], args["Destination_Config"],
         Passwords=args["Passwords"], Remove_Wifi=args["Remove_Wifi"],debug=args["debug"])
