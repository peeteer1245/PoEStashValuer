import _thread
import os
import time

try:
    import requests
except ImportError:
    print("you need the requests library for this script to work")
    quit()

########################################################
# remember to enter your data in lines 147 to 151
########################################################


def ninja_downloader(url, itemList):
    r = requests.get(url)
    r.raise_for_status()
    itemList.append(r.json())
    itemList.append("done")


def ninja_get_data(dataList, league):
    baseURL = "https://poe.ninja/api/data/{}Overview?league={}&type="
    ninjaCurrencyTypes = ["Fragment", "Currency"]
    ninjaTypes = [
        "Fossil",
        "Resonator",
        "Scarab",
        "Essence",
        "DivinationCard",
        "Prophecy",
        "UniqueJewel",
        "UniqueWeapon",
        "UniqueArmour",
        "UniqueAccessory",
        "UniqueFlask",
        "UniqueJewel"
    ]

    urls_to_download = []
    for itemType in ninjaTypes:
        urls_to_download.append(baseURL.format("Item", league) + itemType)
    for currencyType in ninjaCurrencyTypes:
        urls_to_download.append(baseURL.format("Currency", league) + currencyType)

    dataCollection = []
    for j in range(len(urls_to_download)):
        dataCollection.append([])
        _thread.start_new_thread(ninja_downloader, (urls_to_download[j], dataCollection[j]))

    while True:
        try:
            done = False
            for subList in dataCollection:
                if subList[-1] == "done":
                    done = True
                else:
                    raise IndexError
            if done:
                break
        except IndexError:
            time.sleep(0.1)
            pass

    dataList.append({})
    for subList in dataCollection:
        for itemDictionary in subList[0]["lines"]:
            try:
                if itemDictionary["links"] == 0 or \
                        itemDictionary["name"] == "Tabula Rasa" or \
                        itemDictionary["name"] == "Oni-Goroshi":
                    dataList[0][itemDictionary["name"]] = itemDictionary["chaosValue"]
            except KeyError:
                dataList[0][itemDictionary["currencyTypeName"]] = itemDictionary["chaosEquivalent"]
    dataList.append("done")


def poe_stash_downloader(url, poesessid, itemList, stashType):
    r = requests.get(url, cookies=poesessid)
    r.raise_for_status()

    for item in r.json()["items"]:
        if "typeLine" in item.keys():
            if "stackSize" in item.keys():
                for i in range(item["stackSize"]):
                    itemList.append(item["typeLine"])
            else:
                itemList.append(item["typeLine"])
        else:
            itemList.append(item["name"])


def poe_get_data(userName, league, dataList, poesessid):
    baseURL = "https://www.pathofexile.com/character-window/get-stash-items?league={}&accountName={}&tabs={}"
    addinURL = "&tabIndex="
    stashTabWhiteList = ["DivinationCardStash",
                         "PremiumStash",
                         "QuadStash",
                         "NormalStash",
                         "CurrencyStash",
                         "FragmentStash",
                         "EssenceStash"]

    probeURL = baseURL.format(league, userName, 1)
    probe = requests.get(probeURL, cookies=poesessid)
    probe.raise_for_status()

    toDownload = []
    for stashTab in probe.json()["tabs"]:
        if stashTab["type"] in stashTabWhiteList:
            toAppend = []
            toAppend.append(stashTab["n"])     # Name
            toAppend.append(stashTab["i"])     # Index Number
            toAppend.append(stashTab["type"])  # Stash Type
            toDownload.append(toAppend)

    if len(toDownload) < 44:
        print("This should not take long.")
    else:
        totalSleep = round((len(toDownload) + 1) / 45 * 60, 0)
        print("This is going to take at least {} seconds".format(totalSleep))

    throttelingCounter = 0
    for stashTab in toDownload:
        if throttelingCounter == 44:
            print("reached 45/60/60 limit. sleeping for 1 minute")
            time.sleep(60)
            print("continuing")
            throttelingCounter = 0
        throttelingCounter += 1
        stashContent = []
        url = baseURL.format(league, userName, 0) + addinURL + str(stashTab[1])
        print("downloading \"{}\"".format(stashTab[0]))
        poe_stash_downloader(url, poesessid, stashContent, stashTab[2])
        for itemName in stashContent:
            toAppend = []
            toAppend.append(itemName)
            toAppend.append(stashTab[0])
            dataList.append(toAppend)
    dataList.append("done")


if __name__ == "__main__":
    ts1 = time.time()
    writeFile = False
    league = "set me!"  # <------------------------------------------------------------ change this
    fileName = "chaos_report.csv"  # <------------------------------------------------- maybe change this
    minimumChaosValue = 2  # <--------------------------------------------------------- maybe change this
    accountName = "set me!"  # <------------------------------------------------------- change this
    cookie = {"POESESSID": "set me!"}  # <--------------------------------------------- change this
    # you can check the link below, if you don't know where to get the poesessid
    # https://github.com/Stickymaddness/Procurement/wiki/SessionID

    # here you can get a list of all leagues (look for 'id: "')
    # http://api.pathofexile.com/leagues

    if league == "set me!" or \
       accountName == "set me!" or \
       cookie["POESESSID"] == "set me":
        print("please enter your data in lines:\n147 to 151")
        input("press enter to quit")

    if writeFile:
        filePath = os.path.join(os.getcwd(), fileName)
        if os.path.isfile(filePath):
            input(fileName + " already exists.\npress enter to quit")
            quit()

    ninjaData = []
    poeData = []

    # less parallelized for debugging (usually takes > 2x as long)
    # ninja_get_data(ninjaData, league)
    # poe_get_data(accountName, league, poeData, cookie)

    # extremely dirty multithreaded implementation
    _thread.start_new_thread(ninja_get_data, (ninjaData, league))
    _thread.start_new_thread(poe_get_data, (accountName, league, poeData, cookie))

    while True:
        try:
            if ninjaData[-1] == "done":
                if poeData[-1] == "done":
                    raise ChildProcessError
                else:
                    raise IndexError
            else:
                raise IndexError
        except IndexError:
            time.sleep(0.1)
            pass
        except ChildProcessError:
            break
    print("finished downloads, comparing now")


    csvData = []
    for item in poeData:
        try:
            if ninjaData[0][item[0]] >= minimumChaosValue:
                preFormatting = []
                preFormatting.append(item[0])
                preFormatting.append(ninjaData[0][item[0]])
                preFormatting.append(item[1])
                csvData.append(preFormatting)
        except KeyError:
            # Since we are looking up all items from all tabs this happens a lot.
            # Rare, Magic, and Normal items are not in poe.ninja, so they will throw an error.
            pass
    csvData.sort(key=lambda x: int(x[1]))  # sorting is slightly retarded
    csvData.reverse()
    csvData.insert(0, ["total",    0.0,              "yes"])
    csvData.insert(0, ["itemName", "value in chaos", "tabName"])
    for i in range(2, len(csvData)):
        csvData[1][1] += csvData[i][1]
    csvData[1][1] = round(csvData[1][1], 2)

    # writing the csv file
    if writeFile:
        with open(fileName, "w") as fileOut:
            for line in csvData:
                fileOut.write("\"{0}\";\"{1}\";\"{2}\"\n".format(line[0], line[1], line[2]))
            fileOut.close()

    # printing the csv table to the terminal
    longest_column_length = [0, 0, 0]
    for row in csvData:
        for column in range(3):
            if len(str(row[column])) > longest_column_length[column]:
                longest_column_length[column] = len(str(row[column]))
    for i in range(3):
        longest_column_length[i] += 2
    print()
    for column in csvData:
        for i in range(3):
            print("{0:{width}}".format(str(column[i]), width=longest_column_length[i]), end="")
        print()

    print("this took {} seconds".format(round(time.time() - ts1, 2)))
    quit()
