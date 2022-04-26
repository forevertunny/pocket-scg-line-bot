import requests
import re
import random
import configparser
import sys
import datetime
from pytz import timezone, utc
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials as SAC
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from imgurpython import ImgurClient

from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *

app = Flask(__name__)
config = configparser.ConfigParser()
config.read("config.ini")

line_bot_api = LineBotApi(config['line_bot']['Channel_Access_Token'])
handler = WebhookHandler(config['line_bot']['Channel_Secret'])
client_id = config['imgur_api']['Client_ID']
client_secret = config['imgur_api']['Client_Secret']
album_id = config['imgur_api']['Album_ID']
# API_Get_Image = config['other_api']['API_Get_Image']
testArry = []
userDict = {}


def main():
    pass


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'ok'


def pattern_mega(text):
    patterns = [
        'mega',
        'mg',
        'mu',
        'ＭＥＧＡ',
        'ＭＥ',
        'ＭＵ',
        'ｍｅ',
        'ｍｕ',
        'ｍｅｇａ',
        'GD',
        'MG',
        'google',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True


def eyny_movie():
    target_url = 'http://www.eyny.com/forum-205-1.html'
    print('Start parsing eynyMovie....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ''
    for titleURL in soup.select('.bm_c tbody .xst'):
        if pattern_mega(titleURL.text):
            title = titleURL.text
            if '11379780-1-3' in titleURL['href']:
                continue
            link = 'http://www.eyny.com/' + titleURL['href']
            data = '{}\n{}\n\n'.format(title, link)
            content += data
    return content


def apple_news():
    target_url = 'https://tw.appledaily.com/new/realtime'
    print('Start parsing appleNews....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('.rtddt a'), 0):
        if index == 5:
            return content
        link = data['href']
        content += '{}\n\n'.format(link)
    return content


def get_page_number(content):
    start_index = content.find('index')
    end_index = content.find('.html')
    page_number = content[start_index + 5:end_index]
    return int(page_number) + 1


def craw_page(res, push_rate):
    soup_ = BeautifulSoup(res.text, 'html.parser')
    article_seq = []
    for r_ent in soup_.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']
            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                rate = r_ent.find(class_="nrec").text
                url = 'https://www.ptt.cc' + link
                if rate:
                    rate = 100 if rate.startswith('爆') else rate
                    rate = -1 * int(rate[1]) if rate.startswith('X') else rate
                else:
                    rate = 0
                # 比對推文數
                if int(rate) >= push_rate:
                    article_seq.append({
                        'title': title,
                        'url': url,
                        'rate': rate,
                    })
        except Exception as e:
            # print('crawPage function error:',r_ent.find(class_="title").text.strip())
            print('本文已被刪除', e)
    return article_seq


def crawl_page_gossiping(res):
    soup = BeautifulSoup(res.text, 'html.parser')
    article_gossiping_seq = []
    for r_ent in soup.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']

            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                url_link = 'https://www.ptt.cc' + link
                article_gossiping_seq.append({
                    'url_link': url_link,
                    'title': title
                })

        except Exception as e:
            # print u'crawPage function error:',r_ent.find(class_="title").text.strip()
            # print('本文已被刪除')
            print('delete', e)
    return article_gossiping_seq


def ptt_gossiping():
    rs = requests.session()
    load = {'from': '/bbs/Gossiping/index.html', 'yes': 'yes'}
    res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=load)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    index_list = []
    article_gossiping = []
    for page in range(start_page, start_page - 2, -1):
        page_url = 'https://www.ptt.cc/bbs/Gossiping/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_gossiping = crawl_page_gossiping(res)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for index, article in enumerate(article_gossiping, 0):
        if index == 15:
            return content
        data = '{}\n{}\n\n'.format(article.get('title', None),
                                   article.get('url_link', None))
        content += data
    return content


def ptt_beauty():
    rs = requests.session()
    res = rs.get('https://www.ptt.cc/bbs/Beauty/index.html', verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    page_term = 2  # crawler count
    push_rate = 10  # 推文
    index_list = []
    article_list = []
    for page in range(start_page, start_page - page_term, -1):
        page_url = 'https://www.ptt.cc/bbs/Beauty/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_list = craw_page(res, push_rate)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for article in article_list:
        data = '[{} push] {}\n{}\n\n'.format(article.get('rate', None),
                                             article.get('title', None),
                                             article.get('url', None))
        content += data
    return content


def ptt_hot():
    target_url = 'http://disp.cc/b/PttHot'
    print('Start parsing pttHot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('#list div.row2 div span.listTitle'):
        title = data.text
        link = "http://disp.cc/b/" + data.find('a')['href']
        if data.find('a')['href'] == "796-59l9":
            break
        content += '{}\n{}\n\n'.format(title, link)
    return content


def movie():
    target_url = 'http://www.atmovies.com.tw/movie/next/0/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('ul.filmNextListAll a')):
        if index == 20:
            return content
        title = data.text.replace('\t', '').replace('\r', '')
        link = "http://www.atmovies.com.tw" + data['href']
        content += '{}\n{}\n'.format(title, link)
    return content


def technews():
    target_url = 'https://technews.tw/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('article div h1.entry-title a')):
        if index == 12:
            return content
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content


def panx():
    target_url = 'https://panx.asia/'
    print('Start parsing ptt hot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('div.container div.row div.desc_wrap h2 a'):
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content


def oil_price():
    target_url = 'https://gas.goodlife.tw/'
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.select('#main')[0].text.replace('\n', '').split('(')[0]
    gas_price = soup.select('#gas-price')[0].text.replace('\n\n\n',
                                                          '').replace(' ', '')
    cpc = soup.select('#cpc')[0].text.replace(' ', '')
    content = '{}\n{}{}'.format(title, gas_price, cpc)
    return content


def order(userName, text):
    print('Order ', userName, text)
    content = userName + ' Order Failure'
    GDriveJSON = 'RedInfoBot.json'
    GSpreadSheet = 'RedInfoOrder'
    while True:
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                'https://www.googleapis.com/auth/drive'
            ]
            key = SAC.from_json_keyfile_name(GDriveJSON, scope)
            gc = gspread.authorize(key)
            worksheet = gc.open(GSpreadSheet).sheet1
        except Exception as ex:
            print('無法連線Google試算表', ex)
            sys.exit(1)
        if text != "":
            splitText = text.split(' ')
            print(splitText)
            data = [userName, GetTime(), '', '', '', '']
            if len(splitText) >= 2:
                data[2] = splitText[1]
                if len(splitText) >= 3:
                    tryGet = tryGetNum(splitText[2])
                    if (tryGet['sucess']):
                        data[4] = tryGet['num']
                        if len(splitText) >= 4:
                            data[3] = splitText[3]
                    else:
                        data[3] = splitText[2]
                        if len(splitText) >= 4:
                            tryGet = tryGetNum(splitText[3])
                            if (tryGet['sucess']):
                                data[4] = tryGet['num']

            if (splitText[1] == ''):
                content = 'Ex:\n#吃 燕窩魚翅 Ps 9999 \n#喝 金薄珍珠奶茶 微糖少冰 800'
            elif 'eat' in text or '吃' in text:
                for i in range(3, 100):
                    cell = worksheet.cell(i, 1)
                    if (cell.value == ''):
                        # print('Add Eat Value ',i)
                        row_format = f'A{i}:E{i}'
                        row = worksheet.range(row_format)
                        for x, cell in enumerate(row):
                            cell.value = data[x]
                        worksheet.update_cells(row)
                        content = userName + ' Order Eat Sucess, No ' + str(i)
                        break
            elif 'drink' in text or '喝' in text:
                for i in range(3, 100):
                    cell = worksheet.cell(i, 8)
                    # print(cell.value)
                    if (cell.value == ''):
                        # print('Add Drink Value ',i)
                        row_format = f'H{i}:L{i}'
                        row = worksheet.range(row_format)
                        for x, cell in enumerate(row):
                            cell.value = data[x]
                        worksheet.update_cells(row)
                        content = userName + ' Order Drink Sucess, No ' + str(
                            i)
                        break
            #worksheet.append_row((userName,GetTime(), item,gold,remarks))

        return content


def delorder(userName, text):
    content = userName + ' Del Order Failure'
    GDriveJSON = 'RedInfoBot.json'
    GSpreadSheet = 'RedInfoOrder'
    while True:
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                'https://www.googleapis.com/auth/drive'
            ]
            key = SAC.from_json_keyfile_name(GDriveJSON, scope)
            gc = gspread.authorize(key)
            worksheet = gc.open(GSpreadSheet).sheet1
        except Exception as ex:
            print('無法連線Google試算表', ex)
            sys.exit(1)

        data = ['', '', '', '', '', '']

        if text != "":
            splitText = text.split(' ')
            print(splitText)

            if (len(splitText) >= 2):
                tryGet = tryGetNum(splitText[1])
                if (tryGet['sucess']):
                    index = tryGet['num']
                    row = None
                    if 'eat' in text or '吃' in text:
                        cell = worksheet.cell(index, 1)
                        if cell.value == userName:
                            row_format = f'A{index}:E{index}'
                            row = worksheet.range(row_format)
                            for x, cell in enumerate(row):
                                cell.value = data[x]
                            worksheet.update_cells(row)
                            content = userName + ' Del Order Sucess'
                    elif 'drink' in text or '喝' in text:
                        cell = worksheet.cell(index, 8)
                        if cell.value == userName:
                            row_format = f'H{index}:L{index}'
                            row = worksheet.range(row_format)
                            for x, cell in enumerate(row):
                                cell.value = data[x]
                            worksheet.update_cells(row)
                            content = userName + ' Del Order Sucess'
                else:
                    content = 'Ex:\n#刪吃 1(No)\n#刪喝 5(No)'
        return content


def uporder(userName, text):
    content = userName + ' Up Order Failure'
    GDriveJSON = 'RedInfoBot.json'
    GSpreadSheet = 'RedInfoOrder'
    while True:
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                'https://www.googleapis.com/auth/drive'
            ]
            key = SAC.from_json_keyfile_name(GDriveJSON, scope)
            gc = gspread.authorize(key)
            worksheet = gc.open(GSpreadSheet).sheet1
        except Exception as ex:
            print('無法連線Google試算表', ex)
            sys.exit(1)
        if text != "":
            splitText = text.split(' ')
            print(splitText)
            data = [userName, GetTime(), '', '', '', '']
            if len(splitText) >= 3:
                data[2] = splitText[2]
                if len(splitText) >= 4:
                    tryGet = tryGetNum(splitText[3])
                    if (tryGet['sucess']):
                        data[4] = tryGet['num']
                        if len(splitText) >= 5:
                            data[3] = splitText[4]
                    else:
                        data[3] = splitText[3]
                        if len(splitText) >= 5:
                            tryGet = tryGetNum(splitText[4])
                            if (tryGet['sucess']):
                                data[4] = tryGet['num']

            if (splitText[1] == '' or splitText[2] == ''):
                content = 'Ex:\n#修吃 1(No) 燕窩魚翅 PS 9999\n#修喝 5(No) 金薄珍珠奶茶 微糖少冰 800'
            else:
                tryGet = tryGetNum(splitText[1])
                if (tryGet['sucess']):
                    index = tryGet['num']
                    if 'eat' in text or '吃' in text:
                        cell = worksheet.cell(index, 1)
                        print(cell.value)
                        if cell.value == userName:
                            row_format = f'A{index}:E{index}'
                            row = worksheet.range(row_format)
                            for x, cell in enumerate(row):
                                cell.value = data[x]
                            worksheet.update_cells(row)
                            content = userName + ' Update Order Sucess'
                    elif 'drink' in text or '喝' in text:
                        cell = worksheet.cell(index, 8)
                        if cell.value == userName:
                            row_format = f'H{index}:L{index}'
                            row = worksheet.range(row_format)
                            for x, cell in enumerate(row):
                                cell.value = data[x]
                            worksheet.update_cells(row)
                            content = userName + ' Update Order Sucess'
                else:
                    content = 'Ex:\n#修吃 1(No) 燕窩魚翅 PS 9999\n#修喝 5(No) 金薄珍珠奶茶 微糖少冰 800'
        return content


def GetBcStory():
    print('GetBcStory')
    GDriveJSON = 'RedInfoBot.json'
    GSpreadSheet = 'BCStory'

    while True:
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                'https://www.googleapis.com/auth/drive'
            ]
            key = SAC.from_json_keyfile_name(GDriveJSON, scope)
            gc = gspread.authorize(key)
            worksheet = gc.open(GSpreadSheet).sheet1
        except Exception as ex:
            print('無法連線Google試算表', ex)
            sys.exit(1)

        #print('新增一列資料到試算表' ,GSpreadSheet)
        values = worksheet.get_all_values()
        # for data in values:
        #     print(data)

        index = random.randint(0, len(values) - 1)
        print(index)
        print(values[index][0])
        return values[index][0]


def test1():
    target_url = 'https://ptt-beauty-images.herokuapp.com/'
    print('Start test1')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    temp = []
    content = ""
    for data in soup.select('div.row div.images a.img-thumbnail'):
        link = data['href']
        temp.append(link)
    content = temp[random.randint(0, len(temp))]
    return content


def test3():
    target_url = 'https://argo-play.net/'
    aa = 'https://argo-play.net/album/2/6'
    print('Start test3')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    messages = []
    content = ""
    girlitems = soup.find('article').find('div', 'girl-list').find_all(
        'div', 'girl-item')
    index = random.randint(0, len(girlitems) - 1)
    #for i in range(3):
    element = girlitems[index]
    # print("0",element)
    picUrl = element.find('div', 'bg-cover').get('style').replace(
        'background-image: url(', target_url).replace(')', '')
    # print(element.find('div','bg-cover').get('style'))
    print(picUrl)
    print(element.find('div', 'girl-name').text)
    print(element.find('div', 'price').text)
    # details = element .find_all('div','detail-item')
    # for detail in details:
    #     print(detail.text)
    title = element.find('div', 'girl-name').text + ' ' + element.find(
        'div', 'price').text
    # content += '{}\n{}\n\n'.format(title, picUrl)

    messages.append(TextSendMessage(text=title))
    messages.append(
        ImageSendMessage(original_content_url=picUrl,
                         preview_image_url=picUrl))

    return messages


def test2():
    return 0


def bcstamp():
    timenow = GetTime()
    content = "Bc Tag " + timenow
    GDriveJSON = 'RedInfoBot.json'
    GSpreadSheet = 'BCTag'
    while True:
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                'https://www.googleapis.com/auth/drive'
            ]
            key = SAC.from_json_keyfile_name(GDriveJSON, scope)
            gc = gspread.authorize(key)
            worksheet = gc.open(GSpreadSheet).sheet1
        except Exception as ex:
            print('無法連線Google試算表', ex)
            sys.exit(1)
        #GetTime()
        for i in range(1, 31):
            # print(worksheet.cell(i,1).value)
            if (worksheet.cell(i, 1).value == ''):
                worksheet.update_acell(f'A{i}', timenow)
                break
        return content


def tryGetNum(value):
    try:
        return {'sucess': True, 'num': int(value)}
    except Exception:
        return {'sucess': False}


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event ", event)
    print("user_id: ", event.source.user_id)
    # print("group_id: ", event.source.group_id)
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)

    if (not event.source.user_id in userDict):
        print('UserId not in dict')
        if (event.source.type == 'group'):
            try:
                profile = line_bot_api.get_group_member_profile(
                    event.source.group_id, event.source.user_id)
                info = json.loads(str(profile))
                # print('UserInfo ',info)
                userDict[event.source.user_id] = info['displayName']
            except Exception as ex:
                print("Get UserId Err ", ex)
                sys.exit(1)
        else:
            try:
                profile = line_bot_api.get_profile(event.source.user_id)
                info = json.loads(str(profile))
                userDict[event.source.user_id] = info['displayName']
            except Exception as ex:
                print("Get UserId Err ", ex)
                sys.exit(1)

    # profile = line_bot_api.get_group_member_profile(<group_id>, <user_id>)

    if event.message.text.lower() == "test1":
        content = test1()
        # image = requests.get(API_Get_Image)
        # url = image.json().get('Url')
        url = content
        image_message = ImageSendMessage(original_content_url=url,
                                         preview_image_url=url)
        line_bot_api.reply_message(event.reply_token, image_message)
        return 0

    if event.message.text.lower() == "halloween":
        content ='Hello World'
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "萬聖節":
        content ='IAN 快樂'
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if "給糖" in event.message.text.lower():
        content ='給屁給 死屁孩'
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "bcstamp":
        content = bcstamp()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "lotteryargo":
        content = test3()
        line_bot_api.reply_message(event.reply_token, content)
        return 0
    if event.message.text.lower() == "test4":
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text='ABC'),
            ImageSendMessage(
                original_content_url=
                'https://argo-play.net//storage/upload/album/image/2019-10-04/gS13ixBTRpUrpf53X6m6C2AnSF8C7jjsFit2XbVV.jpeg',
                preview_image_url=
                'https://argo-play.net//storage/upload/album/image/2019-10-04/gS13ixBTRpUrpf53X6m6C2AnSF8C7jjsFit2XbVV.jpeg'
            )
        ])
        return 0

    if event.message.text.lower() == 'redinfo' or event.message.text.lower() == '紅信' or event.message.text.lower(
    ) == 'bot' or event.message.text.lower() == '機器人':
        content = "目前功能有:\n時間(now),\n點餐:\n#吃(#eat),#喝(#drink),\n#修吃(#upeat),#修喝(#updrink),\n#刪吃(#deleat),#刪喝(#deldrink)\n骰子(random)\n隨便來張正妹圖片\n蘋果即時新聞\n即時廢文"
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if "#eat" in event.message.text.lower(
    ) or "#drink" in event.message.text.lower(
    ) or "#吃" in event.message.text.lower(
    ) or "#喝" in event.message.text.lower():
        content = order(userDict[event.source.user_id], event.message.text)
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if "#upeat" in event.message.text.lower(
    ) or "#updrink" in event.message.text.lower(
    ) or "#修吃" in event.message.text.lower(
    ) or "#修喝" in event.message.text.lower():
        content = uporder(userDict[event.source.user_id], event.message.text)
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if "#deleat" in event.message.text.lower(
    ) or "#deldrink" in event.message.text.lower(
    ) or "#刪吃" in event.message.text.lower(
    ) or "#刪喝" in event.message.text.lower():
        content = delorder(userDict[event.source.user_id], event.message.text)
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "order" or event.message.text.lower(
    ) == "訂單":
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='https://reurl.cc/pDWQD4'))
        return 0
    if event.message.text.lower() == "bc故事" or event.message.text.lower(
    ) == "bcstory":
        content = GetBcStory()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "now" or event.message.text.lower(
    ) == "時間":
        content = GetTime()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if "random" in event.message.text.lower(
    ) or "骰子" in event.message.text.lower():
        content = 'Ex:\nRandom 0(Offset) To 2147483647\nRandom 要 不要'
        isSucess = False
        splitText = event.message.text.split(' ')
        print(splitText)
        try:
            if len(splitText) == 2:
                content = random.randint(0, int(splitText[1]))
                isSucess = True
            elif len(splitText) == 3:
                num1 = int(splitText[1])
                num2 = int(splitText[2])
                content = random.randint(num1, num2)
                isSucess = True
        except Exception:
            isSucess = False

        if (len(splitText) >= 2 and isSucess == False) or len(splitText) > 2:
            index = random.randint(0, len(splitText) - 2) + 1
            content = splitText[index]

        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text.lower() == "eyny":
        content = eyny_movie()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text == "蘋果即時新聞":
        content = apple_news()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    # if event.message.text == "PTT 表特版 近期大於 10 推的文章":
    #     content = ptt_beauty()
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text=content))
    #     return 0
    if event.message.text == "來張 imgur 正妹圖片":
        client = ImgurClient(client_id, client_secret)
        images = client.get_album_images(album_id)
        index = random.randint(0, len(images) - 1)
        url = images[index].link
        image_message = ImageSendMessage(original_content_url=url,
                                         preview_image_url=url)
        line_bot_api.reply_message(event.reply_token, image_message)
        return 0
    if event.message.text == "隨便來張正妹圖片":
        content = test1()
        url = content
        image_message = ImageSendMessage(original_content_url=url,
                                         preview_image_url=url)
        line_bot_api.reply_message(event.reply_token, image_message)
        return 0
    if event.message.text == "近期熱門廢文":
        content = ptt_hot()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text == "即時廢文":
        content = ptt_gossiping()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    # if event.message.text == "近期上映電影":
    #     content = movie()
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text=content))
    #     return 0
    if event.message.text == "觸電網-youtube":
        target_url = 'https://www.youtube.com/user/truemovie1/videos'
        rs = requests.session()
        res = rs.get(target_url, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        seqs = [
            'https://www.youtube.com{}'.format(data.find('a')['href'])
            for data in soup.select('.yt-lockup-title')
        ]
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text=seqs[random.randint(0,
                                                     len(seqs) - 1)]),
            TextSendMessage(text=seqs[random.randint(0,
                                                     len(seqs) - 1)])
        ])
        return 0
    if event.message.text == "科技新報":
        content = technews()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    if event.message.text == "PanX泛科技":
        content = panx()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0
    # if event.message.text == "開始玩":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='開始玩 template',
    #         template=ButtonsTemplate(
    #             title='選擇服務',
    #             text='請選擇',
    #             thumbnail_image_url='https://i.imgur.com/xQF5dZT.jpg',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='新聞',
    #                     text='新聞'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='電影',
    #                     text='電影'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='看廢文',
    #                     text='看廢文'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='正妹',
    #                     text='正妹'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    #     return 0
    # if event.message.text == "新聞":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='新聞 template',
    #         template=ButtonsTemplate(
    #             title='新聞類型',
    #             text='請選擇',
    #             thumbnail_image_url='https://i.imgur.com/vkqbLnz.png',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='蘋果即時新聞',
    #                     text='蘋果即時新聞'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='科技新報',
    #                     text='科技新報'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='PanX泛科技',
    #                     text='PanX泛科技'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    #     return 0
    # if event.message.text == "電影":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='電影 template',
    #         template=ButtonsTemplate(
    #             title='服務類型',
    #             text='請選擇',
    #             thumbnail_image_url='https://i.imgur.com/sbOTJt4.png',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='近期上映電影',
    #                     text='近期上映電影'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='eyny',
    #                     text='eyny'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='觸電網-youtube',
    #                     text='觸電網-youtube'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    #     return 0
    # if event.message.text == "看廢文":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='看廢文 template',
    #         template=ButtonsTemplate(
    #             title='你媽知道你在看廢文嗎',
    #             text='請選擇',
    #             thumbnail_image_url='https://i.imgur.com/ocmxAdS.jpg',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='近期熱門廢文',
    #                     text='近期熱門廢文'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='即時廢文',
    #                     text='即時廢文'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    #     return 0
    # if event.message.text == "正妹":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='正妹 template',
    #         template=ButtonsTemplate(
    #             title='選擇服務',
    #             text='請選擇',
    #             thumbnail_image_url='https://i.imgur.com/qKkE2bj.jpg',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='PTT 表特版 近期大於 10 推的文章',
    #                     text='PTT 表特版 近期大於 10 推的文章'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='來張 imgur 正妹圖片',
    #                     text='來張 imgur 正妹圖片'
    #                 ),
    #                 MessageTemplateAction(
    #                     label='隨便來張正妹圖片',
    #                     text='隨便來張正妹圖片'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    #     return 0
    # if event.message.text == "imgur bot":
    #     carousel_template_message = TemplateSendMessage(
    #         alt_text='ImageCarousel template',
    #         template=ImageCarouselTemplate(
    #             columns=[
    #                 ImageCarouselColumn(
    #                     image_url='https://i.imgur.com/g8zAYMq.jpg',
    #                     action=URIAction(
    #                         label='加我好友試玩',
    #                         uri='https://line.me/R/ti/p/%40gmy1077x'
    #                     ),
    #                 ),
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         carousel_template_message)
    #     return 0
    if event.message.text == "油價查詢":
        content = oil_price()
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=content))
        return 0

    # carousel_template_message = TemplateSendMessage(
    #     alt_text='目錄 template',
    #     template=CarouselTemplate(
    #         columns=[
    #             CarouselColumn(
    #                 thumbnail_image_url='https://i.imgur.com/kzi5kKy.jpg',
    #                 title='選擇服務',
    #                 text='請選擇',
    #                 actions=[
    #                     MessageAction(
    #                         label='開始玩',
    #                         text='開始玩'
    #                     ),
    #                     URIAction(
    #                         label='影片介紹 阿肥bot',
    #                         uri='https://youtu.be/1IxtWgWxtlE'
    #                     ),
    #                     URIAction(
    #                         label='如何建立自己的 Line Bot',
    #                         uri='https://github.com/twtrubiks/line-bot-tutorial'
    #                     )
    #                 ]
    #             ),
    #             CarouselColumn(
    #                 thumbnail_image_url='https://i.imgur.com/DrsmtKS.jpg',
    #                 title='選擇服務',
    #                 text='請選擇',
    #                 actions=[
    #                     MessageAction(
    #                         label='other bot',
    #                         text='imgur bot'
    #                     ),
    #                     MessageAction(
    #                         label='油價查詢',
    #                         text='油價查詢'
    #                     ),
    #                     URIAction(
    #                         label='聯絡作者',
    #                         uri='https://www.facebook.com/TWTRubiks?ref=bookmarks'
    #                     )
    #                 ]
    #             ),
    #             CarouselColumn(
    #                 thumbnail_image_url='https://i.imgur.com/h4UzRit.jpg',
    #                 title='選擇服務',
    #                 text='請選擇',
    #                 actions=[
    #                     URIAction(
    #                         label='分享 bot',
    #                         uri='https://line.me/R/nv/recommendOA/@vbi2716y'
    #                     ),
    #                     URIAction(
    #                         label='PTT正妹網',
    #                         uri='https://ptt-beauty-infinite-scroll.herokuapp.com/'
    #                     ),
    #                     URIAction(
    #                         label='youtube 程式教學分享頻道',
    #                         uri='https://www.youtube.com/channel/UCPhn2rCqhu0HdktsFjixahA'
    #                     )
    #                 ]
    #             )
    #         ]
    #     )
    # )
    #line_bot_api.reply_message(event.reply_token, carousel_template_message)


def GetTime():
    # print(datetime.datetime.utcnow())
    utc_dt = utc.localize(datetime.datetime.utcnow())
    # print(utc_dt)
    my_tz = timezone("Asia/Taipei")
    return utc_dt.astimezone(my_tz).strftime('%Y-%m-%d %H:%M:%S')


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    print("package_id:", event.message.package_id)
    print("sticker_id:", event.message.sticker_id)
    # ref. https://developers.line.me/media/messaging-api/sticker_list.pdf
    sticker_ids = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21, 100,
        101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
        115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128,
        129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 401, 402
    ]
    # index_id = random.randint(0, len(sticker_ids) - 1)
    # sticker_id = str(sticker_ids[index_id])
    # print(index_id)
    # sticker_message = StickerSendMessage(
    #     package_id='1',
    #     sticker_id=sticker_id
    # )
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     sticker_message)


if __name__ == '__main__':
    app.run()
    main()
