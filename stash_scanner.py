#!/usr/bin/env python3


########################################################################################
# Set your personal preferences here.
writeFile = False
fileName = "chaos_report.csv"  # <------------------- maybe change this

minimumChaosValue = 2  # <--------------------------- maybe change this

sortByUnitPrice = False  # <------------------------- maybe change this

league = "set me!"  # <------------------------------ change this
accountName = "set me!"  # <------------------------- change this
poesessid = "set me!"  # <--------------------------- change this
# you can check the link below, if you don't know where to get the poesessid
# https://github.com/Stickymaddness/Procurement/wiki/SessionID

# enter a "?" in league, and execute the script, if you want a list of all valid leagues
########################################################################################

### start of code ###

# due to a different tool DDoS-ing GGG we need to identify ourselves
# https://www.pathofexile.com/forum/view-thread/3019033/page/1#p23790007
HEADERS = {
    "User-Agent": "https://github.com/peeteer1245/PoEStashValuer",
}


import multiprocessing
import os
import time

try:
    import requests
except ImportError:
    print("you need the requests library for this script to work")
    quit()


def json_downloader(url: str) -> dict:
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def ninja_get_data(league: str) -> list:
    baseURL = "https://poe.ninja/api/data/{}Overview?league={}&type={}"
    ninjaCurrencyTypes = ["Fragment", "Currency"]
    ninjaTypes = [
        "DeliriumOrb",
        "DivinationCard",
        "Essence",
        "Fossil",
        "Incubator",
        "Map",
        "Oil",
        "Prophecy",
        "Resonator",
        "Scarab",
        "UniqueAccessory",
        "UniqueArmour",
        "UniqueFlask",
        "UniqueJewel",
        "UniqueJewel",
        "UniqueMap",
        "UniqueWeapon",
        "Vial",
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


def poe_stash_downloader(infoList: list) -> list:
    url = infoList[0]
    cookie = infoList[1]

    r = requests.get(url, cookies=cookie, headers=headers)

    r.raise_for_status()

    return r.json()["items"]


def poe_get_data(userName: str, league: str, poesessid: str) -> list:
    baseURL = "https://www.pathofexile.com/character-window/get-stash-items?league={}&accountName={}&tabs={}"
    addinURL = "&tabIndex="
    stashTabBlackList = [
        "MapStash",
    ]

    cookie = {"POESESSID": poesessid}

    probeURL = baseURL.format(league, userName, 1)

    probe = requests.get(probeURL, cookies=cookie, headers=headers)
    probe.raise_for_status()

    toDownload = []
    for stashTab in probe.json()["tabs"]:
        if stashTab["type"] not in stashTabBlackList:
            toAppend = []
            toAppend.append(stashTab["n"])  # Name
            toAppend.append(stashTab["i"])  # Index Number
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
            for i in range(
                downloadadTabsCounter, downloadadTabsCounter + tabsToDownloadCounter
            ):
                url = (
                    baseURL.format(league, userName, 0)
                    + addinURL
                    + str(toDownload[i][1])
                )
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


def count_item_links(item: dict) -> int:
    if "sockets" in item and len(item["sockets"]) > 4:
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


def item_is_map(item: dict) -> bool:
    if "properties" in item:
        for property in item["properties"]:
            if property["name"] == "Map Tier":
                return True
    return False


def compare_poe_with_ninja_data(poeData: list, ninjaData: list) -> list:
    poeTabInfos = poeData[0]
    poeData.pop(0)

    # creating a map to ease the process of getting the proper name of a stashtab
    poeTabNameMap = {}
    for tab in poeTabInfos:
        poeTabNameMap["Stash" + str(tab["i"] + 1)] = tab["n"]

    csvData = []
    for item in poeData:
        # Map Fragments and Maps (non map items get filtered)
        if 0 <= item["frameType"] <= 2:
            referenceAmount = item["stackSize"] if "stackSize" in item else 1
            for ninjaItem in ninjaData:
                referenceNinjaItemName = (
                    "name" if "name" in ninjaItem else "currencyTypeName"
                )
                referencePriceName = (
                    "chaosValue" if "chaosValue" in ninjaItem else "chaosEquivalent"
                )
                if item["typeLine"] in ninjaItem[referenceNinjaItemName]:
                    if item_is_map(item):
                        # getting the map tier
                        map_tier = 0
                        for property in item["properties"]:
                            if property["name"] == "Map Tier":
                                try:
                                    map_tier = int(property["values"][0][0])
                                except ValueError as e:
                                    raise e
                        if map_tier != ninjaItem["mapTier"]:
                            continue
                    csvData.append(
                        [
                            item["typeLine"],
                            round(ninjaItem[referencePriceName] * referenceAmount, 2),
                            referenceAmount,
                            ninjaItem[referencePriceName],
                            poeTabNameMap[item["inventoryId"]],
                        ]
                    )
                    break

        # Unique items
        elif item["frameType"] == 3:
            for ninjaItem in ninjaData:
                if (
                    "name" in ninjaItem
                    and item["name"] == ninjaItem["name"]
                    and item["typeLine"] == ninjaItem["baseType"]
                    and ninjaItem["itemClass"] == 3
                    and count_item_links(item) == ninjaItem["links"]
                ):
                    csvData.append(
                        [
                            item["name"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]],
                        ]
                    )
                    break

        # Gems get skipped
        elif item["frameType"] == 4:
            continue

        # everything stackable
        elif 5 <= item["frameType"] <= 6:
            # non seeds
            if "descrText" not in item or (
                "Sacred Grove" not in item["descrText"]
                or "to place it." in item["descrText"]
            ):
                for ninjaItem in ninjaData:
                    referenceAmount = item["stackSize"] if "stackSize" in item else 1
                    referenceNinjaItemName = (
                        "name" if "name" in ninjaItem else "currencyTypeName"
                    )
                    referencePriceName = (
                        "chaosValue" if "chaosValue" in ninjaItem else "chaosEquivalent"
                    )
                    if item["typeLine"] == ninjaItem[referenceNinjaItemName]:
                        csvData.append(
                            [
                                item["typeLine"],
                                round(
                                    ninjaItem[referencePriceName] * referenceAmount, 2
                                ),
                                referenceAmount,
                                ninjaItem[referencePriceName],
                                poeTabNameMap[item["inventoryId"]],
                            ]
                        )
                        break
            else:
                matches = []
                seedTier = 0
                monsterLevel = 0
                for itemProperty in item["properties"]:
                    if itemProperty["name"] == "Seed Tier":
                        seedTier = int(itemProperty["values"][0][0])
                    if (
                        itemProperty["name"]
                        == "Spawns a Level %0 Monster when Harvested"
                    ):
                        monsterLevel = int(itemProperty["values"][0][0])

                for ninjaItem in ninjaData:
                    if (
                        "name" in ninjaItem
                        and item["typeLine"] == ninjaItem["name"]
                        and seedTier == ninjaItem["mapTier"]
                        and monsterLevel >= ninjaItem["levelRequired"]
                    ):
                        matches.append(ninjaItem)

                if len(matches) == 0:
                    continue
                else:
                    bestMatch = matches[0]

                for match in matches:
                    if match["chaosValue"] > bestMatch["chaosValue"]:
                        bestMatch = match

                csvData.append(
                    [
                        item["typeLine"],
                        round(bestMatch["chaosValue"] * item["stackSize"], 2),
                        item["stackSize"],
                        bestMatch["chaosValue"],
                        poeTabNameMap[item["inventoryId"]],
                    ]
                )
                break

        # Watchstones get skipped
        elif item["frameType"] == 7:
            continue

        # Prophecies
        elif item["frameType"] == 8:
            for ninjaItem in ninjaData:
                if "name" in ninjaItem and item["typeLine"] == ninjaItem["name"]:
                    csvData.append(
                        [
                            item["typeLine"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]],
                        ]
                    )
                    break

        # Relics
        elif item["frameType"] == 9:
            for ninjaItem in ninjaData:
                if (
                    "name" in ninjaItem
                    and item["name"] == ninjaItem["name"]
                    and ninjaItem["links"] == 0
                    and ninjaItem["itemClass"] == 9
                    and count_item_links(item) == ninjaItem["links"]
                ):
                    csvData.append(
                        [
                            item["name"],
                            ninjaItem["chaosValue"],
                            1,
                            ninjaItem["chaosValue"],
                            poeTabNameMap[item["inventoryId"]],
                        ]
                    )
                    break
    return csvData


def print_valid_leagues():
    # Determines valid league by trial-and-error -ing against the poe.ninja API

    print("Getting valid leagues")

    poeApi = "http://api.pathofexile.com/leagues"
    ninjaApi = "https://poe.ninja/api/data/ItemOverview?league={}&type=Fossil"

    poeApiResponse = requests.get(poeApi, headers=headers)
    poeLeagues = [league["id"] for league in poeApiResponse.json()]

    matches = []
    for leagueName in poeLeagues:
        ninjaResponse = requests.get(ninjaApi.format(leagueName), headers=headers)
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

    if league == "set me!" or accountName == "set me!" or poesessid == "set me!":
        print("please enter your data at the start of this file")
        input("press enter to quit")
        quit(1)

    if writeFile:
        filePath = os.path.join(os.getcwd(), fileName)

    print("downloading")

    ninjaData = ninja_get_data(league)
    while True:
        try:
            poeData = poe_get_data(accountName, league, poesessid)
            break
        except requests.exceptions.HTTPError as e:
            print("pathofexile.com: too many requests")
            print("waiting for 1 minute")
            time.sleep(60)
    print("finished downloads, comparing now")

    csvData = compare_poe_with_ninja_data(poeData, ninjaData)

    # culling items that are not worth enough
    csvData = [row for row in csvData if row[1] > minimumChaosValue]

    if sortByUnitPrice:
        csvData.sort(key=lambda x: x[3])
    else:
        csvData.sort(key=lambda x: x[1])
    csvData.reverse()

    csvData.insert(0, ["total", 0.0, "", "", ""])
    csvData.insert(
        0, ["itemName", "value in chaos", "stackSize", "individual value", "tabName"]
    )
    for i in range(2, len(csvData)):
        csvData[1][1] += csvData[i][1]  # calculating total value
    csvData[1][1] = round(csvData[1][1], 2)  # rounding total value to 2 decimal points

    # writing the csv file
    if writeFile:
        with open(fileName, "w") as fileOut:
            for line in csvData:
                fileOut.write(
                    '"{0}";"{1}";"{2}";"{3}";"{4}"\n'.format(
                        line[0], line[1], line[2], line[3], line[4]
                    )
                )
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
            print(
                "{0:{width}}".format(str(row[i]), width=longest_column_length[i]),
                end="",
            )
        print()

    print()
    print("this took {} seconds".format(round(time.time() - ts1, 2)))

    if not writeFile:
        input("press enter to quit")

    quit()
