'''
获取微博
'''

from urllib.parse import urlencode
from pyquery import PyQuery as pq
from pymongo import MongoClient
import re
import time
import random
import requests

def get_page(value, containerid, page):
    """获取页面微博列表"""
    params = {
        'type':	'uid',
        'value': value,
        'containerid': containerid,
        'page': page
    }
    url = base_url + urlencode(params)
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError as e:
        print('Error', e.args)

def parse_page(json):
    """解析网页"""
    if json:
        items = json.get('data').get('cards')
        for item in items:
            try:
                item = item.get('mblog')
                weibo = {}
                # 创建日期
                weibo['date'] = item.get('created_at')
                weibo['id'] = item.get('id')
                if item.get('isLongText') == True:
                    content = pq(item.get('text'))
                    result = re.search(r'<a.*?status.*?(\d{16}).*?"', str(content))
                    lt_id = result.group(1)
                    weibo['text'] = longtext(lt_id)
                else:
                    # 微博正文
                    weibo['text'] = pq(item.get('text')).text()
                weibo['source'] = item.get('source')
                # 转发数
                weibo['reposts'] = item.get('reposts_count')
                # 评论数
                weibo['comments'] = item.get('comments_count')
                # 点赞数
                weibo['attitudes'] = item.get('attitudes_count')
                # 转发原文内容
                if item.get('retweeted_status'):
                    weibo['repost_text'] = pq(item.get('retweeted_status').get('text')).text()
            except AttributeError as e:
                continue
            yield weibo

def longtext(id):
    """获取长微博内容"""
    url = 'https://m.weibo.cn/statuses/extend?id=' + id
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            longtext = response.json().get('data').get('longTextContent')
            return pq(longtext).text()
    except requests.ConnectionError as e:
        print('Error', e.args)


def save_to_mongo(result):
    """将返回结果result保存到MongoDB"""
    if collection.insert_many(result):
        print('Saved to mongodb')

if __name__ == '__main__':
    value = '1862855661'
    containerid = '1076031862855661'
    base_url = 'https://m.weibo.cn/api/container/getIndex?'
    headers = {
        'Host': 'm.weibo.cn',
        'Referer': 'https://m.weibo.cn/u/' + value,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;) Gecko/20100101 Firefox/63.0',
        'X-Requested-With': 'XMLHttpRequest'
    }
    myclient = MongoClient("mongodb://localhost:27017/")
    mydb = myclient["test"]
    collection = mydb["weibo" + value]
    page = 1
    while True:
        print('*'*50)
        print('正在爬取：第%s 页' %page)
        json = get_page(value, containerid, page)
        if not json.get('ok') == 0:
            results = parse_page(json)
            save_to_mongo(results)
            page += 1
            time.sleep(random.randint(1,4))
        else:
            print("下载完最后一页!")
            break
