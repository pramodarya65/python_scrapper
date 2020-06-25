import re
import json
import time
import math
import string
import asyncio
import aiohttp
from datetime import datetime
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
from bs4.element import Tag
from pprint import pprint
import soundex

import pymysql
from pymysql.err import OperationalError


CONNECTION_NAME = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'root@321'
DB_NAME = 'company_test'


mysql_config = {
  'user': DB_USER,
  'password': DB_PASSWORD,
  'db': DB_NAME,
  'charset': 'utf8',
  'cursorclass': pymysql.cursors.DictCursor,
  'autocommit': True
}
# Create SQL connection globally to enable reuse
# PyMySQL does not include support for connection pooling
mysql_conn = None

def __get_cursor():
    global mysql_conn
    """
    Helper function to get a cursor
      PyMySQL does NOT automatically reconnect,
      so we must reconnect explicitly using ping()
    """
    if not mysql_conn:
        try:
            mysql_conn = pymysql.connect(**mysql_config)
        except OperationalError:
            # If production settings fail, use local development ones
            mysql_config['unix_socket'] = f'/cloudsql/{CONNECTION_NAME}'
            mysql_conn = pymysql.connect(**mysql_config)

    try:
        return mysql_conn.cursor()
    except OperationalError:
        mysql_conn.ping(reconnect=True)
        return mysql_conn.cursor()





phantomjs_timeout = 30
recaptcha_max_retries = 60
recaptcha_api_key = '02be6b8fec0a92106abc3af2b17ccb07'


class RecaptchaMaxRetriesError(Exception): pass

async def solve_recaptcha(key, url):
    print('Start Get Recaptcha Solve Id rrrrrggh')
    async with aiohttp.ClientSession() as session:
        data = {
            'key': recaptcha_api_key,
            'method': 'userrecaptcha',
            'googlekey': '6LeVeDkUAAAAAC2dK8vev-V4PwG2y4Eg88kwDkcF',
            'pageurl': 'https://ahu.go.id/pencarian/profil-pt',
            'json': 1,
        }
        async with session.post('http://2captcha.com/in.php', data=data) as resp:
            recaptcha_solve_id = await resp.json()
            recaptcha_solve_id = recaptcha_solve_id['request']

        data = {
            'key': recaptcha_api_key,
            'action': 'get',
            'id': recaptcha_solve_id,
            'json': 1,
        }
        print('Start Get Recaptcha Solve Data')
        for i in range(recaptcha_max_retries):
            await asyncio.sleep(5)
            try:
                async with session.post('http://2captcha.com/res.php', data=data) as resp:
                    recaptcha_solve_data = await resp.json()
            except Exception:
                continue
            if recaptcha_solve_data['status'] == 1:
                return recaptcha_solve_data['request']

    raise RecaptchaMaxRetriesError


def construct_cookie_jar(cookies):
    print('constructing cookie jar')
    sc = SimpleCookie()
    for cookie in cookies:
        cookie_name = cookie['name']
        sc[cookie_name] = cookie['value']
        del cookie['name']
        del cookie['value']
        for key, value in cookie.items():
            sc[cookie_name][key] = value

    cj = aiohttp.CookieJar()
    cj.update_cookies(sc)
    return cj


async def get_cookie_jar():
    print('Passing ReCaptcha and getting cookies...')
    while True:
        proc = await asyncio.create_subprocess_exec('./phantomjs', 'recaptcha.js', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        try:
            while True:
                status = (await asyncio.wait_for(proc.stdout.readline(), phantomjs_timeout)).decode()[:-1]
                if status == 'recaptcha':
                    recaptcha_key = (await asyncio.wait_for(proc.stdout.readline(), phantomjs_timeout)).decode()[:-1]
                    recaptcha_url = (await asyncio.wait_for(proc.stdout.readline(), phantomjs_timeout)).decode()[:-1]

                    recaptcha_result = await solve_recaptcha(recaptcha_key, recaptcha_url)
                    proc.stdin.write('{0}\n'.format(recaptcha_result).encode())
                    await proc.stdin.drain()
                elif status == 'success':
                    print('Success!')
                    return construct_cookie_jar(json.loads((await asyncio.wait_for(proc.stdout.readline(), phantomjs_timeout)).decode()[:-1])['cookies'])
        except asyncio.TimeoutError:
            print('Phantomjs timed out, retrying')
        except RecaptchaMaxRetriesError:
            print('2captcha.com reached maximum retries, retrying')
        finally:
            proc.terminate()
            await proc.communicate()


searches_left = 0
sem1 = asyncio.Semaphore(20)
sem2 = asyncio.Semaphore(5)
prev_timestamp = None
prev_remain = None

async def process_search(conn, session, search, search_id):
    global searches_left
    global prev_timestamp
    global prev_remain

    async with sem1:
        companies = []
        i = 1
        while True:
            while True:
                async with sem2:
                    print('Search "{0}": page {1}'.format(search, i))
                    try:
                        soup = BeautifulSoup(await (await session.get('https://www.ahu.go.id/pencarian/bakum/cari/tipe/perseroan?nama={0}&page={1}'.format(search, i), timeout=5)).text(), 'html.parser')
                        assert soup.find(class_='mimik_tabel') is not None
                        break
                    except Exception as e:
                        print('Search "{0}": page {1} failed ({2}), retrying'.format(search, i, type(e).__name__))

            container = soup.find(id='hasil_cari')
            if container is None:
                break

            for div in container.find_all('div', attrs={'class': ['cl0', 'cl1']}):
                company_name_container = div.find(class_='judul')
                company_name = ''
                for element in company_name_container.contents:
                    if type(element) is Tag:
                        company_name += element.contents[0]
                    else:
                        company_name += str(element)
                company_name = company_name.strip()[4:]

                company_system_id = int(company_name_container['data-id'])
                company_address = div.find(class_='alamat').contents[0].strip()
                company_telp = div.find(class_='telp')
                if company_telp is not None:
                    company_telp = str(company_telp.contents[0])

                companies.append((company_system_id, company_name, company_address, company_telp))

            i += 1

        print('Search "{0}": inserting {1} companies...'.format(search, len(companies)))


        with __get_cursor() as cursor:
            
            cursor.executemany('insert ignore into companies (system_id,name,address,telp) values (%s,%s,%s,%s)', companies)
            cursor.execute('update searches set last_update=%s where id=%s', (datetime.now(), search_id))
            mysql_conn.commit()

        searches_left -= 1

        cur_timestamp = int(time.time() * 1000)
        if prev_timestamp is not None:
            microseconds_taken = cur_timestamp - prev_timestamp
            prev_timestamp = cur_timestamp
            microseconds_left_total = microseconds_taken * searches_left

            if prev_remain is not None:
                microseconds_left_total = int(((prev_remain * 100) + microseconds_left_total) / 101)
            prev_remain = microseconds_left_total

            hours_left = math.floor(((microseconds_left_total / 1000) / 60) / 60)
            minutes_left = math.floor(((microseconds_left_total - hours_left * 60 * 60 * 1000) / 1000) / 60)
            seconds_left = math.floor((microseconds_left_total - hours_left * 60 * 60 * 1000 - minutes_left * 60 * 1000) / 1000)
        else:
            prev_timestamp = cur_timestamp
            hours_left = 0
            minutes_left = 0
            seconds_left = 0

        print('Search "{0}": {1} companies inserted. {2} searches left. Time remaining: {3} hours, {4} minutes, {5} seconds'.format(search, len(companies), searches_left, hours_left, minutes_left, seconds_left))


async def main():
    global searches_left

    with __get_cursor() as cursor:
        sql = """SHOW TABLES LIKE 'companies'"""
        cursor.execute(sql)
        resTable = cursor.fetchone()
        if resTable is None:
            print('Creating necessary tables...')
            cursor.execute(
                """CREATE TABLE `companies` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `system_id` int(11) NOT NULL,
                        `name` varchar(255) NOT NULL,
                        `address` varchar(500) NOT NULL,
                        `telp` varchar(500) NOT NULL,
                        `report` text,
                        `code` text,
                        `viewCount` int(11) NOT NULL,
                        `countryCode` varchar(5) NOT NULL,
                        `country` varchar(100) NOT NULL,
                        `createdAt` datetime DEFAULT CURRENT_TIMESTAMP,
                        `updatedAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `status` tinyint(4) NOT NULL DEFAULT '1',
                        `city` varchar(255) NOT NULL,
                        `brand` varchar(255) DEFAULT NULL,
                        `soundex_name` varchar(255) DEFAULT NULL,
                        `soundex_brand` varchar(255) DEFAULT NULL,
                        PRIMARY KEY (id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=latin1"""
            )

            cursor.execute('''
                CREATE TABLE `searches` (
                `id` int(11) NOT NULL AUTO_INCREMENT,
                `text` text,
                `last_update` datetime DEFAULT NULL,
                PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
            ''')

            page_search_strings = []
            for i in string.ascii_lowercase:
                for j in string.ascii_lowercase:
                    for k in string.ascii_lowercase:
                        for l in string.ascii_lowercase:
                            page_search_strings.append(('{0}{1}{2}{3}'.format(i, j, k, l),))

            #print(page_search_strings)
            q = """ insert ignore into searches (text) values (%s) """
            cursor.executemany( q, page_search_strings)
            mysql_conn.commit()
        cookie_jar = await get_cookie_jar()
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'}
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5), headers=headers, cookie_jar=cookie_jar) as session:
            search_sql = """ select id,text from searches where last_update is null """
            cursor.execute(search_sql)
            searches = cursor.fetchall()
            arr_query_search=[]
            for search_res in searches:
                searchID=search_res['id']
                searchText=search_res['text']
                arr_query_search.append((searchID, searchText))
            searches_left = len(arr_query_search)
            await asyncio.gather(*[process_search(cursor, session, search, search_id) for search_id, search in arr_query_search])


if 4 <= 7:
	loop = asyncio.get_event_loop()
	loop.run_until_complete((main()))
	loop.close()
