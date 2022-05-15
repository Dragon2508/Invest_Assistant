from urllib import response
from requests import request
import tinvest as tinv

class Sandbox_Ti:

    def __init__(self, token, use_sandbox = True):
        self._use_sandbox = use_sandbox
        self._key = token
        self.sync_client = None

    def get_sync_client(self):
        #Создаю клиента для rest запросов к Open API Тинькофф Инвестиций
        if not self.sync_client:
            self.sync_client = tinv.SyncClient(self._key, use_sandbox=self._use_sandbox)
            # print(self.sync_client.get_accounts().payload.accounts)
            # self.sync_client = tinv.SyncClient(self._key)
        return self.sync_client

    def create_sandbox(self, account_type):

        # проверка на работу в песочнице
        if not self._use_sandbox:
            return

        # получаю список аккаунтов (в песочнице только 1 акк)
        # accounts = self.get_sync_client().get_accounts().payload.accounts[0].broker_account_id

        # если аккаунт в песочнице уже создан, то удлаяю его (хотя есть и методы очистки)
        # if len(accounts) > 0:
        #     self.get_sync_client().remove_sandbox_account(accounts[0].broker_account_id)

        # создаю аккаунт в песочнице и получаю его номер
        if account_type == 'ИИС':
            type_account = tinv.BrokerAccountType.tinkoff_iis
        else:
            type_account = tinv.BrokerAccountType.tinkoff
        broker_account_id = self.get_sync_client().register_sandbox_account(
            tinv.SandboxRegisterRequest(broker_account_type=type_account) #tinkof_iis
        ).payload.broker_account_id

        return broker_account_id, type_account

    def delete_sandbox(self, account_id):
        # получаю список аккаунтов (в песочнице только 1 акк)
        # accounts = self.get_sync_client().get_accounts().payload.accounts
        self.get_sync_client().remove_sandbox_account(account_id)

    def clear_sandbox(self, id_account):
        # проверка на работу в песочнице
        self.get_sync_client().clear_sandbox_account(id_account)

    def buy(self, figi, lots, id_account):
        request = tinv.MarketOrderRequest(lots=lots, operation=tinv.OperationType.buy)
        response = self.get_sync_client().post_orders_market_order(figi, request, broker_account_id=id_account)
        return response
    
    def sell(self, figi, lots, id_account):
        request = tinv.MarketOrderRequest(lots=lots, operation=tinv.OperationType.sell)
        response = self.get_sync_client().post_orders_market_order(figi, request, broker_account_id=id_account)
        return response

    # Получение списков акций, фондов, etf
    def get_list_stocks(self):
        list_stocks = [i for i in self.get_sync_client().get_market_stocks().payload.instruments]
        return list_stocks

    def get_list_bonds(self):
        return self.get_sync_client().get_market_bonds().payload.instruments

    def get_list_etf(self):
        return self.get_sync_client().get_market_etfs().payload.instruments
