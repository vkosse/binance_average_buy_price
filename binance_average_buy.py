from binance import Client
from binance_keys import get_api_keys
import time
import requests
import asyncio
from binance_transactions import *

api_key, api_secret = get_api_keys()
client = Client(api_key, api_secret)

'''
def get_user_data(session, query, address):
    signature = hmac.new(api_secret.encode('utf-8'),
                         query.encode('utf-8'), hashlib.sha256).hexdigest()
    url = 'https://api.binance.com'
    headers = {'X-MBX-APIKEY': api_key}
    userdata = session.get(
        f'{url}{address}?{query}&signature={signature}', headers=headers).json()
    return userdata


def get_filled_orders(session, symbol):
    try:
        servertime = session.get("https://api.binance.com/api/v1/time").json()
        timestamp = servertime['serverTime']
    except:
        print('Synchronize your clock!')
    query = f'symbol={symbol}&timestamp={timestamp}&limit=1000'
    address = '/api/v3/allOrders'
    orders = get_user_data(query, address)
    orders = [order for order in orders if order['status'] == 'FILLED']
    return orders[::-1]
'''


def get_my_assets():
    '''
    Функция возвращает название и количество актива в портфеле.
    '''
    all_assets = client.get_account()['balances']
    my_assets = {asset['asset']: float(asset['free']) + float(asset['locked'])
                 for asset in all_assets if float(asset['free']) + float(asset['locked']) > 0}
    return my_assets


def get_asset_precision(session, my_assets):
    '''
    Функция возвращает точность (знаки после запятой) для каждого актива.
    Это необходимо, так как для каждой монеты установлен различный минимальный размер ордера.
    '''
    precisions = {}
    symbols = []
    for asset in my_assets.keys():
        if asset != 'USDT':
            symbols.append(f'{asset}USDT')
    symbols_as_str = str(symbols).replace("'", '"').replace(' ', '')
    url = f'https://api.binance.com/api/v3/exchangeInfo?symbols={symbols_as_str}'
    response = session.get(url).json()
    for symbol in response['symbols']:
        min_quantity = symbol['filters'][2]['minQty']
        precision = len(str(min_quantity).rstrip('0').split('.')[1])
        asset = symbol['symbol'].replace('USDT', '')
        precisions.setdefault(asset, precision)
    return precisions


def find_avg(asset, precision, my_assets, transactions_result_data):
    '''
    Функция вычисляет среднюю цену покупки для каждого актива в портфеле.
    '''
    symbol = f'{asset}USDT'
    orders = client.get_all_orders(symbol=symbol, limit=1000)[::-1]
    max_remain_balance = 10 ** -precision
    asset_amount = my_assets[asset]
    current_asset_amount = asset_amount
    bought_asset, orders_money, commission_in_asset = 0, 0, 0
    result_precision = 8 - precision
    binance_fee = 0.001
    for order in orders:
        if order['status'] == 'FILLED':
            if order['side'] == 'BUY':
                bought_asset += float(order['executedQty']) * (1 - binance_fee)
                commission_in_asset += float(order['executedQty']
                                             ) * binance_fee
                asset_amount -= float(order['executedQty'])
                orders_money += float(order['cummulativeQuoteQty'])
            elif order['side'] == 'SELL':
                bought_asset -= float(order['executedQty'])
                asset_amount += float(order['executedQty'])
                orders_money -= float(order['cummulativeQuoteQty']
                                      ) * (1 - binance_fee)
        if round(asset_amount - max_remain_balance, precision + 1) < -commission_in_asset:
            avg_asset_buy = orders_money / bought_asset
            return asset, f'{avg_asset_buy:.{result_precision}f}', current_asset_amount
    transactions_money = transactions_result_data[symbol]
    avg_asset_buy = (transactions_money +
                     orders_money) / current_asset_amount
    return asset, f'{avg_asset_buy:.{result_precision}f}', current_asset_amount


def main():
    '''
    Главная функция, которая обеспечивает вызов вспомогательных функций.
    Результатом работы функции является возврат средней цены покупки каждого актива
    в виде кортежей вида (asset, avg_asset_buy)
    '''
    data = []
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    transactions_result_data = asyncio.run(main_func())
    session = requests.session()
    my_assets = get_my_assets()
    for asset, precision in get_asset_precision(session, my_assets).items():
        data.append(find_avg(asset, precision, my_assets, transactions_result_data))
    session.close()
    return data


if __name__ == '__main__':
    start = time.time()
    print(main())
    end = time.time()
    print('\n' + 'Elapsed time: ' + str(end - start) + ' sec')
