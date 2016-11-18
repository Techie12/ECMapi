import ECMapi
import argparse
from json import dumps, loads
from os.path import exists


def get_account(ECM_Account, accounts):
    if ECM_Account != "":
        account = accounts[1][ECM_Account]
        return account
    else:
        account = accounts[0]
        return account
    raise Exception("No valid ECM Account")

def loadFile(directory):
    try:
        with open(directory,'r') as f:
            config = loads(f.read())
    except:
        raise Exception("Couldn't find File at %s" % directory)
    return config

def writeFile(directory,config):
    if exists(directory):
        raise Exception("File at %s already exists!" % directory)
    else:
        with open(directory,'a') as f:
            f.write(dumps({"configuration":config}))
    return 1

def cleanconfig(config,options):
    # Remove NetCloud Engine (Pertino)
    try:
        del config["configuration"][0]["overlay"]
        print("Removed NetCloud Engine Gateway")
    except:
        print("-> No NetCloud Engine Gateway (overlay config) needs removed")
    # Remove Certs from the config
    try:
        del config["configuration"][0]["certmgmt"]
    except:
        print("-> No CertManagement (certificates) need removed")
    # Remove Wifi section of the config if Remove_Wifi is true
    if options["Remove_Wifi"] == True:
        try:
            del config["configuration"][0]["wlan"]
            del config["configuration"][0]["wwan"]
        except:
            print("-> Unable to remove wifi settings (none set?)")
    # Remove or modify Passwords in the config
    removals = [item for item in item_generator(config,"password")]
    getdebug("config items to remove",removals)
    if options["Passwords"] == "":
        for path in removals:
            exec_command = "".join(["del config"]+["[%s]"% step for step in path])
            getdebug("config password removal", exec_command)
            exec exec_command
    else:
        for path in removals:
            exec_command = "".join(["config"]+["[%s]"% step for step in path]+['="%s"' % options["Passwords"]])
            getdebug("config password change", exec_command)
            exec exec_command
    return config

def item_generator(json_input, lookup_key):
    if isinstance(json_input, dict):
        for k, v in json_input.iteritems():
            if (k == lookup_key) or (v == "*"):
                yield ['"%s"'%k]
            else:
                for child_val in item_generator(v, lookup_key):
                    yield ['"%s"'%k]+child_val
    elif isinstance(json_input, list):
        for item in json_input:
            for item_val in item_generator(item, lookup_key):
                yield [json_input.index(item)]+item_val


def getdebug(head,text):
    if debuglevel:
        output = ["----------"*20,str(head),str(text),"----------"*20,"\n"]
        print("\n".join(output))

def main(ECM_Source_Account,ECM_Destination_Account,Source_Config,Destination_Config,Passwords="",Remove_Wifi=False):
    print("\n--------------- Started ---------------\n")
    try: accounts = ECMapi.readECMkeys()
    except: raise Exception("Couldn't find ECMkeys.txt with valid ECM keys!")
    if ECM_Source_Account == "FILE":
        config = loadFile(Source_Config)
        print("Got config from File %s" % ECM_Source_Account)
    else:
        account = get_account(ECM_Source_Account, accounts)
        getdebug("ecm source account", account)
        print("Loading ECM account %s" % ECM_Source_Account)
        api = ECMapi.API(account)
        getdebug("load source account", api)
        try:
            config = api.get("groups/",name=Source_Config)[0]
            getdebug("source config from group", config)
            print("Got Config from %s Group\n" % Source_Config)
        except:
            config = api.get("configuration_managers/?fields=configuration,router.product,router.actual_firmware,router.account&router.name=%s" % Source_Config)[0]
            getdebug("source config from device", config)
            try:
                config.update(config["router"])
                getdebug("updated config with router", config)
                print("Got Config from Router %s\n" % Source_Config)
            except:
                raise ValueError("Couldn't Find %s in Groups or Devices of %s ECM Account" % (Source_Config, ECM_Source_Account))

    print("Modifying Config ....")
    config = cleanconfig(config,{"Passwords":Passwords,"Remove_Wifi":Remove_Wifi})
    print("\n")
    getdebug("modified config", config)

    if ECM_Destination_Account == "FILE":
        writeFile(Destination_Config,config["configuration"])
        print("Configuration Copied to File %s" % Destination_Config)
    else:
        if ECM_Source_Account != ECM_Destination_Account:
            account = get_account(ECM_Destination_Account, accounts)
            getdebug("ecm destination account", account)
            print("Loading ECM account %s" % ECM_Destination_Account)
            api = ECMapi.API(account)
            getdebug("load destination account", api)
        try:
            deviceID = api.get("configuration_managers/?fields=id&router.name=%s" % Destination_Config)[0]['id']
            getdebug("destination device id", deviceID)
            print("Found device with device ID: %s" % deviceID)
            var = api.put("configuration_managers/%s/" % deviceID, dumps({"configuration": config["configuration"]}))
            getdebug("attempt to push config to device", var)
            print("\nConfiguration Copied to %s" % Destination_Config)
        except:
            try:
                groupID = api.get("groups/?fields=id&name=%s" % Destination_Config)[0]["id"]
                getdebug("destination group id", groupID)
                print("Found group %s with group ID: %s" % (Destination_Config,groupID))
            except:
                try:
                    if ECM_Source_Account != ECM_Destination_Account:
                        config["account"] = api.me
                    if "actual_firmware" in config: config["target_firmware"] = config["actual_firmware"]
                    groupID = api.creategroup(Destination_Config, config["product"], config["target_firmware"], config["account"])
                    getdebug("created destination group id", groupID)
                    print("Couldn't find group %s, created group with ID: %s" % (Destination_Config,groupID))
                except:
                    print("Couldn't create a new group for this config! "
                          "(An existing device is required if you are using a source file instead of an ECM account)")
            package = dumps({"configuration": config["configuration"]})
            getdebug("config package to put", package)
            var = api.put("groups/%s/" % groupID, package)
            getdebug("attempt to put package", var)
            print("\nConfiguration Copied to %s!" % Destination_Config)
    print("\n--------------- Finished ----------------\n")


if __name__ == "__main__":
    helper = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description='ECM config copier',conflict_handler='resolve', formatter_class=helper)
    parser.add_argument("-e1","--ECM_Source", default="", dest="ECM_Source_Account", 
                        help="Specify the source ECM account for the copy operation as defined in ECMkeys.txt "
                             "(use 'FILE' to specify using a local file instead)")
    parser.add_argument("Source_Config",
                        help="Specify the name of the Group or Device to copy the config from")
    parser.add_argument("-e2","--ECM_Destination", dest="ECM_Destination_Account", default="",
                        help="Specify the destination ECM account for the copy operation as defined in ECMkeys.txt "
                             "(use 'FILE' to specify using a local file instead)")
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

    debuglevel = args["debug"]

    getdebug("command line args", args)

    try:
        main(args["ECM_Source_Account"], args["ECM_Destination_Account"], args["Source_Config"], args["Destination_Config"],
         Passwords=args["Passwords"], Remove_Wifi=args["Remove_Wifi"])
    except Exception as err:
        print("--------------- FAILED! --------------- \nError: %s" % err)