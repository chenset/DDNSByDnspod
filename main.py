# -*- coding:utf-8 -*-
import time
import json
import re
import urllib
import urllib2
import logging

# dnspos 的账号密码, 用于api的访问
DNSPOD_ACCOUNT = '4199191@qq.com'
DNSPOD_PASSWORD = ''

# 需要使用 DDNS 服务的域名地址
DOMAIN = 'chenof.com'
SUB_DOMAIN_LIST = ['@', 'www']  # 指定需要修改的主机记录
RECORD_LINE = '默认'  # 记录线路 默认|电信|联通|教育网|百度|搜索引擎 推荐保持默认


def http_request(url, data=()):
    response = None
    try:
        opener = urllib2.Request(url)
        opener.add_header('User-Agent', 'DDNSByDNSPod/1.0(4199191@qq.com)')  # DNSPod要求的User-Agent
        response = urllib2.urlopen(opener, urllib.urlencode(data)).read()
    except urllib2.HTTPError:
        logging.error(url + '地址无法联通')
    except Exception, e:
        logging.error(e)

    return response


def fetch_ip(content):
    result = re.search(
        '((?:(?:25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(?:25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d))))',
        content)
    if not result:
        return None
    return result.group(0)


def get_wan_ip():
    server_list = (  # 获取wan ip的网站地址, 可以执行添加更多
                     'http://1111.ip138.com/ic.asp',
                     'http://city.ip138.com/ip2city.asp',
                     'http://www.ip38.com/',
    )

    ip = None
    for server in server_list:
        try:
            html = http_request(server)
            ip = fetch_ip(html)
            if not ip:
                raise Exception(server + '响应的内容中无匹配的IP地址')

        except Exception, e:
            logging.error(e)
            continue
        else:
            break

    return ip


class DDNS():
    common_data = {'format': 'json', 'login_email': DNSPOD_ACCOUNT, 'login_password': DNSPOD_PASSWORD, }

    def __init__(self):
        pass

    def domain_info(self):
        post_data = self.common_data
        post_data['domain'] = DOMAIN

        response = http_request('https://dnsapi.cn/Domain.Info', post_data)
        if not response:
            return None

        return json.loads(response)

    def record_list(self, domain_id):
        post_data = self.common_data
        post_data['domain_id'] = domain_id

        response = http_request('https://dnsapi.cn/Record.List', post_data)
        if not response:
            return None

        return json.loads(response)

    def record_ddns(self, domain_id, record_id, sub_domain, record_line, value):
        post_data = self.common_data
        post_data['domain_id'] = domain_id
        post_data['record_id'] = record_id
        post_data['sub_domain'] = sub_domain
        post_data['record_line'] = record_line
        post_data['value'] = value

        response = http_request('https://dnsapi.cn/Record.Ddns', post_data)
        if not response:
            return None

        return json.loads(response)


def main():
    wan_id = get_wan_ip()
    if not wan_id:
        return

    d = DDNS()

    # 获取域名信息
    info_result = d.domain_info()

    if not info_result:
        return
    domain_id = info_result['domain']['id']

    # 获取域名下的解析记录
    record_list = d.record_list(domain_id)
    records = record_list['records']
    if not records:
        return

    # 过滤部分record
    change_records = []
    for row in records:
        old_ip = fetch_ip(row['value'])
        if not old_ip:
            continue
        if not row['name'] in SUB_DOMAIN_LIST:
            continue

        if old_ip == wan_id:  # 如果跟现在的IP相同则过掉
            continue

        change_records.append(
            {'domain_id': domain_id, 'record_id': row['id'], 'sub_domain': row['name'], 'record_line': RECORD_LINE,
             'value': wan_id, })

    if not change_records:
        logging.warning('没有记录需要修改')
        return

    # 执行DNS记录修改,实现DDNS
    index = 0
    for row in change_records:
        index += 1
        change_result = d.record_ddns(row['domain_id'], row['record_id'], row['sub_domain'], row['record_line'],
                                      row['value'])
        # print row['sub_domain']
        sub_domain = '' if row['sub_domain'] == '@' else row['sub_domain'] + '.'
        print str(index) + ': ' + sub_domain + record_list['domain']['name'] + ': ' + change_result['status']['message']


while True:
    main()
    time.sleep(60)  # 60秒尝试一次