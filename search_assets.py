from sklearn import preprocessing
from ta.momentum import RSIIndicator

import numpy as np
import pandas_datareader as pdr
import datetime
import sqlite3

con = sqlite3.connect('db.db')
cur = con.cursor()


# Стоимость закупа и текущая стоимость портфеля
def analyse_buy(cost_buy, current_cost_portfolio, account_id):
    total_analyse = {}
    stocks_procent = {}
    cur.execute("""select T.ticker, P.procent from Portfolio P, Tickers T where T.id_ticker = P.id_ticker and P.number_account = ?""",
    (account_id,))

    records = cur.fetchall()
    for record in records:
        stocks_procent[record[0]] = record[1]

    good_stocks, compareing_arr, revenue_arr, rsi_arr = get_dict(stocks_procent, cost_buy, current_cost_portfolio, account_id)

    for i, (key, value) in enumerate(good_stocks.items()):
        total_analyse[key] = revenue_arr[0][i] + rsi_arr[0][i] - compareing_arr[0][i]
    stock = get_key(total_analyse, total_analyse[max(total_analyse, key=total_analyse.get)])
    count = int(cost_buy/good_stocks[stock])
    return stock, count

def get_key(dict, value):
    for k, v in dict.items():
        if v == value:
            return k

# Получение списка с сортированными акциями по доходности
def get_dict(stocks_procent, cost_buy, current_cost_portfolio, account_id):
    good_stocks = {}
    stocks_rsi = np.array([])
    revenue_array = np.array([])
    compare_array = np.array([])
    for ticker, procent in stocks_procent.items():
        # Compare
        # Получение цены
        stock_price = pdr.get_quote_yahoo(ticker)['price'][0]
        if stock_price > cost_buy:
            continue
        else:
            good_stocks[ticker] = stock_price
        # Получения числа акций
        cur.execute("""select purchase_count from Purchase_prices
         where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", (ticker, account_id))
        record = cur.fetchone()
        if record != None:
            stock_count = record[0]
        else:
            stock_count = 0
        # Вычисление и нормализация
        result = (stock_count * stock_price * 100/current_cost_portfolio) / procent
        compare_array = np.append(compare_array, result)  

        # Цены за 30 дней
        dataframe = pdr.get_data_yahoo(ticker, start=datetime.datetime.today() - datetime.timedelta(days=30), end=datetime.date.today())

        # Revenue
        value_first_day = dataframe['Close'][0]
        value_last_day = dataframe['Close'][-1]
        revenue_array = np.append(revenue_array, (value_last_day - value_first_day)/value_first_day * 100)

        # RSI
        stocks_rsi = np.append(stocks_rsi, RSIIndicator(close = dataframe['Close'], window=14).rsi()[-1])

    compare_array = preprocessing.normalize([compare_array]) 
    revenue_array = preprocessing.normalize([revenue_array])
    stocks_rsi = preprocessing.normalize([stocks_rsi]) 

    return good_stocks, compare_array, revenue_array, stocks_rsi