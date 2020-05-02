#!/usr/bin/env python3


##############################################################################################################
# Set your personal preferences here.
writeFile = False
fileName = "chaos_report.csv"  # <------------------------------------------------- maybe change this

minimumChaosValue = 2  # <--------------------------------------------------------- maybe change this

sortByUnitPrice = False  # <------------------------------------------------------- maybe change this

league = "set me!"  # <------------------------------------------------------------ change this
accountName = "set me!"  # <------------------------------------------------------- change this
poessid = "set me!"  # <----------------------------------------------------------- change this
# you can check the link below, if you don't know where to get the poesessid
# https://github.com/Stickymaddness/Procurement/wiki/SessionID

# enter a "?" in league, and execute the script, if you want a list of all valid leagues
##############################################################################################################

### start of code ###


import multiprocessing
import os
import time

try:
    import requests
except ImportError:
    print("you need the requests library for this script to work")
    quit()


def json_downloader(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def ninja_get_data(league):
    baseURL = "https://poe.ninja/api/data/{}Overview?league={}&type={}"
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
        "UniqueJewel",
        "DeliriumOrb",
        "Incubator",
        "UniqueMap",
        "Map",
        "Vial",
        "Oil"
    ]

    urls_to_download = []
    for itemType in ninjaTypes:
        urls_to_download.append(baseURL.format("Item", league, itemType))
    for currencyType in ninjaCurrencyTypes:
        urls_to_download.append(baseURL.format("Currency", league, currencyType))

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
                itemList.append([item["typeLine"], stashName, item["stackSize"]])
            elif "properties" in item.keys() and "name" in item["properties"][0].keys() and item["properties"][0]["name"] == "Map Tier":  # check if the item is a map
                if item["frameType"] == 3:
                    itemList.append([item["name"], stashName, 1])  # unique map
                else:
                    itemList.append([item["typeLine"], stashName, 1])  # non unique map
            elif item["frameType"] > 2:
                itemList.append([item["name"], stashName, 1])
            else:
                itemList.append([item["typeLine"], stashName, 1])
        else:
            itemList.append([item["name"], stashName, 1])

    if len(itemList) == 0:
        itemList.append(["Literally", stashName, -1])
        itemList.append(["Empty", stashName, -1])
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
        totalSleep = int((len(toDownload) + 1) / 45 * 60 - 60)
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


def print_valid_leagues():
    # Determines valid league by trial-and-error -ing against the poe.ninja API

    print("Getting valid leagues")

    poeApi = "http://api.pathofexile.com/leagues"
    ninjaApi = "https://poe.ninja/api/data/ItemOverview?league={}&type=Fossil"

    poeApiResponse = requests.get(poeApi)
    poeLeagues = [league["id"] for league in poeApiResponse.json()]

    matches = []
    for leagueName in poeLeagues:
        ninjaResponse = requests.get(ninjaApi.format(leagueName))
        if ninjaResponse.status_code == 200:
            matches.append(leagueName)

    print("The following leagues are valid:")
    [print(match) for match in matches]


if __name__ == "__main__":
    cookie = {"POESESSID": poessid}
    ts1 = time.time()

    if league == "?":
        print_valid_leagues()
        input("press enter to quit")
        quit(0)

    if league == "set me!" or \
            accountName == "set me!" or \
            cookie["POESESSID"] == "set me!":
        print("please enter your data at the start of this file")
        input("press enter to quit")
        quit(1)

    if writeFile:
        filePath = os.path.join(os.getcwd(), fileName)

    print("downloading")

    ninjaData = ninja_get_data(league)
    poeData = poe_get_data(accountName, league, cookie)

    print("finished downloads, comparing now")

    csvData = []
    for item in poeData:
        try:
            if ninjaData[item[0]] * item[2] >= minimumChaosValue:
                csvData.append([
                    item[0],                                 # item name
                    round(ninjaData[item[0]] * item[2], 2),  # the stacks total worth
                    item[2],                                 # how many of this is stacked
                    ninjaData[item[0]],                      # worth of each individual item
                    item[1],                                 # the StashTab that it is in
                    ])
        except KeyError:
            pass

    if sortByUnitPrice:
        csvData.sort(key=lambda x: x[3])
    else:
        csvData.sort(key=lambda x: x[1])
    csvData.reverse()
    csvData.insert(0, ["total",    0.0,              "",          "",                 ""])
    csvData.insert(0, ["itemName", "value in chaos", "stackSize", "individual value", "tabName"])
    for i in range(2, len(csvData)):
        csvData[1][1] += csvData[i][1]  # calculating total value
    csvData[1][1] = round(csvData[1][1], 2)  # rounding total value to 2 decimal points

    # writing the csv file
    if writeFile:
        with open(fileName, "w") as fileOut:
            for line in csvData:
                fileOut.write("\"{0}\";\"{1}\";\"{2}\";\"{3}\";\"{4}\"\n".format(line[0], line[1], line[2], line[3], line[4]))
            fileOut.close()

    # printing the csv table to the terminal
    longest_column_length = [0, 0, 0, 0, 0]
    for row in csvData:
        for column in range(5):
            if len(str(row[column])) > longest_column_length[column]:
                longest_column_length[column] = len(str(row[column]))
    for i in range(5):
        longest_column_length[i] += 2

    print()
    for row in csvData:
        for i in range(5):
            print("{0:{width}}".format(str(row[i]), width=longest_column_length[i]), end="")
        print()

    print()
    print("this took {} seconds".format(round(time.time() - ts1, 2)))

    if not writeFile:
        input("press enter to quit")

    quit()
