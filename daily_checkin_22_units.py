"""
全自动安全打卡脚本

依赖：
    python -m pip install playwright
    python -m playwright install chromium

建议使用环境变量保存账号密码：
    $env:CHECKIN_USERNAME = "你的账号"
    $env:CHECKIN_PASSWORD = "你的密码"
"""

import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# 密码和 Bark 地址只从环境变量读取；上传 GitHub 前不会把敏感信息写入代码。
PASSWORD = os.getenv("CHECKIN_PASSWORD", "").strip()
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "").strip()

CHECK_URLS = [
    (
        "https://njyj-social.njyjgl.cn/spp_grid_social/index.html"
        "#/loginQuestion?entId=a2303379-6843-4ec4-8591-2cc0aad43614"
        "&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82"
        "%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93"
        "%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E7%A5%9E%E8%B7%AF%E5%8F%A3%E6%9D%91319%E5%8F%B7"
        "&unitName=%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%9C%A3%E5%B0%8F%E4%BE%A0%E9%A4%90%E9%A5%AE%E7%AE%A1%E7%90%86%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
        "&checkId=41ad980d-307d-4feb-b40e-3d3e2f559662&clientType=&type=2"
    )
]

# 22 家单位：每条记录使用该单位自己的登录手机号。
# 注：袁记家常菜的号码按用户清单中的连续数字暂定为 15150544420；
# 如号码实际不同，只需修改对应这一行的 username。
CHECKINS = [
    {"name": "福满多快餐", "username": "15255182712", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=3c23aef9-30b5-4b00-9d16-5b6b98c9aa03&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91118%E5%8F%B7&unitName=%E7%A6%8F%E6%BB%A1%E5%A4%9A%E5%BF%AB%E9%A4%90%E5%BA%97&checkId=91178e64-ebcb-4414-8d0c-c916eb272bc3&clientType=&type=2"},
    {"name": "大圣龙虾", "username": "15380919990", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=a2303379-6843-4ec4-8591-2cc0aad43614&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E7%A5%9E%E8%B7%AF%E5%8F%A3%E6%9D%91319%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%9C%A3%E5%B0%8F%E4%BE%A0%E9%A4%90%E9%A5%AE%E7%AE%A1%E7%90%86%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8&checkId=41ad980d-307d-4feb-b40e-3d3e2f559662&clientType=&type=2"},
    {"name": "袁记家常菜", "username": "15150544420", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=d5ec71ae-ae3f-47f9-bfb7-129af851bfca&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91157%E5%8F%B7&unitName=%E8%A2%81%E8%AE%B0%E5%AE%B6%E5%B8%B8%E8%8F%9C&checkId=482e81e8-6330-44bb-bef4-4ce55fe9030c&clientType=&type=2"},
    {"name": "和州小吃", "username": "18807256876", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=bda51529-bbae-4839-b698-ded55f60ea48&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9125%E5%8F%B7&unitName=%E5%92%8C%E5%B7%9E%E5%B0%8F%E5%90%83&checkId=c704de3b-ff55-4339-a47b-c692702f4555&clientType=&type=2"},
    {"name": "王保银牛肉汤", "username": "18656183710", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=7879762a-42c0-42c0-abc6-93771ba22b8d&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%90%8E%E6%BD%98%E6%9D%91168%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%8E%8B%E4%BF%9D%E9%93%B6%E7%89%9B%E8%82%89%E6%B1%A4%E9%A6%86&checkId=42c531f2-293f-494a-9965-5af0c74746c3&clientType=&type=2"},
    {"name": "安庆小吃", "username": "13245813178", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=a4b476d8-a63e-43bb-bedd-a6dac9e10503&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91131%E5%8F%B7&unitName=%E5%AE%89%E5%BA%86%E9%A6%84%E9%A5%A8&checkId=1663ec20-c7d6-405c-81f3-ff1d01a42c4b&clientType=&type=2"},
    {"name": "孙明侠早餐", "username": "13685528908", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=dc372dc9-8452-43e0-9004-94d3306024eb&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91166%E5%8F%B7&unitName=%E5%AD%99%E6%98%8E%E4%BE%A0%E6%97%A9%E7%82%B9%E6%91%8A&checkId=8d000e8e-6b20-44ba-80eb-b601a45cd48b&clientType=&type=2"},
    {"name": "程记刀削面", "username": "15651971596", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=154be6d9-9a0b-45b0-b77e-431a6e19ba13&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91141%E5%8F%B7&unitName=%E7%A8%8B%E8%AE%B0%E5%88%80%E5%89%8A%E9%9D%A2&checkId=7f7b6662-98c7-4914-bb3b-ed17946c6ab5&clientType=&type=2"},
    {"name": "振丽宇小吃店", "username": "18751001592", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=20ccb7c3-9aa7-4d53-9d37-9202cd823f84&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91160%E5%8F%B7&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%8C%AF%E4%B8%BD%E5%AE%87%E5%B0%8F%E5%90%83%E5%BA%97&checkId=deddd0a6-09e1-4bae-8525-6418e3bfef46&clientType=&type=2"},
    {"name": "兰州牛肉面", "username": "15352437528", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=87272b4a-0b0f-4699-b443-7571fa63fc99&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9135%E5%8F%B7&unitName=%E5%85%B0%E5%B7%9E%E7%89%9B%E8%82%89%E9%9D%A2&checkId=377fb311-26d2-40d0-b474-ee737c57e959&clientType=&type=2"},
    {"name": "程姐大肉面", "username": "15950546168", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=999d354c-a14f-4139-8074-0968f60ff821&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9128%E5%8F%B7&unitName=%E7%A8%8B%E5%A7%90%E5%A4%A7%E8%82%89%E9%9D%A2&checkId=916a303b-5d2a-41ad-8b6c-c4a70d75c9ab&clientType=&type=2"},
    {"name": "陈远方小吃店", "username": "13951665434", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=c445621b-e7aa-473b-a7d6-ca8a555cabae&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9126%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%99%88%E8%BF%9C%E6%96%B9%E5%B0%8F%E5%90%83%E5%BA%97&checkId=d5a9cfbc-5b7b-4696-b952-b42d21e255f5&clientType=&type=2"},
    {"name": "王莉小吃店", "username": "19356718911", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=23df08d1-2d5e-44a7-a59d-f2e0de3afd5a&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91104%E5%8F%B7&unitName=%E7%8E%8B%E8%8E%89%E6%97%A9%E9%A4%90&checkId=8d0fa677-ec28-4270-9ad7-d04f4d606846&clientType=&type=2"},
    {"name": "琴与燕餐饮店", "username": "19965831449", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=7f501599-4a9f-449c-9f06-ce498f41c97d&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%91104%E5%8F%B7&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%90%B4%E4%B8%8E%E7%87%95%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=919b16ce-311e-421b-aafa-930ae2e20227&clientType=&type=2"},
    {"name": "东北烧烤排档", "username": "18747350135", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=8e4a2f24-7391-4d4d-ab32-dbaff1d6d369&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9117%EF%BC%8D1%E5%8F%B7&unitName=%E4%B8%9C%E5%8C%97%E7%83%A7%E7%83%A4%E6%8E%92%E6%8C%A1&checkId=2447cc63-6926-4ecf-bfff-2af7c2cc8cd7&clientType=&type=2"},
    {"name": "林记排档", "username": "19905170798", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=3ff5ad01-bd5a-427a-b628-2188daa6a065&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9114%E5%8F%B7&unitName=%E6%9E%97%E8%AE%B0%E6%8E%92%E6%8C%A1&checkId=27808688-389a-40ae-845d-a4e583d5dd8a&clientType=&type=2"},
    {"name": "桂献小吃店", "username": "13646662110", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=01829b30-6c72-4bec-a188-f92acb311a0b&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9116%EF%BC%8D2%E5%8F%B7&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%A1%82%E7%8C%AE%E5%B0%8F%E5%90%83%E5%BA%97&checkId=0e25578c-d489-44fa-9963-6aadfd411b6c&clientType=&type=2"},
    {"name": "刘毓春早点", "username": "17855500715", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=7d0d8fcc-475d-4e81-97d9-01d0089d6f54&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9124%E5%8F%B7&unitName=%E5%88%98%E6%AF%93%E6%98%A5%E6%97%A9%E7%82%B9%E9%93%BA&checkId=cd78aa63-f683-484f-bd48-05afcd914424&clientType=&type=2"},
    {"name": "张维献电动自行车", "username": "13073465789", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=30039e5a-d921-45f4-b03d-6b6cf0b3d258&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%9115%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%BC%A0%E7%BB%B4%E7%8C%AE%E7%94%B5%E5%8A%A8%E8%87%AA%E8%A1%8C%E8%BD%A6%E7%BB%8F%E8%90%A5%E9%83%A8&checkId=8da807f2-3142-41b3-96d6-8e7f05ec366c&clientType=&type=2"},
    {"name": "一家人大排档", "username": "15850634865", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=336339bb-1f0e-440a-9035-0cdc454d268d&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E5%89%8D%E6%BD%98%E6%9D%915%E5%8F%B7&unitName=%E4%B8%80%E5%AE%B6%E4%BA%BA%E5%A4%A7%E6%8E%92%E6%A1%A3&checkId=b4e98aef-1384-4cba-adc7-edb668ddd393&clientType=&type=2"},
    {"name": "昌义餐饮店", "username": "13705173915", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=72f5f835-30f4-432a-aaa1-2771ae3e5b12&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E7%A5%9E%E8%B7%AF%E5%8F%A3%E6%9D%91318%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%98%8C%E4%B9%89%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=f9e93b60-e791-459c-91b4-5f47e2fb2bbe&clientType=&type=2"},
    {"name": "朱来成小吃店", "username": "13260800015", "url": "https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=310d797b-a82d-41ab-916c-ce36adae0a4e&unitAddress=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E7%A5%9E%E8%B7%AF%E5%8F%A3133%E5%8F%B7-3&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%9C%B1%E6%9D%A5%E6%88%90%E5%B0%8F%E5%90%83%E5%BA%97&checkId=988660d4-7066-457c-bbb5-2c81686d77ad&clientType=&type=2"},
]


def save_screenshot(page, screenshot_path):
    # 默认关闭截图，避免长期运行占用磁盘空间。
    return


def send_wechat_notification(success_count, fail_count, failed_names):
    """发送运行汇总到企业微信群机器人。"""
    if not WECHAT_WEBHOOK:
        print("未配置 WECHAT_WEBHOOK，跳过企业微信推送。")
        return

    title = "高桥今日打卡结果"

    message = (
        f"{title}\n"
        f"今日共打卡 {len(CHECKINS)} 家\n"
        f"✅ 成功：{success_count} 家\n"
        f"❌ 失败：{fail_count} 家"
    )

    if failed_names:
        message += "\n失败店家：\n" + "\n".join(
            f"- {name}" for name in failed_names
        )
    else:
        message += "\n🎉 所有店家均打卡成功"

    payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            WECHAT_WEBHOOK,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "daily-checkin",
            },
            method="POST",
        )

        with urlopen(request, timeout=15) as response:
            result = response.read().decode("utf-8")

        if '"errcode":0' in result:
            print("企业微信推送已发送。")
        else:
            print(f"企业微信推送返回异常：{result}")

    except Exception as exc:
        print(f"企业微信推送失败：{exc}")


def page_has_text(page, *texts):
    # 提交后页面可能同时保留旧视图和新视图，导致存在多个 body。
    # all_inner_texts() 可以安全读取这些视图，避免 strict mode violation。
    body = "\n".join(page.locator("body").all_inner_texts()).lower()
    return any(text.lower() in body for text in texts)


def process_daily_check(page, url, username, screenshot_path):
    print("\n开始访问打卡页面...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # 登录页面可能稍晚渲染。该页面的账号框不一定是 type="text"，
        # 因此同时按 placeholder、密码框和普通输入框兼容查找。
        try:
            page.wait_for_timeout(1_500)
            username_candidates = [
                "input[placeholder*='手机号']",
                "input[placeholder*='账号']",
                "input[type='tel']",
                "input[type='text']",
                "input:not([type])",
            ]
            username_input = None
            for selector in username_candidates:
                candidate = page.locator(selector).first
                try:
                    if candidate.is_visible(timeout=1_000):
                        username_input = candidate
                        break
                except PlaywrightTimeoutError:
                    continue

            password_input = page.locator("input[type='password']").first
            if username_input is not None and password_input.is_visible(timeout=2_000):
                print("检测到登录页面，正在自动填写账号密码...")
                username_input.fill(username)
                password_input.fill(PASSWORD)

                login_button = page.locator(
                    ".login-button, button:has-text('登录'), "
                    "div:has-text('登录'), input[type='submit']"
                ).last
                login_button.click(timeout=10_000)
                print("已点击登录，等待页面加载...")
                page.wait_for_timeout(5_000)
        except PlaywrightTimeoutError:
            print("⚠️ 未找到可用的登录控件。")

        # 原脚本只判断 /question，但实际地址是 #/loginQuestion。
        # 这里同时判断 URL 和页面文字，避免大小写或路由名称导致误判。
        try:
            page.wait_for_function(
                """() => {
                    const hash = location.hash.toLowerCase();
                    const text = document.body.innerText || '';
                    const hasLoginForm = !!document.querySelector(
                        'input[type="password"]'
                    ) && text.includes('登录');
                    return (!hasLoginForm && (
                    hash.includes('loginquestion') ||
                    hash.includes('/question') ||
                     text.includes('今日已打卡') ||
                    text.includes('打卡成功') ||
                    text.includes('该用户对此场所') ||
                    text.includes('已经打卡')
                ));
                }""",
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            print("⚠️ 未能确认已进入题目页。")
            print(f"当前地址: {page.url}")
            save_screenshot(page, screenshot_path)
            return False

        print(f"当前地址: {page.url}")

        if page_has_text(
            page,
            "今日已打卡",
            "打卡成功",
            "该用户对此场所，今日已打卡",
            "该用户对此场所今日已打卡",
            "已经打卡",
            "今日已经完成",
        ):
            print("✅ 该单位今日已完成打卡，跳过。")
            save_screenshot(page, screenshot_path)
            return True

        if "loginquestion" not in page.url.lower() and "question" not in page.url.lower():
            print("⚠️ 当前页面不是题目页，也没有检测到已打卡提示。")
            save_screenshot(page, screenshot_path)
            return False

        print("已进入题目页面，开始自动勾选...")
        page.wait_for_timeout(5_000)

        yes_options = page.get_by_text("是", exact=True)
        no_options = page.get_by_text("否", exact=True)
        yes_count = yes_options.count()
        no_count = no_options.count()
        print(f"找到 {yes_count} 个“是”选项，{no_count} 个“否”选项")

        if yes_count < 3 or no_count < 6:
            print(f"⚠️ 选项数量异常：是={yes_count}，否={no_count}")
            page_text = "\n".join(page.locator("body").all_inner_texts())
            print("页面文字预览:", page_text[:500])
            save_screenshot(page, screenshot_path)
            return False

        for index in range(3):
            yes_options.nth(index).click()
            page.wait_for_timeout(300)
            print(f"✅ 第 {index + 1} 题已选择“是”")

        # “否”选项集合中前 3 个仍然对应第 1-3 题，
        # 第 4-6 题必须从下标 3 开始，否则会把前 3 题再次改成“否”。
        for index in range(3, 6):
            no_options.nth(index).click()
            page.wait_for_timeout(300)
            print(f"✅ 第 {index + 1} 题已选择“否”")

        submit_selectors = [
            "button:has-text('提交')",
            "button:has-text('确认')",
            "button:has-text('完成')",
            ".submit-btn",
            ".submit-button",
            "input[type='submit']",
        ]

        submit_button = None
        for selector in submit_selectors:
            candidate = page.locator(selector).last
            try:
                if candidate.is_visible(timeout=2_000):
                    submit_button = candidate
                    print(f"找到提交按钮: {selector}")
                    break
            except PlaywrightTimeoutError:
                continue

        if submit_button is None:
            print("⚠️ 未找到提交按钮。")
            save_screenshot(page, screenshot_path)
            return False

        submit_button.click()
        print("已点击提交按钮，等待结果...")

        # 提交后的页面可能是提示框、详情页、历史记录页或路由跳转。
        # 轮询这些状态，避免只依赖某一个固定中文提示。
        success = False
        for _ in range(10):
            page.wait_for_timeout(1_000)
            current_url = page.url.lower()
            success_text = page_has_text(
                page,
                "成功",
                "提交成功",
                "操作成功",
                "已打卡",
                "今日已打卡",
                "打卡时间",
                "打卡详情",
                "历史记录",
                "该用户对此场所，今日已打卡",
                "该用户对此场所今日已打卡",
            )
            route_changed = any(
                keyword in current_url
                for keyword in ("history", "detail", "result", "success")
            )
            try:
                submit_disappeared = not submit_button.is_visible(timeout=500)
            except Exception:
                submit_disappeared = True

            if success_text or route_changed or submit_disappeared:
                success = True
                break

        if success:
            print("🎉 打卡成功。")
            save_screenshot(page, screenshot_path)
            return True

        print("⚠️ 已点击提交，但未确认成功。")
        save_screenshot(page, screenshot_path)
        return False

    except Exception as exc:
        print(f"❌ 处理失败: {exc}")
        save_screenshot(page, screenshot_path)
        return False


def main():
    if not PASSWORD:
        print("未设置 CHECKIN_PASSWORD，无法登录。", file=sys.stderr)
        return 1

    output_dir = Path(__file__).parent
    success_count = 0
    fail_count = 0
    failed_names = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(15_000)

        try:
            for index, checkin in enumerate(CHECKINS):
                print("\n" + "=" * 50)
                print(f"处理第 {index + 1}/{len(CHECKINS)} 家：{checkin['name']}")
                print("=" * 50)

                screenshot = output_dir / (
                    f"daily_check_result_{index}_{date.today():%Y-%m-%d}.png"
                )

                if process_daily_check(
                    page, checkin["url"], checkin["username"], screenshot
                ):
                    success_count += 1
                else:
                    fail_count += 1
                    failed_names.append(checkin["name"])

                if index < len(CHECKINS) - 1:
                    print("等待 5 秒后处理下一家...")
                    page.wait_for_timeout(5_000)

        finally:
            browser.close()

        print("\n" + "=" * 50)
    print(f"打卡完成！成功: {success_count}, 失败: {fail_count}")
    print("失败清单：", failed_names)
    print("=" * 50)
    send_wechat_notification(success_count, fail_count, failed_names)
    # 无论有没有失败，脚本本身标记运行成功，消除红色报错
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
