# Статья как изменить цвет рамки https://evileg.com/en/post/156/
# Документация - https://tinkoff.github.io/invest-openapi/swagger-ui/#/

from urllib import response
from sandbox import Sandbox_Ti
from PyQt5.QtWidgets import QMainWindow, QMessageBox,QSlider, QSizePolicy, QLineEdit, QFrame , QWidget, QWidgetAction, QAction, QApplication, QHBoxLayout, QVBoxLayout, QLabel, QCompleter, QComboBox, QMenu, QToolButton
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
from matplotlib.backends.backend_qt5agg import FigureCanvas
from create_portfolio import  model_scoring
from search_assets import analyse_buy
from update_db import update, get_stocks_100
from pytz import timezone
from yahooquery import Ticker

import numpy as np
import tinvest as tinv
import requests
import sys
import datetime
import pandas_datareader as pdr
import yfinance as yf
import sqlite3
import random

# Подключение библиотеки TA - техничекие индикаторы
import tinvest as tinv
import time
import matplotlib.pyplot as plt

# start_time = time.time()

class Form_LogIn(QMainWindow):    

    def __init__(self,parent=None):
        # For availability form
        super(Form_LogIn, self).__init__(parent)
        self.id_user = 1

        # Connecting qt + qss
        f = open('assets/styles/theme.qss','r')
        self.styleData = f.read() # styleData переменная класса
        f.close
        self.setStyleSheet(self.styleData)

        uic.loadUi('ui/LogIn.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))
        self.label_entry.setPixmap(QPixmap('assets/images/entry.png'))
        self.label_entry.installEventFilter(self)

        # Скрытие виджетов
        self.comboBox.hide()
        self.checkBox.hide()
        self.pushButton.hide()
        self.pushButton.hide()
        self.label_error.hide()
        self.label_password_error.hide()

        # Connect 
        self.pushButton.clicked.connect(lambda: self.logIn())
    
    def logIn(self):
        self.label_error.hide()
        global ti
        ti = Sandbox_Ti(self.comboBox.currentText())
        sync_client = ti.get_sync_client()

        global form_main # Так как переменная умирает после завершения функции
        try:
            form_main = Form_Main(sync_client)
        except:
            self.label_error.show()
            return

        cur = con.cursor()
        cur.execute("""select id_token from Tokens where token = ? """, (self.comboBox.currentText(),)) # Проверка на уже имеющийся токен
        if self.checkBox.isChecked() and cur.fetchone() == None:
                # Добавляем токен
                cur.execute("""insert or ignore into tokens (token) values (?)""", (self.comboBox.currentText(),))
                con.commit()

                cur.execute("""insert into Users_tokens (id_user, id_token) values (?,(select id_token from Tokens where token = ?)) """, (self.id_user, self.comboBox.currentText()))
                con.commit()

        if self.label_error.isVisible() == False:
            form_main.show()
            self.hide()
        cur.close()

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress and source is self.label_entry:
            self.get_tokens()
        return super(Form_LogIn, self).eventFilter(source, event)

    def get_tokens(self):
        # Запрос на совпадения пароля
        cur = con.cursor()
        cur.execute("""select id_user from Users where password = (?)""", (self.lineEdit_password.text(),))
        response = cur.fetchone()
        if response != None:
            self.label_password_error.hide()
            self.id_user = response[0]
            cur.execute("""select id_token from Users_tokens where id_user = ?""", (self.id_user,))
            ids = cur.fetchall()
            for id_token in ids:
                cur.execute("""select token from Tokens where id_token = ?""", (id_token[0],))
                record = cur.fetchone()
                self.comboBox.addItem(record[0])
            cur.close()
            # Показ скрытых виджетов
            self.comboBox.show()
            self.checkBox.show()
            self.pushButton.show()
        else:
            self.label_password_error.show()

class Form_Main(QWidget):    

    def __init__(self, sync_client,parent=None):
        # For availability form
        super(Form_Main, self).__init__(parent)
        self.sync_client = sync_client
        self.account_id = ''
        # Additional of file style 
        f = open('assets/styles/theme.qss','r')
        self.styleData = f.read() # styleData переменная класса
        f.close
        self.setStyleSheet(self.styleData)
        # Connecting qt + qss
        uic.loadUi('ui/Main.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))
        self.label_portfolio.setPixmap(QPixmap('assets/images/portfolio.png'))
        self.label_portfolio.installEventFilter(self)
        self.label_own_portfolio.setPixmap(QPixmap('assets/images/portfolio_own.png'))
        self.label_own_portfolio.installEventFilter(self)
        self.label_analyse.setPixmap(QPixmap('assets/images/analyse.png'))
        self.label_analyse.installEventFilter(self)
        self.label_sell.setPixmap(QPixmap('assets/images/sell.png'))
        self.label_sell.installEventFilter(self)
        # sandbox
        self.label_buy.installEventFilter(self)
        self.label_create.installEventFilter(self)
        self.label_create_IIS.installEventFilter(self)
        self.label_clear.installEventFilter(self)
        self.label_top_up.installEventFilter(self)
        self.label_delete.installEventFilter(self)

        # Прогресс бар
        # global progress_form
        # progress_form = ProgressBar()
        # progress_form.mySignal.connect(self.progress_change)

        # Заполнение comboBox
        for account in self.sync_client.get_accounts().payload.accounts:
            temp = account.broker_account_type + ' ' + account.broker_account_id
            self.comboBox.addItem(temp)
        self.change_account() # Для первого занесения account_id
        self.comboBox.currentIndexChanged.connect(lambda: self.change_account())

    # def progress_change(self, current_list):
    #     current_value =  progress_form.progressBar.value()
    #     progress_form.progressBar.setValue( current_value + 1)

    def resizeEvent(self, event):
        tabWidth = int(self.tabWidget.width() / 2.0)
        self.tabWidget.setStyleSheet( self.tabWidget.styleSheet() +
                                        "QTabBar::tab {"
                                        "width: " + str(tabWidth) + "px;"
                                        "min-height: 40px;}" )
        QWidget.resizeEvent(self, event)
    

    def change_account(self):
        # Запуск и обнуление прогресс бара
        # progress_form.progressBar.setValue(0)
        # progress_form.start()
        # progress_form.show()

        self.account_id = self.comboBox.currentText().split(' ')[1]
        self.build_diagram()
        self.get_portfolio()
        # print(self.account_id)

    def get_portfolio(self):
        cur = con.cursor()
        cur.execute("""select id_ticker, id_currency, procent from Portfolio
        where number_account  = (?)""", (self.account_id,))
        records = cur.fetchall()
        scoring = {}
        # sectors = []
        for record in records:
            if record[0] != None:
                cur.execute("""select ticker from Tickers where id_ticker = ?""", (record[0],))
            else:
                cur.execute("""select name_currency from Currencies where id_currency = ?""", (record[1],))
            stock = cur.fetchone()
            ticker = stock[0]
            scoring[ticker] = record[2]
            # cur.execute("""select name_sector from Sectors where id_sector = ?""", (id_sector,))
            # current_sector = cur.fetchone()[0]
            # sectors.append(current_sector)
        self.filling_portfolio(scoring)
        cur.close()

    def analysis_output(self):
        # Очищение layout 
        self.deleteItemsOfLayout(self.verticalLayout_analyse)

        # Занесение аналитики
        cost_portflio = 0
        list_cost = []
        list_name = []
        total_change = 0
        lots = 0
        current_price = 0
        current_change = 0
        list_positions = self.sync_client.get_portfolio(broker_account_id=self.account_id).payload.positions
        cur = con.cursor()
        for stock in list_positions:
            # Получаем данные об акциях и валюте
            if'USD' in stock.ticker:
                # Обновление баланса
                cur.execute("""update Currencies_prices set currencies_count = ?
                where id_currency = (select id_currency from Currencies where name_currency = 'USD') and number_account = ?""", (int(stock.balance), self.account_id))
                con.commit()

                cur.execute("""select currencies_price, currencies_count from Currencies_prices
                where id_currency = (select id_currency from Currencies where name_currency = 'USD') and number_account = ?""", (self.account_id,))
                record = cur.fetchone()
                lots = record[1]
                current_price = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()['Valute']['USD']['Value']
                current_change = round(float(current_price) - record[0], 2)
            elif 'EUR' in stock.ticker:
                # Обновление баланса
                cur.execute("""update Currencies_prices set currencies_count = ?
                where id_currency = (select id_currency from Currencies where name_currency = 'EUR') and number_account = ?""", (int(stock.balance), self.account_id))
                con.commit()

                cur.execute("""select currencies_price, currencies_count from Currencies_prices
                where id_currency = (select id_currency from Currencies where name_currency = 'EUR') and number_account = ?""", (self.account_id,))
                record = cur.fetchone()
                lots = record[1]
                current_price = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()['Valute']['EUR']['Value']
                current_change = round(float(current_price) - record[0], 2)
            else:
                cur = con.cursor()
                cur.execute("""select purchase_price, purchase_count, purchase_date from Purchase_prices
                where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ? """, (stock.ticker, self.account_id))
                record = cur.fetchone()
                lots = record[1]
                # pdr.get_data_yahoo(stock.ticker, start=datetime.datetime.now() - datetime.timedelta(days=2), end=datetime.datetime.now())['Close'][-1]
                current_price = round(pdr.get_quote_yahoo(stock.ticker)['price'][0], 2)
                current_change = round(current_price - record[0], 2)

            # Заносим на форму
            v_left_box = QVBoxLayout()
            label_name = QLabel()
            list_name.append(stock.name)
            label_name.setText(stock.name)
            label_buy_price = QLabel()
            label_buy_price.setStyleSheet('color: gray;')
            label_buy_price.setText(str(lots) + ' * ' +  str(round(current_price, 2)))
            v_left_box.addWidget(label_name)
            v_left_box.addWidget(label_buy_price)

            v_right_box = QVBoxLayout()
            label_cost = QLabel()
            cost_stock = round(float(lots) * float(current_price) + current_change, 2)
            if'USD' in stock.ticker or 'EUR' in stock.ticker:
                cost_portflio += round(float(lots), 2)
                list_cost.append(round(float(lots), 2))
                label_cost.setText(str(cost_stock) +' ₽')
            else:
                cost_portflio += cost_stock
                list_cost.append(cost_stock)
                label_cost.setText(str(cost_stock) +' $')

            label_change = QLabel()
            # Для добавления изменений в выбранной валюте
            if 'EUR' in stock.ticker or 'USD' in stock.ticker or 'RUB' in stock.ticker:
                total_change += round(current_change/current_price,2)
                label_change.setText(str(round(current_change/current_price,2)))
            else:
                total_change += current_change
                label_change.setText(str(current_change))

            if  current_change > 0:
                label_change.setStyleSheet('color: #1c5d3b;')
            elif current_change == 0:
                label_change.setStyleSheet('color:gray;')
                current_change = 0.0
            else:
                label_change.setStyleSheet('color: red;')
            v_right_box.addWidget(label_cost)
            v_right_box.addWidget(label_change)

            hbox = QHBoxLayout()
            hbox.addLayout(v_left_box)
            hbox.addLayout(v_right_box)

            self.verticalLayout_analyse.addLayout(hbox)

        cur.close()
        # Отображение результативности портфеля
        self.labelCostPortfolio.setText(str(round(cost_portflio + total_change, 2)) + ' $')
        if total_change > 0:
            self.labelTotalChange.setStyleSheet('color: #1c5d3b;')
        elif current_change == 0:
            self.labelTotalChange.setStyleSheet('color:gray;')
        else:
            self.labelTotalChange.setStyleSheet('color: red;')
        self.labelTotalChange.setText(str(round(total_change,2)) + ' $')

        return list_name, list_cost, cost_portflio, list_positions

    def build_diagram(self):
        # Очистка диаграмм
        self.deleteItemsOfLayout(self.layoutPlot)
        self.deleteItemsOfLayout(self.layoutPlotTwo)

        # https://www.pythoncharts.com/matplotlib/pie-chart-matplotlib/ 
        list_name, list_cost, cost_protfolio, list_position = self.analysis_output()
        # Диограмма компаний
        sizes = []
        for cost in list_cost:
            sizes.append(cost/cost_protfolio * 100)

        fig1, ax1 = plt.subplots()
        fig1.patch.set_facecolor('#ffffff')
        ax1.set(facecolor='#AAFFAA')

        cmap = plt.get_cmap('Greens')
        colors = list(cmap(np.linspace(0.55, 0.95, len(sizes))))
        # explode = (0, 0.1, 0, 0) 
        patches, texts, pcts = ax1.pie(
            sizes,
            labels=list_name,
            autopct='%1.1f%%',
            # wedgeprops={'linewidth': 1.0, 'edgecolor': 'white'},
            shadow=True,
            colors=colors,
            normalize=True,
            startangle=90
        )
        for i, patch in enumerate(patches):
            texts[i].set_color('gray')
        plt.setp(pcts, color='white')

        self.plotWidget = FigureCanvas(fig1)
        self.plotWidget.setStyleSheet('background:transparent;')
        self.layoutPlot.addWidget(self.plotWidget)

        # Диограмма секторов
        list_sector = []
        list_cost_sector = []
        for stock in list_position:
            t = Ticker(stock.ticker)
            if 'USD' in stock.ticker or 'EUR' in stock.ticker or 'RUB' in stock.ticker:
                list_sector.append('Сurrency')
            else:
                list_sector.append(t.asset_profile[stock.ticker]['sector'])

        # Суммируем одинаковые сектора
        cost = list_cost.copy()
        sectors = list_sector.copy()
        for i, sector_one in enumerate(sectors):
            sum_sector = cost[i]
            for j, sector_two in enumerate(sectors):
                if sector_one == sector_two and i != j:
                    sum_sector += cost[j]
                    del cost[j]
                    del sectors[j]
            list_cost_sector.append(sum_sector)

        fig2, ax2 = plt.subplots()
        fig2.patch.set_facecolor('#ffffff')
        ax2.set(facecolor='#AAFFAA')
        colors = list(cmap(np.linspace(0.55, 0.95, len(list_cost_sector))))

        # explode = (0, 0.1, 0, 0) 
        patches, texts, pcts = ax2.pie(
            list_cost_sector,
            labels=sectors,
            autopct='%1.1f%%',
            shadow=True,
            colors=colors,
            normalize=True,
            startangle=90
        )
        for i, patch in enumerate(patches):
            texts[i].set_color('gray')
        plt.setp(pcts, color='white')

        self.plotWidgetTwo = FigureCanvas(fig2)
        self.plotWidgetTwo.setStyleSheet('background:transparent;')
        self.layoutPlotTwo.addWidget(self.plotWidgetTwo)

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress and source is self.label_portfolio:
            self.create_portfolio()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_own_portfolio:
            self.create_own_portfolio()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_analyse:
            self.analyse_portfolio()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_sell:
            self.calculate_cost()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_buy:
            self.buy_stock()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_create:
            self.create_account('Брокерский счёт')
        elif event.type() == QEvent.MouseButtonPress and source is self.label_create_IIS:
            self.create_account('ИИС')
        elif event.type() == QEvent.MouseButtonPress and source is self.label_clear:
            self.clear_account()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_top_up:
            self.top_up_account()
        elif event.type() == QEvent.MouseButtonPress and source is self.label_delete:
            self.delete_account(self.account_id)
        return super(Form_Main, self).eventFilter(source, event)

    def create_account(self, account_type):
        # Иключения на уже созданные аккаунты
        accounts = self.sync_client.get_accounts().payload.accounts
        for account in accounts:
            if account.broker_account_type.value == 'Tinkoff' and account_type == 'Брокерский счёт':
                msg = QMessageBox(self)
                msg.setWindowTitle("Создание аккаунта")
                msg.setText("Не удалось создать аккаунт. Брокерский счёт уже существует.")
                msg.setIcon(QMessageBox.Warning)
                # msg.addButton("Ок", QMessageBox.NoRole)
                # msg.addButton("Да", QMessageBox.YesRole)
                msg.exec_()
                # print('Брокерский счёт уже существует')
                return
            elif account.broker_account_type.value == 'TinkoffIis' and account_type == 'ИИС':
                msg = QMessageBox(self)
                msg.setWindowTitle("Создание аккаунта")
                msg.setText("Не удалось создать аккаунт. ИИС уже существует.")
                msg.setIcon(QMessageBox.Warning)
                msg.exec_()
                # print('Не удалось создать аккаунт.ИИС уже существует')
                return

        id_account, type_account = ti.create_sandbox(account_type)
        cur = con.cursor()
        cur.execute("""insert into Broker_accounts (id_token, number_account, id_type)
         values ((select id_token from Tokens where token = ?), ?, (select id_type from Type_accounts where name_account = ?))""",(ti._key, id_account, type_account))
        cur.execute("""select id_ticker from Tickers""")
        id_tickers = cur.fetchall()
        for id_ticker in id_tickers:
            cur.execute("""insert into Tickers_accounts (id_ticker, number_account)
            values (?, ?) """, (id_ticker[0], id_account))
        con.commit()
        cur.close()

        self.comboBox.addItem(type_account + ' ' + id_account)
        self.comboBox.setCurrentText(type_account + ' ' + id_account)

    def delete_account(self, account_id):
        # Вопрос на удаление
        msg = QMessageBox(self)
        msg.setWindowTitle("Удаление аккаунта")
        msg.setText("Вы дейтсвительно хотите удалить аккаунт?")
        msg.setIcon(QMessageBox.Question)
        msg.addButton("Нет", QMessageBox.NoRole)
        msg.addButton("Да", QMessageBox.YesRole)
        reply = msg.exec_()

        if reply == 1:
            ti.delete_sandbox(account_id)
            cur = con.cursor()
            cur.execute("""delete from Broker_accounts where number_account = ? """, (account_id,))
            cur.execute("""delete from Currencies_prices where number_account = ? """, (account_id,))
            cur.execute("""delete from Tickers_accounts where number_account = ? """, (account_id,))
            cur.execute("""delete from Purchase_prices where number_account = ? """, (account_id,))
            cur.execute("""delete from Portfolio where number_account = ? """, (account_id,))
            con.commit()
            cur.close()
            self.comboBox.removeItem(self.comboBox.currentIndex())

    def clear_account(self):
        # Вопрос на очистку
        msg = QMessageBox(self)
        msg.setWindowTitle("Очистка аккаунта")
        msg.setText("Вы дейтсвительно хотите удалить все данные с аккаунта?")
        msg.setIcon(QMessageBox.Question)
        msg.addButton("Нет", QMessageBox.NoRole)
        msg.addButton("Да", QMessageBox.YesRole)
        reply = msg.exec_()

        if reply == 1:
            ti.clear_sandbox(self.account_id)
            # Удаление всех записей
            cur = con.cursor()
            cur.execute("""delete from Purchase_prices where number_account = ?""", (self.account_id,))
            cur.execute("""delete from Currencies_prices where number_account = ?""", (self.account_id,))
            con.commit()
            cur.close()
            # Обновление диаграмм
            self.build_diagram()

    def top_up_account(self):
        global top_up_form
        top_up_form = Form_TopUp(self.sync_client, self.account_id)
        top_up_form.show()

    def buy_stock(self):
        global buy_form
        buy_form = Form_Buy(self.sync_client, self.account_id)
        buy_form.show()

    def create_portfolio(self):
        global form_portfolio # Так как переменная умирает после завершения функции
        form_portfolio = Form_Portfolio(self.sync_client, self.account_id)
        form_portfolio.show()
    
    def create_own_portfolio(self):
        global form_own_portfolio # Так как переменная умирает после завершения функции
        form_own_portfolio = Form_OwnPortfolio(self.sync_client, self.account_id)
        form_own_portfolio.show()

    def filling_portfolio(self, scoring):
        if len(scoring) != 0:
            # Очищение структуры портфеля  
            self.deleteItemsOfLayout(self.verticalLayout_7)

            # Стоимость портфеля
            try:
                cost_portfolio = 0
                cur = con.cursor()
                cur.execute("""select currencies_count from Currencies_prices where number_account = ?""", (self.account_id,))
                count_dollar = cur.fetchone()
                cost_portfolio += count_dollar[0]
                cur.execute("""select purchase_price, purchase_count from Purchase_prices
                 where number_account = ?""", (self.account_id,))
                records = cur.fetchall()
                for record in records:
                    cost_portfolio += record[0] * record[1]
            except:
                return

            # Заполнение структуры
            for key, value in scoring.items():
                cur = con.cursor()
                if key in ('USD','EUR','RUB'):
                    cur.execute("""select currencies_price, currencies_count from Currencies_prices
                    where id_currency = (select id_currency from Currencies where name_currency = ?) and number_account = ? """, (key, self.account_id))
                    record = cur.fetchone()
                    if record != None:
                        stock_cost = record[1] * 100 / cost_portfolio
                    else:
                        stock_cost = 0
                else:    
                    cur.execute("""select purchase_price, purchase_count from Purchase_prices
                    where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ? """, (key, self.account_id))
                    record = cur.fetchone()
                    if record != None:
                        stock_cost = record[0] * record[1] * 100 / cost_portfolio
                    else:
                        stock_cost = 0
                
                # Название и процент
                hbox = QHBoxLayout()
                label_tiker = QLabel()
                label_tiker.setText(key)
                label_procent = QLabel()
                label_icon = QLabel()
                label_procent.setText(str(value) + "%" + " - "+ str(round(stock_cost,2)) +"%")

                # Графическое отображение фактического процента
                slider = QSlider()
                slider.setMaximum(int(value)*2) # Для чётности
                slider.setValue(int(stock_cost)*2)
                slider.setOrientation(Qt.Horizontal)
                slider.setTickPosition(QSlider.TickPosition.TicksBelow)
                slider.setTickInterval(int(value))
                slider.setEnabled(False)

                # Icon
                label_icon.setMaximumSize(QSize(15, 15))
                label_icon.setScaledContents(True)
                if (stock_cost > value-1 and stock_cost < value+1):
                    label_icon.setPixmap(QPixmap('assets/images/cool.png'))
                    slider.setStyleSheet('QSlider::sub-page:horizontal { background: #1c5d3b;}')
                    # label_fact.setStyleSheet('background: green;')
                elif stock_cost < value:
                    label_icon.setPixmap(QPixmap('assets/images/buy.png'))
                    slider.setStyleSheet('QSlider::sub-page:horizontal { background: #9ae199;}')
                    # label_fact.setStyleSheet('background: yellow;')
                elif stock_cost > value:
                    label_icon.setPixmap(QPixmap('assets/images/sold.png'))
                    slider.setStyleSheet('QSlider::sub-page:horizontal { background: red;}')
                    # label_fact.setStyleSheet('background: red;')
                hbox.addWidget(label_tiker)
                hbox.addWidget(label_procent)
                hbox.addWidget(label_icon)

                # Добавлене линии
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                # line.setFixedSize(QSize(30,2))

                # Добавление на вертикальный слой
                vbox = QVBoxLayout()
                vbox.addLayout(hbox)
                vbox.addWidget(slider)
                vbox.addWidget(line)

                # Занесение на главную форму
                self.verticalLayout_7.addLayout(vbox)
        else:
            self.deleteItemsOfLayout(self.verticalLayout_7)
    
    def deleteItemsOfLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.deleteItemsOfLayout(item.layout())

    def analyse_portfolio(self):
        global analysis_form
        analysis_form = Form_Analysis(self.sync_client, self.account_id, self.labelCostPortfolio.text())
        analysis_form.show()

    def calculate_cost(self):
        global calculate_form
        calculate_form = Form_Calculate(self.sync_client, self.account_id, self.labelCostPortfolio.text())
        calculate_form.show()

class Form_Portfolio(QWidget):    

    def __init__(self, sync_client, account_id, parent=None):
        # For availability form
        super(Form_Portfolio, self).__init__(parent)
        # Global value
        self.sync_client = sync_client
        self.account_id = account_id
        self.currency = ''
        self.cost = 500 # Минимальная стоимость портфеля
        self.profit = 0
        self.risk = 0
        self.liq = 0
        self.scoring = {}
        self.sectors = []
 
        uic.loadUi('ui/Portfolio.ui', self)
        #self.setStyleSheet('background-color: #393e3f;')
        self.setWindowTitle("Portfolio helper")
        self.setWindowIcon(QIcon('assets/images/icon.png'))
        
        # Шаг 1
        self.label_rub.setPixmap(QPixmap('assets/images/rub.png'))
        self.label_rub.installEventFilter(self)
        self.label_dollar.setPixmap(QPixmap('assets/images/dollar.png'))
        self.label_dollar.installEventFilter(self)
        self.tabWidget.tabBar().hide()

        # Connect
        self.pushButton.clicked.connect(lambda: self.next_button())
        self.pushButton_2.clicked.connect(lambda: self.next_button())
        self.pushButton_3.clicked.connect(lambda: self.next_button())
        self.pushButton_4.clicked.connect(lambda: self.next_button())
        self.horizontalSlider.valueChanged.connect(lambda:self.cost_changed())
        self.horizontalSlider_2.valueChanged.connect(lambda:self.profit_changed())
        self.horizontalSlider_3.valueChanged.connect(lambda:self.risk_changed())
        self.horizontalSlider_4.valueChanged.connect(lambda:self.liq_changed())

        # Обновление таблицы Tickers
        update(ti)
    def resizeEvent(self, event):
        tabWidth =  int(self.tabWidget.width() / 4.0)
        self.tabWidget.setStyleSheet( self.tabWidget.styleSheet() +
                                        "QTabBar::tab {"
                                        "width: " + str(tabWidth) + "px;"
                                        "min-height: 30px;}" )
        QWidget.resizeEvent(self, event)

    def cost_changed(self):
        self.label_horizontalSlider.setText(str(self.horizontalSlider.value()))
        self.cost = self.horizontalSlider.value()
    
    def profit_changed(self):
        coef_prof = self.horizontalSlider_2.value()/10.0
        self.label_horizontalSlider_2.setText(str(coef_prof))
        self.profit = round(coef_prof, 2)

    def risk_changed(self):
        coef_risk = self.horizontalSlider_3.value()/10.0
        self.label_horizontalSlider_3.setText(str(coef_risk))
        self.risk = round(coef_risk, 2)

    def liq_changed(self):
        coef_liq = self.horizontalSlider_4.value()/10.0
        self.label_horizontalSlider_4.setText(str(coef_liq))
        self.liq = round(coef_liq, 2)

    def next_button(self):
        if self.tabWidget.currentIndex() == 0:
            self.tabWidget.setCurrentIndex(1)
        elif self.tabWidget.currentIndex() == 1:
            self.tabWidget.setCurrentIndex(2)
        elif self.tabWidget.currentIndex() == 2:
            if (self.risk + self.profit + self.liq) == 1:
                self.scoring, self.sectors = model_scoring(ti, self.currency, self.cost, self.profit, self.risk, self.liq)
                self.fill_box(self.scoring, self.sectors)
                self.tabWidget.setCurrentIndex(3)

        elif self.tabWidget.currentIndex() == 3:
            # Очищение структуры портфеля
            self.deleteItemsOfLayout(self.verticalLayout_14)
        
            # Очищение секторов
            self.deleteItemsOfLayout(self.verticalLayout_17)

            # Проверка на наличие уже созаднной структуры у данного аккаунта
            cur = con.cursor()
            cur.execute("""select * from portfolio where number_account =?""", (self.account_id,))
            if cur.fetchone() != None:
                # Очистить базу если уже было заполнено портфолио
                cur.execute("""delete from Portfolio where number_account = ?""", (self.account_id,))

            # Заполнение базы если не было заполнено портфолио раньше
            for key, value in self.scoring.items():
                if not key in ('USD', 'EUR','RUB'):
                    cur.execute("""insert into Portfolio (id_ticker, procent, number_account)
                    values ((select id_ticker from Tickers where ticker = ?), ?, ?)""", (key, value, self.account_id))
                else:
                    cur.execute("""insert into Portfolio (id_currency, procent, number_account)
                    values ((select id_currency from Currencies where name_currency = ?), ?, ?)""", (key, value, self.account_id))
            con.commit()
            cur.close()

            # Заполнение идельного портфеля
            form_main.filling_portfolio(self.scoring)
            self.close()

    def deleteItemsOfLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.deleteItemsOfLayout(item.layout())

    def fill_box(self, scoring, sectors):
        for key, value in scoring.items():
            hbox = QHBoxLayout()
            hbox.setObjectName("clearLayout")
            label_tiker = QLabel()
            label_tiker.setText(key)
            label_procent = QLabel()
            label_procent.setText(str(value) + "%")

            hbox.addWidget(label_tiker)
            hbox.addWidget(label_procent)

            self.verticalLayout_14.addLayout(hbox)

        for i in range(len(sectors)):
            label_secotr = QLabel()
            label_secotr.setText(sectors[i])

            self.verticalLayout_17.addWidget(label_secotr)

    def eventFilter(self, source, event):
        # if event.type() == QEvent.MouseButtonPress and source is self.label_rub:
        #     if self.label_rub.styleSheet() == "background:#73dc98; border-radius:30px;":
        #         self.label_rub.setStyleSheet("background: none;")
        #         self.currency = ''
        #     else:
        #         self.label_rub.setStyleSheet("background:#73dc98; border-radius:30px;")
        #         self.currency = 'RUB'
        if event.type() == QEvent.MouseButtonPress and source is self.label_dollar:
            if self.label_dollar.styleSheet() == "background:#73dc98; border-radius:32px;":
                self.label_dollar.setStyleSheet("background: none;")
                self.currency = ''
            else:
                self.label_dollar.setStyleSheet("background:#73dc98; border-radius:32px;")
                self.currency = 'USD'

        return super(Form_Portfolio, self).eventFilter(source, event)

class Form_Calculate(QWidget):
    
    def __init__(self, sync_client, account_id, cost, parent=None):
        # For availability form
        super(Form_Calculate, self).__init__(parent)
        # Connecting qt
        self.cost = float(cost.replace("$", ""))
        uic.loadUi('ui/Calculate.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

        self.calculate(sync_client, account_id)

    def calculate(self, sync_client, account_id):
        # Определение коммисии
        if self.label_tariff.text() == 'Трейдер':
            self.commission = 0.0004
        else:
            self.commission = 0.003

        # Определение курса доллара
        self.curs_dollar = sync_client.get_market_orderbook(figi='BBG0013HGFT4', depth=1).payload.close_price
        self.label_curs.setText(str(self.curs_dollar)+' ₽')

        # Подсчёт налога на прибыль
        #TO DO: получить из базы ценны закупа, суммировать и найти разность 
        profit = float(form_main.labelTotalChange.text().replace('$',''))
        if profit > 0:
            tax = profit * 0.13
            self.label_tax.setText(str(tax)+' ₽')
        else:
            self.label_tax.setText('0')

        # Стоимость продажи
        total_cost = round((float(self.cost) - (float(self.cost) * self.commission) - float(self.label_tax.text())) * (float(self.curs_dollar)-(float(self.curs_dollar)*self.commission)), 2)
        self.label_total_cost.setText(str(total_cost)+' ₽')

        # Cумма всех вычетов
        self.label_minus.setText(str(round(float(self.cost)* float(self.curs_dollar) -  total_cost, 2))+' ₽')

class Form_Analysis(QWidget):
    
    def __init__(self, sync_client, account_id, current_cost_portfolio, parent=None):
        # For availability form
        super(Form_Analysis, self).__init__(parent)
        # Connecting qt
        uic.loadUi('ui/Analysis.ui', self)
        self.account_id = account_id
        self.current_cost_portfolio = float(current_cost_portfolio.replace("$", ""))
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

        # Ограничения на lineEdit
        self.lineEdit.setValidator(QRegExpValidator(QRegExp("\d+")))

        self.pushButton_analyse.clicked.connect(lambda: self.analysis())

    def analysis(self):
        if int(self.lineEdit.text()) >= 0 :
            stock, count = analyse_buy(int(self.lineEdit.text()), self.current_cost_portfolio, self.account_id)
            self.label_result.setText(stock + ' (' + str(count) + ' шт)')

class Form_Buy(QWidget):

    def __init__(self, sync_client, account_id, parent=None):
        # For availability form
        super(Form_Buy, self).__init__(parent)
        # Connecting qt
        self.sync_client = sync_client
        self.account_id = account_id
        uic.loadUi('ui/Buy.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

        # Заполнение списка акций
        cur = con.cursor()
        cur.execute("""select ticker from Tickers""")
        tickers = cur.fetchall()
        for ticker in tickers:
            self.comboBox.addItem(ticker[0])
        cur.close()
        # completers only work for editable combo boxes. QComboBox.NoInsert prevents insertion of the search text
        self.comboBox.setEditable(True)
        self.comboBox.setInsertPolicy(QComboBox.NoInsert)

        # change completion mode of the default completer from InlineCompletion to PopupCompletion
        self.comboBox.completer().setCompletionMode(QCompleter.PopupCompletion)
        # Для первой проверки
        self.change_stock()

        # Ограничения на lineEdit
        self.lineEdit_lot.setMaxLength(2)
        self.lineEdit_lot.setValidator(QRegExpValidator(QRegExp("\d+")))
        self.lineEdit_lot.textChanged.connect(lambda: self.change_lot())

        self.label_price.setText(str(round(pdr.get_quote_yahoo(self.comboBox.currentText())['price'][0], 2)))
        self.pushButton_buy.clicked.connect(lambda: self.buy_stock())
        self.pushButton_sell.clicked.connect(lambda: self.sell_stock())
        self.comboBox.currentIndexChanged.connect(lambda:self.change_stock())

    def change_lot(self):
        if self.lineEdit_lot.text() != '':
            current_price = pdr.get_quote_yahoo(self.comboBox.currentText())['price'][0]
            self.label_price.setText(str(round( current_price * int(self.lineEdit_lot.text()), 2)))

    def change_stock(self):
        current_price = pdr.get_quote_yahoo(self.comboBox.currentText())['price'][0]
        self.label_price.setText(str(round( current_price * int(self.lineEdit_lot.text()), 2)))
        # cur = con.cursor()
        # cur.execute("""select purchase_count from Purchase_prices
        # where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ? """,
        # (self.comboBox.currentText(), self.account_id))
        # if cur.fetchone() != None:
        #     self.pushButton_sell.setEnabled(True)
        #     self.pushButton_sell.setStyleSheet('background: red; color: white;')
        # else:
        #     self.pushButton_sell.setEnabled(False)
        #     self.pushButton_sell.setStyleSheet('background: none;')

    def buy_stock(self):
        # Исключения на лоты != 0
        if self.lineEdit_lot.text() == '' or int(self.lineEdit_lot.text()) <= 0:
            return
        # Исключения на кеш для покупки
        cur = con.cursor()
        cur.execute("""select currencies_count from Currencies_prices where id_currency = ? and number_account = ?""", (1, self.account_id))
        response = cur.fetchone()
        if response != None:
            currency_count =  response[0]
            if currency_count < float(self.label_price.text()):
                msg = QMessageBox(self)
                msg.setWindowTitle("Investor Assistant")
                msg.setText("Не достаточно средств на балансе счета (USD) для покупки актива.")
                msg.setIcon(QMessageBox.Warning)
                msg.exec_()
                return
        else:
            return 
        stock = self.sync_client.get_market_search_by_ticker(self.comboBox.currentText()).payload.instruments[0]
        lots = int(self.lineEdit_lot.text())
        ti.buy(figi=stock.figi, lots=lots, id_account=self.account_id)#(stock.figi)
        current_price = pdr.get_data_yahoo(stock.ticker, start=datetime.datetime.today() - datetime.timedelta(days=2), end=datetime.date.today())['Close'][-1]

        cur.execute("""select purchase_price, purchase_count from Purchase_prices
        where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", (stock.ticker, self.account_id))
        record = cur.fetchone()
        if record != None:
            cur.execute("""update Purchase_prices set purchase_price = ?, purchase_count = ?, purchase_date = ?
            where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", 
            ((record[0] + current_price)/2, record[1] + lots, datetime.datetime.now(), stock.ticker, self.account_id))
        else:
            cur.execute("""insert into Purchase_prices (id_ticker, number_account, purchase_date, purchase_price, purchase_count)
            values ((select id_ticker from Tickers where ticker = ?),?,?,?,?)""", (stock.ticker, self.account_id, datetime.datetime.now(), current_price, lots))
        con.commit()
        cur.close()

        # Вычет из стоимости портфеля реальную стоимость акции
        list_positions = self.sync_client.get_portfolio(broker_account_id=self.account_id).payload.positions
        for position in list_positions:
            if 'USD' in position.ticker:
                real_cost = float(position.balance) - lots * (current_price - 100)
                self.sync_client.set_sandbox_currencies_balance(
                    tinv.SandboxSetCurrencyBalanceRequest(balance=real_cost, currency=tinv.SandboxCurrency('USD')), self.account_id
                )
                break

        self.change_stock()
        # Обновление диаграмм
        form_main.build_diagram()
        form_main.get_portfolio()
    
    def sell_stock(self):
        if self.lineEdit_lot.text() == '' or int(self.lineEdit_lot.text()) <= 0:
            return
        # list_positions = self.sync_client.get_portfolio(broker_account_id=self.account_id).payload.positions
        # stock = list_positions[0]
        stock = self.sync_client.get_market_search_by_ticker(self.comboBox.currentText()).payload.instruments[0]
        lots = int(self.lineEdit_lot.text())
        # Удаление из бд
        cur = con.cursor()
        cur.execute("""select purchase_count, purchase_price from Purchase_prices 
        where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", (stock.ticker, self.account_id))
        record = cur.fetchone()
        current_count = record[0]
        current_price = record[1]
        if current_count < lots:
            msg = QMessageBox(self)
            msg.setWindowTitle("Investor Assistant")
            msg.setText("Невозможно продать акцию. Указанное количество акций меньше, чем в портфеле.")
            msg.setIcon(QMessageBox.Warning)
            msg.exec_()
            return
        elif current_count > lots:
            cur.execute("""update Purchase_prices set purchase_count = ?
            where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", (current_count-lots, stock.ticker, self.account_id))
        else:
            cur.execute("""delete from Purchase_prices 
            where id_ticker = (select id_ticker from Tickers where ticker = ?) and number_account = ?""", (stock.ticker, self.account_id))
        con.commit()
        cur.close()

        # Продажа акции
        ti.sell(figi=stock.figi, lots=lots , id_account=self.account_id)
        # Вычет из стоимости портфеля реальную стоимость акции
        list_positions = self.sync_client.get_portfolio(broker_account_id=self.account_id).payload.positions
        for position in list_positions:
            if 'USD' in position.ticker:
                real_cost = float(position.balance) + lots * (current_price - 100)
                self.sync_client.set_sandbox_currencies_balance(
                    tinv.SandboxSetCurrencyBalanceRequest(balance=real_cost, currency=tinv.SandboxCurrency('USD')), self.account_id
                )
                break

        self.change_stock()
        # Обновление диаграмм
        form_main.build_diagram()
        form_main.get_portfolio()

class Form_TopUp(QWidget):

    def __init__(self, sync_client, account_id, parent=None):
        # For availability form
        super(Form_TopUp, self).__init__(parent)
        # Connecting qt
        self.sync_client = sync_client
        self.account_id = account_id
        uic.loadUi('ui/TopUp.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

        # Заполнение списка валют
        cur = con.cursor()
        cur.execute("""select name_currency from Currencies""")
        currencies = cur.fetchall()
        for currency in currencies:
            self.comboBox.addItem(currency[0])
        cur.close()

        # Ограничения на lineEdit
        self.lineEdit.setValidator(QRegExpValidator(QRegExp("\d+")))

        self.comboBox.setEditable(True)
        self.comboBox.setInsertPolicy(QComboBox.NoInsert)
        self.comboBox.completer().setCompletionMode(QCompleter.PopupCompletion)
        # Для первой проверки
        self.change_currency()

        self.pushButton.clicked.connect(lambda: self.top_up())
        self.comboBox.currentIndexChanged.connect(lambda:self.change_currency())

    def change_currency(self):
        if self.comboBox.currentText() == 'RUB':
            self.label_price.setText(str(1))
        else:
            current_price = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()['Valute'][self.comboBox.currentText()]['Value']
            self.label_price.setText(str(round(current_price,2)))

    def top_up(self):
        #USD000UTSTOM figi='BBG0013HGFT4'
        #EUR_RUB__TOM figi='BBG0013HJJ31'
        name_currency = self.comboBox.currentText()
        # Исключение на название валюты 
        if name_currency != 'RUB' and name_currency != 'USD' and name_currency != 'EUR':
            return
        balance = int(self.lineEdit.text())
        current_price = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()['Valute'][name_currency]['Value']

        # Занесение в базу данных
        cur = con.cursor()
        cur.execute("""select currencies_price, currencies_count from Currencies_prices
        where id_currency = (select id_currency from Currencies where name_currency = ?) and number_account = ?""", (name_currency, self.account_id))
        record = cur.fetchone()

        if record != None:
            balance = record[1] + balance
            cur.execute("""update Currencies_prices set currencies_price = ?, currencies_count = ?, currencies_date = ?
            where id_currency = (select id_currency from Currencies where name_currency = ?) and number_account = ?""", 
            ((record[0] + current_price)/2, balance, datetime.datetime.now(), name_currency,  self.account_id))
        else:
            cur.execute("""insert into Currencies_prices (number_account, id_currency, currencies_date, currencies_count,currencies_price)
            values (?,(select id_currency from Currencies where name_currency = ?),?,?,?)  """,
            (self.account_id, name_currency, datetime.datetime.now(),balance, current_price))
        con.commit()
        cur.close()

        # Покупка в песочнице
        self.sync_client.set_sandbox_currencies_balance(
            tinv.SandboxSetCurrencyBalanceRequest(balance=balance, currency=tinv.SandboxCurrency(name_currency)), self.account_id
        )
        # self.sync_client.set_sandbox_currencies_balance(body_request, self.account_id)
        # Обновление диаграмм
        form_main.build_diagram()
        form_main.get_portfolio()

class Form_OwnPortfolio(QWidget):

    def __init__(self, sync_client, account_id, parent=None):
        # For availability form
        super(Form_OwnPortfolio, self).__init__(parent)
        # Connecting qt
        self.sync_client = sync_client
        self.account_id = account_id
        uic.loadUi('ui/OwnPortfolio.ui', self)
        self.setWindowTitle("Investor Assistant")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

        # Заполнение списка акций
        self.comboBox.clear()
        cur = con.cursor()
        cur.execute("""select ticker from Tickers""")
        tickers = cur.fetchall()
        for ticker in tickers:
            self.comboBox.addItem(ticker[0])
        cur.close()
        self.allItems = [self.comboBox.itemText(i) for i in range(self.comboBox.count())]

        self.comboBox.setEditable(True)
        self.comboBox.setInsertPolicy(QComboBox.NoInsert)
        self.comboBox.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.lineEdit.setMaxLength(2)
        self.lineEdit.setValidator(QRegExpValidator(QRegExp("\d+")))

        self.pushButton_add_currency.clicked.connect(lambda: self.add_active(False))
        self.pushButton_add_stock.clicked.connect(lambda: self.add_active(True))
        self.pushButton.clicked.connect(lambda: self.create_own_portfolio())

    def add_active(self, metka):
        comboBox = QComboBox()
        comboBox.setEditable(True)
        comboBox.setInsertPolicy(QComboBox.NoInsert)
        comboBox.setFont(QFont('Times New Roman', 10))
        comboBox.completer().setCompletionMode(QCompleter.PopupCompletion)
        # Заполнение списка
        cur = con.cursor()
        if metka:
            cur.execute("""select ticker from Tickers""")
            tickers = cur.fetchall()
            for ticker in tickers:
                comboBox.addItem(ticker[0])
        else:
            cur.execute("""select name_currency from Currencies""")
            currencies = cur.fetchall()
            for currency in currencies:
                comboBox.addItem(currency[0])
        cur.close()

        
        lineEdit = QLineEdit()
        lineEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lineEdit.setFont(QFont('Times New Roman', 10))
        lineEdit.setValidator(QRegExpValidator(QRegExp("\d+")))
        # Добавление на слой
        self.verticalLayout_active.addWidget(comboBox)
        self.verticalLayout_procent.addWidget(lineEdit)

    def create_own_portfolio(self):
        portfolio = {}
        stocks = []
        procent = []
        sum_procent = 0
        
        # Цикл по всем QLineEdit на lqyout
        widgets = (self.verticalLayout_procent.itemAt(i).widget() for i in range(self.verticalLayout_procent.count())) 
        for i, widget in enumerate(widgets):
            if isinstance(widget, QLineEdit) and widget.text() != '' :
                procent.append(widget.text())
                sum_procent += float(widget.text())
        
        # Исключения
        if sum_procent != 100:
            return
        


        # Цикл по всем QCombobox на lqyout
        widgets = (self.verticalLayout_active.itemAt(i).widget() for i in range(self.verticalLayout_active.count())) 
        for widget in widgets:
            if isinstance(widget, QComboBox):
                # Исключение на одинаковые акции
                if widget.currentText() in stocks or not widget.currentText() in self.allItems:
                    return
                stocks.append(widget.currentText())
            
        # Заполнение славоря
        for i, stock in enumerate(stocks):
            portfolio[stock] = float(procent[i])

        # Проверка на наличие уже созаднной структуры у данного аккаунта
            cur = con.cursor()
            cur.execute("""select * from portfolio where number_account =?""", (self.account_id,))
            # Удалить имеющуюся структуру и вставить новую
            if cur.fetchone() != None:
                cur.execute("""delete from Portfolio where number_account = ? """, (self.account_id,))
            for i, (key, value) in enumerate(portfolio.items()):
                if not key in ('USD', 'EUR','RUB'):
                    cur.execute("""insert into Portfolio (id_ticker, procent, number_account)
                    values ((select id_ticker from Tickers where ticker = ?), ?, ?)""", (key, value, self.account_id))
            con.commit()
            cur.close()

        # Заполнение формы
        form_main.filling_portfolio(portfolio)
        self.close()

class ProgressBar(QWidget):

    def __init__(self, parent=None):
        # For availability form
        super(ProgressBar, self).__init__(parent)
        uic.loadUi('ui/ProgressBar.ui', self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.mySignal = pyqtSignal(list)

    def run(self):
        for step in range(0, 101):
            self.mySignal.emit(['step', step])
            time.sleep(0.03)

if __name__ == "__main__":
    con = sqlite3.connect('db.db')
    app = QApplication(sys.argv)
    form_LogIn = Form_LogIn()
    form_LogIn.show()
    app.exec()