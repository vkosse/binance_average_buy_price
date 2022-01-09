from binance import Client
from binance_keys import get_api_keys
import time
import requests
import hashlib
import hmac
import aiohttp
import asyncio


api_key, api_secret = get_api_keys()
client = Client(api_key, api_secret)


'''
def get_all_transactions():
    servertime = requests.get("https://api.binance.com/api/v1/time").json()
    timestamp = servertime['serverTime']
    transactions = []
    starttime = 1609459200000  # 01.01.2021
    interval = 7776000000  # 90 дней
    endtime = starttime + interval
    while True:
        query_string = f'timestamp={timestamp}&startTime={str(starttime)}&endTime={str(endtime)}'
        signature = hmac.new(api_secret.encode(
            'utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        starttime = endtime
        endtime += interval
        url = 'https://api.binance.com'
        headers = {'X-MBX-APIKEY': api_key}
        data = requests.get(
            f'{url}/sapi/v1/capital/deposit/hisrec?{query_string}&signature={signature}', headers=headers).json()
        if len(data) == 0:
            return transactions
        else:
            transactions.append(data)
'''


def get_all_transactions():
    '''
    Функция записывает в переменную "transactions" все транзакции на аккаунте
    с "starttime" = 01.01.2021 до того момента, пока за период 90 дней
    не будет найдено ни одной транзакции.
    Примечание:
    если за 90 дней осуществляется более 1000 транзакций,
    то необходимо уменьшить "interval".
    '''
    transactions = []
    starttime = 1609459200000  # 01.01.2021
    interval = 7776000000  # 90 дней
    endtime = starttime + interval
    while True:
        data = client.get_deposit_history(startTime=starttime, endTime=endtime)
        starttime = endtime
        endtime += interval
        if len(data) == 0:
            return transactions
        else:
            transactions.append(data)


def get_transactions_data():
    '''
    Функция обрабатывает все транзакции на аккаунте,
    а затем записывает полученные данные в словарь вида
    transactions_data = {coin: [insertTime, amount], []}
    '''
    transactions_data = {}
    all_transactions = get_all_transactions()
    for transactions in all_transactions:
        for transaction in transactions:
            if transaction['status'] == 1:
                starttime = transaction['insertTime']
                amount = float(transaction['amount'])
                transactions_data.setdefault(transaction['coin'], []).append(
                    [starttime, amount])
    return transactions_data


async def get_and_process_kline(session, result_data, amount, starttime, symbol, interval='1m', limit='1'):
    '''
    Функция ищет данные о цене монеты в момент совершения транзакции,
    а также увеличивает значение по ключу на количество затраченных на эту монету средств.
    '''
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={starttime}&limit={limit}'
    async with session.get(url) as response:
        data = await response.json()
        open_price = data[0][1]
        result_data[symbol] += (float(open_price) * amount)


async def main_func():
    '''
    Главная функция, которая обеспечивает вызов вспомогательных функций.
    Результатом работы функции является возврат словаря вида
    {'symbol': total_money, }
    '''
    transactions_data = get_transactions_data()
    result_data = {}
    async with aiohttp.ClientSession() as session:
        tasks = []
        for asset in transactions_data.keys():
            symbol = f'{asset}USDT'
            result_data[symbol] = 0
            for value in transactions_data[asset]:
                starttime, amount = value[0], value[1]
                task = asyncio.ensure_future(
                    get_and_process_kline(session, result_data, amount, starttime, symbol))
                tasks.append(task)
        await asyncio.gather(*tasks)
    return result_data


if __name__ == '__main__':
    start = time.time()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    transactions_result_data = asyncio.run(main_func())
    print(transactions_result_data)
    end = time.time()
    print('\n' + 'Elapsed time: ' + str(end - start) + ' sec')
