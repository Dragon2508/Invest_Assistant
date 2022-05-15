from sandbox import Sandbox_Ti
from sklearn import preprocessing # нормализация
from bs4 import BeautifulSoup # парсинг

import datetime
import pandas_datareader as pdr
import re # регулярные выражения
import yfinance as yf
import numpy as np
import requests
import time
import sqlite3
import math

def get_stocks_100(ti):
    # url = 'https://ru.tradingview.com/markets/stocks-russia/market-movers-large-cap/'
    url = 'https://ru.tradingview.com/markets/stocks-usa/market-movers-large-cap/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # Получение названий акций
    regex = re.compile('>[A-Z]{0,7}.[A-Z]{0,7}<.a>')
    matchs = regex.findall(str(soup))
    list_stocks = []
    for match in matchs:
        match = match.replace('>','')
        match = match.replace('</a','')
        list_stocks.append(match)

    # Проверка на наличие в Тинькофф Инвестиции/--
    stocks_tinkoff = ti.get_list_stocks()
    stocks_tinkoff_tiker = []
    for stock in stocks_tinkoff:
        stocks_tinkoff_tiker.append(stock.ticker)
    for stock in list_stocks:
        if not stock in  stocks_tinkoff_tiker:
            list_stocks.remove(stock)
    return list_stocks

def update(ti):
    # Проверка на необходимост обновлений
    con = sqlite3.connect('db.db')
    cur = con.cursor()
    cur.execute("""select current_date from Current_prices""")
    records = cur.fetchall()
    for record in records:
        if record[0] == datetime.datetime.today() - datetime.timedelta(days=1):
            return

    list_tiker = get_stocks_100(ti)
    for i, stock in enumerate(list_tiker):
        # if i < 90:
        #     continue
        print(i)
        token = yf.Ticker(stock)

        # Занесение текущих цен
        # dataframe = pdr.get_data_yahoo(stock, start=datetime.datetime.today() - datetime.timedelta(days=2), end=datetime.date.today())
        # previous_price = dataframe['Close'][-2]
        # current_price = dataframe['Close'][-1]
        
        # cur.execute("""insert into current_prices (id_ticker, current_change, current_date, current_price)
        # values ((select id_ticker from Tickers where ticker = ?),?, ?, ?) """,(stock, previous_price, datetime.date.today(),current_price))
        # con.commit()
        
        # Sectors
        # cur.execute("""Replace into Sectors (name_sector) values (?) """,(token.info['sector'],))
        # con.commit()

        # # Currency
        # cur.execute("""insert into Sectors (name_currency) values (?) """,(token.info['currency'],))
        # con.commit()

        # Tickers
        try:
            trailingPE = token.info['trailingPE']
        except:
            trailingPE = 0.1
        try:
            if not token.info['trailingEps']:
                trailingEps = 0
            else:
                trailingEps = token.info['trailingEps']
        except:
            trailingEps = 0.1
        try:
            if token.info['beta'] < 1 and token.info['beta'] > 0:
               beta = token.info['beta'] + 2
            elif token.info['beta'] < 0 or token.info['beta'] > 2 or token.info['beta'] == None:
                beta = 0.1
            else:
                beta = token.info['beta']
        except:
            beta = 0.1
        try:
            debt = token.info['totalRevenue']/token.info['totalDebt']
        except:
            debt = 0.1
        try:
            averageVolume = token.info['averageVolume']
        except:
            averageVolume = 0
        try:
            volume = token.info['volume']
        except:
            volume = 0
        
        cur.execute("""select id_ticker from Tickers where ticker = ?""", (stock,))
        if cur.fetchone() != None:
            cur.execute("""update Tickers  set id_sector = (select id_sector from Sectors where name_sector = ?),
                                            id_currency = (select id_currency from Currencies where name_currency = ?),
                                            trailing_EPS = ?,
                                            trailing_PE = ?,
                                            beta = ?,
                                            debt = ?,
                                            average_volume = ?,
                                            volume = ? where ticker = ?""",
            (token.info['sector'], token.info['currency'], trailingEps, trailingPE, beta, debt, averageVolume, volume, stock))
        else:
            cur.execute("""insert into Tickers 
            (ticker, id_sector, id_currency, trailing_EPS, trailing_PE, beta, debt, average_volume, volume)
            values (?,
                    (select id_sector from Sectors where name_sector = ?),
                    (select id_currency from Currencies where name_currency = ?),
                    ?, ?, ?, ?, ?, ?) """,
            ( stock, token.info['sector'], token.info['currency'], trailingEps, trailingPE, beta, debt, averageVolume, volume))
            con.commit()
            accounts = ti.get_sync_client().get_accounts().payload.accounts
            for account in accounts:
                cur.execute("""select id_ticker from Tickers where ticker = ? """, (stock,))
                id_ticker = cur.fetchone()[0]
                cur.execute("""insert into Tickers_accounts (id_ticker, number_account)
                values (?, ?)""", (id_ticker, account.broker_account_id))
        con.commit()        
    cur.close()