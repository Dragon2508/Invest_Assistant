# Модель скоринга https://studref.com/691325/finansy/model_skoringa_tsennyh_bumag
# Можно использовать модель Марковица https://github.com/Kotsubinskaya/PortfolioOptimization
# Сайт для проверки портфеля на исторических данных https://www.portfoliovisualizer.com/backtest-portfolio?s=y&allocation4_1=30&endYear=2022&initialAmount=10000&showYield=true&allocation1_1=40&allocation3_1=10&allocation2_1=20&symbol4=VBMFX&startYear=1985&symbol1=VTSMX&symbol2=VGTSX&symbol3=VGSIX
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

con = sqlite3.connect('db.db')
    
def model_scoring(ti, currency, cost, profit, risk, liquidity):

    array_J = np.array([])
    scoring_coef = {}
    scoring_procent = {}

    list_tiker = []
    trailingPE = np.array([])
    trailingEps = np.array([])
    beta = np.array([])
    debt = np.array([])
    averageVolume = np.array([])
    volume = np.array([])

    cur = con.cursor()
    query = """select ticker, trailing_PE, Trailing_EPS, beta, debt, average_volume, volume from Tickers
    order by id_ticker"""
    cur.execute(query)
    records = cur.fetchall()
    for row in records:
        list_tiker.append(row[0])
        trailingPE = np.append(trailingPE, row[1])
        trailingEps = np.append(trailingEps, row[2])
        #pegRatio = np.array([])
        beta = np.append(beta, row[3])
        debt = np.append(debt, row[4])
        averageVolume = np.append(averageVolume, row[5])
        volume = np.append(trailingPE, row[6])
    cur.close()

    trailingPE = preprocessing.normalize([trailingPE])
    trailingEps = preprocessing.normalize([trailingEps])
    beta = preprocessing.normalize([beta])
    debt = preprocessing.normalize([debt])
    averageVolume = preprocessing.normalize([averageVolume])
    volume = preprocessing.normalize([volume])


    for i, tiker in enumerate(list_tiker):
        profit_coef = 0.5 * trailingPE[0][i] + 0.5 * trailingEps[0][i]
        #print('Prof:', trailingPE[0][i], ' and ',trailingEps[0][i])
        risk_coef = 0.5 * beta[0][i] + 0.5 * debt[0][i]
        #print('Risk:', beta[0][i], ' and ', debt[0][i])
        liquidity_coef = 0.5 * averageVolume[0][i] + 0.5 * volume[0][i]
        #print('Prof:', averageVolume[0][i], ' and ',volume[0][i])
        J = profit * profit_coef + risk * risk_coef + liquidity * liquidity_coef
        scoring_coef[tiker] = J
        array_J = np.append(array_J, J)


    ticker_price = get_price_100(ti)
    scoring_coef = cost_portflio(scoring_coef, cost, ticker_price)

    # Удаление менее привлекательных акций
    total_dict = {}
    sectors = []
    total_cost = 0
    while len(scoring_coef.items()) != 0 and len(total_dict.items()) < 10:
        # Формируем 10 наиболее доходных акций + проводим диверсификацию
        for key, current_value in scoring_coef.items():
            max_value = scoring_coef[max(scoring_coef, key=scoring_coef.get)]
            if max_value == current_value:
                cur = con.cursor()
                cur.execute("""select name_sector from Sectors 
                where id_sector = (select id_sector from Tickers where ticker = ?)""", (key,))
                result = cur.fetchone()
                # Проверяем количество повторений в списке (не больше 3)
                if sectors.count(result[0]) < 2:
                    sectors.append(result[0])
                    # current_price = pdr.get_data_yahoo(key, start=datetime.datetime.now() - datetime.timedelta(days=2), end=datetime.datetime.now())['Close'][-1]
                    current_price = ticker_price[key]
                    total_cost += current_price
                    total_dict[key] = scoring_coef[key]

                del scoring_coef[key]
                break
    cur.close()
    sectors.append('Cash') # Добавление валюты 10%

    # Формирование состава процента
    sum_coef = 0
    for key, value in total_dict.items():
        sum_coef += value
    sum_coef = sum_coef + sum_coef * 0.1 # 10% Под валюту

    suma = 0
    for key, value in total_dict.items():
        procent = round(value/sum_coef * 100, 2)
        scoring_procent[key] =  procent
        suma +=  procent
    scoring_procent[currency] =  10.0

    return scoring_procent, sectors
    # Вывод результатов
    # print('Список секторов:', sectors)
    # print('Структура портфеля:', scoring_procent)
    # print('Cумма процентов:', round(suma), '%')
    # print('Итоговая стоимость портфеля (по 1 шт):', total_cost)

def cost_portflio(scoring_coef, cost, ticker_price):
    temp_dict = scoring_coef.copy()
    for key, value in temp_dict.items():
            try:
                current_price = ticker_price[key]
                if  current_price > 0.1 * cost:
                    del scoring_coef[key]
            except:
                del scoring_coef[key]

            #current_price = pdr.get_data_yahoo(key, start=datetime.datetime.now() - datetime.timedelta(days=2), end=datetime.datetime.now())['Close'][-1]

    return scoring_coef

def get_price_100(ti):
    url = 'https://ru.tradingview.com/markets/stocks-usa/market-movers-large-cap/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # Получение названий акций
    regex = re.compile('>[A-Z]{0,7}.[A-Z]{0,7}<.a>')
    matchs = regex.findall(str(soup))
    list_stocks = []
    ticker_price = {}

    for match in matchs:
        match = match.replace('>','')
        match = match.replace('</a','')
        list_stocks.append(match)

    regex = re.compile('<.div><.span><.td><td class="cell-v9oaRE4W right-v9oaRE4W">[0-9]{1,7}.[0-9]{1,7}<')
    matchs = regex.findall(str(soup))
    list_prices = []
    for match in matchs:
        match = match.replace('</div></span></td><td class="cell-v9oaRE4W right-v9oaRE4W">','')
        match = match.replace('<','')
        list_prices.append(match)

    # Проверка на наличие в Тинькофф Инвестиции/--
    cur = con.cursor()
    for i, stock in enumerate(list_stocks):
        cur.execute("""select * from Tickers where ticker = ? """, (stock,))
        if cur.fetchone() != None:
            ticker_price[list_stocks[i]] = float(list_prices[i])
    
    return ticker_price