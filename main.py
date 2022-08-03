# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import json
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

TIMEOUT = 60  ### 测试的时候，各个地方的timeout可以设置的小一点，在实际程序运行的时候需要设置的更大一点
ALLPARENTSNUMBER = 10000
USERINFOLIST = []
TRUSTLIST = []
baseUrl = 'https://www.twitter.com'


def init(url):
    cookieFile = './t-cookie.json'
    with open(cookieFile, 'r') as f:
        cookie = json.load(f)
    chromeOptions = webdriver.ChromeOptions()

    #chromeOptions.add_argument("--proxy-server=http://127.0.0.1:7890")
    #chromeOptions.add_argument('headless')

    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {"performance": "ALL"}  # newer: goog:loggingPrefs
    # 还有一种错误的做法
    # chrome_options.add_experimental_option('w3c', False)

    driver = webdriver.Chrome(options=chromeOptions, desired_capabilities=capabilities)
    while 1:
        try:
            driver.get(url)
            break
        except:
            sleep(TIMEOUT // 10)
    for item in cookie:
        if 'sameSite' in item:
            if item['sameSite'] != 'None' or item['sameSite'] != 'Strict' or item['sameSite'] != 'Lax':
               item['sameSite'] = 'Strict'
        driver.add_cookie(item)
    driver.get(url)
    print('Initialize Success!')
    return driver


def getUserInfo(driver, userPageUrl):
    driver.get(userPageUrl)
    nameXpath = '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div[1]/div/div[1]/div/div/span[1]/span'
    uidXpath = '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div[1]/div/div[2]/div/div/div/span'
    introXpath = '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/div/div/div/div/div[3]/div/div[1]/span[3]'
    followingNumXpath = '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/div/div/div/div/div[4]/div[1]/a/span[2]/span'


    name = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, nameXpath))).text
    uid = driver.find_element(By.XPATH, uidXpath).text
    try:
        intro = driver.find_element(By.XPATH, introXpath).text
    except:
        intro = ''
    try:
        followingNum = int(
            (driver.find_element(By.XPATH, followingNumXpath).text).replace(',', '').replace('.', '').replace('K',
                                                                                                              '000'))
    except:
        followingNum = 1000
    return [name, uid, intro, followingNum]


def getFollowingInfo(driver, userInfo):
    userFollowingPageUrl = baseUrl + '/' + userInfo[1] + '/following'
    driver.get(userFollowingPageUrl)
    sleep(TIMEOUT // 10)
    scrollUntilLoaded(driver)
    targetUserName = userInfo[0]
    sleep(TIMEOUT // 10)
    trueFollowerNum = getFollowingResponse(targetUserName, driver)
    return trueFollowerNum


def getFollowingResponse(targetUserName, driver):
    tmpTrueFollowerNum = 0
    for row in driver.get_log('performance'):
        log_data = row
        log_json = json.loads(log_data['message'])
        log = log_json['message']

        if log['method'] == 'Network.responseReceived' and 'Following' in log['params']['response']['url']:
            requestId = log['params']['requestId']
            try:
                responseBody = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": requestId})['body']
                oneResponseNum = decodeFollowingReponse(targetUserName, responseBody)
                tmpTrueFollowerNum += oneResponseNum
            except:
                pass
    print('\nfollowingNumbers:\t', tmpTrueFollowerNum)
    return tmpTrueFollowerNum


def decodeFollowingReponse(targetUserName, responseBody):
    responseBody = json.loads(responseBody)
    allInstructions = responseBody['data']['user']['result']['timeline']['timeline']['instructions']
    for instruction in allInstructions:
        if instruction['type'] == 'TimelineAddEntries':
            allEntries = instruction['entries']
            break
    verifiedEntries = 0
    for ids in range(len(allEntries) - 2):
        result = allEntries[ids]['content']['itemContent']['user_results']['result']
        if result.get('legacy'):
            userContent = result['legacy']
            name = userContent['name']
            intro = userContent['description']
            uid = userContent['screen_name']
            isVerified = userContent['verified']
            if isVerified:
                verifiedEntries += 1
                TRUSTLIST.append([targetUserName, name])
                USERINFOLIST.append([name, uid, intro, 0])
    return verifiedEntries


def scrollUntilLoaded(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(TIMEOUT // 6)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def save():
    userInfoFrame = pd.DataFrame(USERINFOLIST, columns=['name', 'uid', 'intro', 'followingNum'])
    trustFrame = pd.DataFrame(TRUSTLIST, columns=['followee', 'follower'])

    fileDir = "Twitter_" + str(ALLPARENTSNUMBER) + '/'
    if not os.path.exists(fileDir):
        os.makedirs(fileDir)
    userInfoFrame.to_csv(fileDir + "userInfo.csv", sep='\t')
    trustFrame.to_csv(fileDir + "trusts.csv", sep='\t')


if __name__ == '__main__':
    driver = init(baseUrl)
    startUserUrl = baseUrl + '/iirham6'
    # 对第一个用户的处理
    startUserInfo = getUserInfo(driver, startUserUrl)
    USERINFOLIST.append(startUserInfo)
    startUserFollowerNum = getFollowingInfo(driver, startUserInfo)
    USERINFOLIST[0][-1] = startUserFollowerNum

    # 后续用户重复处理
    levelCount = 0
    parentsUserInfo = USERINFOLIST[0]
    parentsUserNum, allUserNum = 1, 1
    try:
        while True:
            nextUserInfo = USERINFOLIST[parentsUserNum]
            trueFollowerNum = getFollowingInfo(driver, nextUserInfo)
            USERINFOLIST[allUserNum][-1] = trueFollowerNum
            allUserNum += trueFollowerNum
            parentsUserNum += 1
            print('number\t:', parentsUserNum)
            if parentsUserNum == ALLPARENTSNUMBER:
                break
        savedUserInfoLen = len(USERINFOLIST)
        for restUser in range(parentsUserNum + 1, savedUserInfoLen):
            userUrl = baseUrl + '/' + USERINFOLIST[restUser][1]
            trueFollowerNum = getUserInfo(driver, userUrl)
            USERINFOLIST[restUser][-1] = trueFollowerNum
            print('number\t:', restUser)
    except:
        save()
