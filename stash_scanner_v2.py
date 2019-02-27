#!/usr/bin/env python3
import multiprocessing
import os
import time

try:
    import requests
except ImportError:
    print("you need the requests library for this script to work")
    quit()

########################################################
# remember to enter your data in lines 158 to 162
########################################################


def json_downloader(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def ninja_get_data(league):
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
    with multiprocessing.Pool(processes=len(urls_to_download)) as pool:
        for itemCategoryList in pool.imap_unordered(json_downloader, urls_to_download):
            for itemDictionary in itemCategoryList["lines"]:
                dataCollection.append(itemDictionary)

    dataList = {}
    for itemDictionary in dataCollection:
        try:
            if itemDictionary["links"] == 0 or \
               itemDictionary["name"] == "Tabula Rasa" or \
               itemDictionary["name"] == "Oni-Goroshi":
                dataList[itemDictionary["name"]] = itemDictionary["chaosValue"]
        except KeyError:
            dataList[itemDictionary["currencyTypeName"]] = itemDictionary["chaosEquivalent"]
    return dataList


def poe_stash_downloader(infoList):
    url = infoList[0]
    poesessid = infoList[1]
    stashType = infoList[2]
    stashName = infoList[3]

    itemList = []
    r = requests.get(url, cookies=poesessid)

    r.raise_for_status()

    for item in r.json()["items"]:
        if "typeLine" in item.keys():
            if "stackSize" in item.keys():
                for i in range(item["stackSize"]):
                    itemList.append([item["typeLine"], stashName])
            else:
                itemList.append([item["typeLine"], stashName])
        else:
            itemList.append([item["name"], stashName])

    if len(itemList) == 0:
        itemList.append(["Literally", stashName])
        itemList.append(["Empty", stashName])
    return itemList


def poe_get_data(userName, league, poesessid):
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

    dataList = []
    with multiprocessing.Pool(processes=45) as pool:
        downloadadTabsCounter = 0  # TODO: think of better names
        while True:
            # determine the amount of tabs to download in the current iteration
            tabsToDownloadCounter = 45  # TODO: think of better names
            if downloadadTabsCounter == 0:
                tabsToDownloadCounter = 44  # compensating for the probe
            if tabsToDownloadCounter > len(toDownload) - downloadadTabsCounter:
                tabsToDownloadCounter = len(toDownload) - downloadadTabsCounter  #

            tabsForThePool = []  # TODO: think of better names
            for i in range(downloadadTabsCounter, downloadadTabsCounter + tabsToDownloadCounter):
                url = baseURL.format(league, userName, 0) + addinURL + str(toDownload[i][1])
                tabsForThePool.append([url, poesessid, toDownload[i][2], toDownload[i][0]])

            for itemList in pool.imap_unordered(poe_stash_downloader, tabsForThePool):
                for item in itemList:
                    if item[0] != "Literally" or \
                            item[0] != "Empty":
                        dataList.append(item)
            downloadadTabsCounter += tabsToDownloadCounter

            if downloadadTabsCounter < len(toDownload):
                print("reached 45/60/60 limit. sleeping for 1 minute")
                time.sleep(60)
                print("continuing with download")
            else:
                break

    return dataList


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
            cookie["POESESSID"] == "set me!":
        print("please enter your data in lines:\n158 to 162")
        input("press enter to quit")

    if writeFile:
        filePath = os.path.join(os.getcwd(), fileName)
        if os.path.isfile(filePath):
            input(fileName + " already exists.\npress enter to quit")
            quit()

    print("downloading")

    ninjaData = ninja_get_data(league)
    poeData = poe_get_data(accountName, league, cookie)

    print("finished downloads, comparing now")

    csvData = []
    for item in poeData:
        try:
            if ninjaData[item[0]] >= minimumChaosValue:
                csvData.append([
                    item[0],                # item name
                    ninjaData[item[0]],     # it's price
                    item[1]                 # the StashTab that it is in
                    ])
        except KeyError:
            pass

    csvData.sort(key=lambda x: int(x[1]))  # for some reason also sorts by tabname
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

    print()
    print("this took {} seconds".format(round(time.time() - ts1, 2)))
    quit()
