import os
from tonclient.client import TonClient
from tonclient.types import ClientConfig, KeyPair, Address, ParamsOfParse, ParamsOfEncodeMessage, ParamsOfQueryCollection, ParamsOfWaitForCollection
import asyncio

# Конфигурация (лучше вынести в .env)
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY")  # Получите на https://toncenter.com
NETWORK = "mainnet"  # или "testnet"

class TONClient:
    def __init__(self):
        self.client = TonClient(ClientConfig(
            network=NETWORK,
            api_key=TONCENTER_API_KEY
        ))

    async def generate_deposit_address(self, user_id: int):
        # Генерируем уникальный адрес кошелька для депозита.
        # На практике это может быть один кошелек бота, а user_id используется в комментарии (payload) транзакции.
        # Но для лучшего отслеживания можно генерировать отдельные адреса.
        # Здесь для простоты вернем один статический адрес бота.
        # В реальном проекте рассмотрите использование Wallets с разными сериями.
        BOT_WALLET_ADDRESS = "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM9"  # Замените на адрес вашего кошелька бота
        return BOT_WALLET_ADDRESS

    async def check_transactions(self, address: str):
        # Проверяем входящие транзакции для адреса
        query = """
            query MyQuery {
                blockchain {
                    account(address: "%s") {
                        messages(msg_type: ExtIn) {
                            created_lt
                            value
                            src
                            hash
                        }
                    }
                }
            }
        """ % address
        # Это упрощенный пример. В реальности нужно использовать GraphQL или методы toncenter.
        # Вместо этого мы будем использовать get_transactions из toncenter-python

    async def get_transactions(self, address: str, limit: int = 10):
        # Более реалистичный метод через toncenter API
        # Используем прямой HTTP запрос, так как toncenter-python может не иметь готового метода
        import aiohttp
        url = f"https://toncenter.com/api/v2/getTransactions?address={address}&limit={limit}"
        headers = {"X-API-Key": TONCENTER_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data.get("result", [])

    async def send_ton(self, from_seed: str, to_address: str, amount: float, comment: str = ""):
        # Отправка TON. from_seed - seed фраза кошелька бота.
        # ВАЖНО: Безопасно храните seed фразу!
        # Это сложная операция, требующая подписи транзакции.
        # Для продакшена используйте надежный кошелек или кастодиальное решение.
        # Это примерная структура.
        key_pair = KeyPair.from_seed(from_seed)
        message = await self.client.abi.encode_message(
            ParamsOfEncodeMessage(
                address=Address(from_address),
                abi={...},  # ABI кошелька
                call_set={...},  # Данные для вызова
                signer=key_pair
            )
        )
        # ... Дальнейшая логика отправки
        pass

# Упрощенный клиент для проверки транзакций
class SimpleTONClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://toncenter.com/api/v2"

    async def get_transactions(self, address: str, limit: int = 20):
        import aiohttp
        url = f"{self.base_url}/getTransactions?address={address}&limit={limit}"
        headers = {"X-API-Key": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data.get("result", [])
