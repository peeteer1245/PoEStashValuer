#!/usr/bin/env python3


##############################################################################################################
# Set your personal preferences here.
writeFile = False
fileName = "chaos_report.csv"  # <------------------------------------------------- maybe change this

minimumChaosValue = 2  # <--------------------------------------------------------- maybe change this

sortByUnitPrice = False  # <------------------------------------------------------- maybe change this

league = "set me!"  # <------------------------------------------------------------ change this
accountName = "set me!"  # <------------------------------------------------------- change this
poesessid = "set me!"  # <--------------------------------------------------------- change this
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
            dataCollection.extend(itemCategoryList["lines"])

    return dataCollection


def poe_stash_downloader(infoList):
    url = infoList[0]
    cookie = infoList[1]

    r = requests.get(url, cookies=cookie)

    r.raise_for_status()

    return r.json()["items"]


def poe_get_data(userName, league, poesessid):
    baseURL = "https://www.pathofexile.com/character-window/get-stash-items?league={}&accountName={}&tabs={}"
    addinURL = "&tabIndex="
    stashTabWhiteList = [
        "DivinationCardStash",
        "PremiumStash",
        "QuadStash",
        "NormalStash",
        "CurrencyStash",
        "FragmentStash",
        "EssenceStash"
    ]

    cookie = {"POESESSID": poesessid}

    probeURL = baseURL.format(league, userName, 1)

    probe = requests.get(probeURL, cookies=cookie)
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
        # for every 45 tabs you have, you have to wait 60 seconds
        totalSleep = int((len(toDownload) + 1) / 45) * 60
        print("This is going to take at least {} seconds".format(totalSleep))

    dataList = [probe.json()["tabs"]]

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
                tabsForThePool.append([url, cookie])

            for items in pool.imap_unordered(poe_stash_downloader, tabsForThePool):
                dataList.extend(items)
            downloadadTabsCounter += tabsToDownloadCounter

            if downloadadTabsCounter < len(toDownload):
                print("reached 45/60/60 limit. sleeping for 1 minute")
                time.sleep(60)
                print("continuing with download")
            else:
                break

    return dataList


def check_links(item):
    if "sockets" in item \
            and len(item["sockets"]) > 4:
        largestLink = 1
        linkCounter = 1
        lastSocketGroup = 0
        for socket in item["sockets"]:
            if socket["group"] == lastSocketGroup:
                linkCounter += 1
                largestLink = linkCounter
            else:
                linkCounter = 1
        if largestLink > 4:
            return largestLink
        else:
            return 0
    else:
        return 0


def compare_poe_with_ninja_data(poeData, ninjaData):
    poeTabInfos = poeData[0]
    poeData.pop(0)

    # creating a map to ease the process of getting the proper name of a stashtab
    poeTabNameMap = {}
    for tab in poeTabInfos:
        poeTabNameMap["Stash" + str(tab["i"]+1)] = tab["n"]

    csvData = []
    for item in poeData:
        # Map Fragments and Maps (non maps get filtered)
        if 0 <= item["frameType"] <= 2:
            # stackable Map Fragments
            for ninjaItem in ninjaData:
                if "stackSize" in item \
                        or ("descrText" in item and "Map Device" in item["descrText"]):
                    if "currencyTypeName" in ninjaItem \
                            and item["typeLine"] == ninjaItem["currencyTypeName"]:
                        amount = item["stackSize"] if "stackSize" in item else 1
                        csvData.append(
                            [
                                item["typeLine"],
                                round(ninjaItem["chaosEquivalent"] * amount, 2),
                                amount,
                                ninjaItem["chaosEquivalent"],
                                poeTabNameMap[item["inventoryId"]]
                            ]
                        )
                        break
                # Map Fragments and Maps basetypes
                elif "properties" in item \
                        and "name" in item["properties"] \
                        and item["properties"]["name"] == "Map Tier":
                    if "name" in ninjaItem \
                            and item["typeLine"] == ninjaItem["name"]:
                        csvData.append(
                            [
                                item["typeLine"],
                                ninjaItem["chaosValue"],
                                1,
                                ninjaItem["chaosValue"],
                                poeTabNameMap[item["inventoryId"]]
                            ]
                        )
                        break

        # Unique items
        elif item["frameType"] == 3:
            for ninjaItem in ninjaData:
                if "name" in ninjaItem \
                        and item["name"] == ninjaItem["name"] \
                        and item["typeLine"] == ninjaItem["baseType"] \
                        and ninjaItem["itemClass"] == 3 \
                        and check_links(item) == ninjaItem["links"]:
                    csvData.append(
                        [
                            item["name"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]]
                        ]
                    )
                    break

        # Gems get skipped
        elif item["frameType"] == 4:
            continue

        # everything stackable
        elif 5 <= item["frameType"] <= 6:
            if "stackSize" in item:
                for ninjaItem in ninjaData:
                    itemReferenceName = "name" if "name" in ninjaItem else "currencyTypeName"
                    chaosReferenceName = "chaosValue" if "chaosValue" in ninjaItem else "chaosEquivalent"
                    if item["typeLine"] == ninjaItem[itemReferenceName]:
                        csvData.append(
                            [
                                item["typeLine"],
                                round(ninjaItem[chaosReferenceName] * item["stackSize"], 2),
                                item["stackSize"],
                                ninjaItem[chaosReferenceName],
                                poeTabNameMap[item["inventoryId"]]
                            ]
                        )
                        break

        # Watchstones get skipped
        elif item["frameType"] == 7:
            continue

        # Prophecies
        elif item["frameType"] == 8:
            for ninjaItem in ninjaData:
                if "name" in ninjaItem \
                        and item["typeLine"] == ninjaItem["name"]:
                    csvData.append(
                        [
                            item["typeLine"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]]
                        ]
                    )
                    break

        # Relics
        elif item["frameType"] == 9:
            for ninjaItem in ninjaData:
                if "name" in ninjaItem \
                        and item["name"] == ninjaItem["name"] \
                        and ninjaItem["links"] == 0 \
                        and ninjaItem["itemClass"] == 9 \
                        and check_links(item) == ninjaItem["links"]:
                    csvData.append(
                        [
                            item["name"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]]
                        ]
                    )
                    break
    return csvData


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
    ts1 = time.time()

    if league == "?":
        print_valid_leagues()
        input("press enter to quit")
        quit(0)

    if league == "set me!" or \
            accountName == "set me!" or \
            poesessid == "set me!":
        print("please enter your data at the start of this file")
        input("press enter to quit")
        quit(1)

    if writeFile:
        filePath = os.path.join(os.getcwd(), fileName)

    print("downloading")

    ninjaData = ninja_get_data(league)
    poeData = poe_get_data(accountName, league, poesessid)

    print("finished downloads, comparing now")

    csvData = compare_poe_with_ninja_data(poeData, ninjaData)

    # culling items that are not worth enough
    csvData = [row for row in csvData if row[1] > minimumChaosValue]

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
