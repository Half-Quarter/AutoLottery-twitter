# encoding:utf-8
import re

userIDs = []
fp = open("userdata.txt", "r", encoding='UTF-8')
sample = fp.readlines()

file = open("result.txt", "w", encoding='UTF-8')
cur = 0
for i in sample:
    if i[0] == '@':
        file.write(i)
        userIDs.append(i)
        print(userIDs[cur][1:])
        cur = cur + 1
fp.close()
file.close()

### 需求： 关注人数 - 粉丝数目 > 1500 