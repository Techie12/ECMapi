import ECMapi
import argparse
import json

def get_account(ECM_Source_Account,accounts):
    try:
        account = accounts[1][ECM_Source_Account]
    except:
        account = accounts[0]
    return account

def creategroup(api,name,product,firmware,account):
    id = api.post("groups/",json.dumps({"name":name,"product":product,"target_firmware":firmware,"account":account}))[0]["id"]
    return str(id)

def main(ECM_Source_Account,ECM_Destination_Account,Source_Config,Destination_Config,Passwords="",Remove_Wifi=False):
    accounts = ECMapi.readECMkeys()
    account = get_account(ECM_Source_Account, accounts)
    api = ECMapi.API(account)
    try:
        config = api.get("groups/",name=Source_Config)[0]
    except:
        config = api.get("configuration_managers/?fields=configuration,router.product,router.actual_firmware,router.account&router.name=%s" % Source_Config)[0]
        print(config)
        try:

            config.update(config["router"])
            print(config)
        except:
            raise ValueError("Couldn't Find %s in Groups or Devices of %s ECM Account" % (Source_Config, ECM_Source_Account))

    account = get_account(ECM_Destination_Account, accounts)
    api = ECMapi.API(account)
    try:
        deviceID = api.get("configuration_managers/?fields=id&router.name=%s" % Destination_Config)[0]['id']
        print(deviceID)
        api.put("configuration_managers/%s/" % deviceID, json.dumps({"configuration": config["configuration"]}))
    except:
        if "actual_firmware" in config: config["target_firmware"] = config["actual_firmware"]
        try:
            groupID = api.get("groups/?fields=id&name=%s" % Destination_Config)[0]["id"]
            print(groupID)
        except:
            groupID = creategroup(api,Destination_Config, config["product"], config["target_firmware"], config["account"])
        package = json.dumps({"configuration": config["configuration"]})
        print(groupID,"\n----------\n",package)
        api.put("groups/%s/" % groupID, package)




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
    args = vars(parser.parse_args())

    print(args)

    main(args["ECM_Source_Account"], args["ECM_Destination_Account"], args["Source_Config"], args["Destination_Config"],
         Passwords=args["Passwords"], Remove_Wifi=args["Remove_Wifi"])
