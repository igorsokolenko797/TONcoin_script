import sqlite3
import logging

class Database:
    def __init__(self, db_path: str = 'bot.db'):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0
                )
            ''')
            # Таблица транзакций для отслеживания депозитов (чтобы избежать двойного зачисления)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_hash TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            conn.commit()

    def get_user_balance(self, user_id: int) -> float:
        # Возвращает баланс пользователя, создает запись, если пользователя нет
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0.0

    def update_user_balance(self, user_id: int, amount: float):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()

    def add_transaction(self, tx_hash: str, user_id: int, amount: float, status: str = "pending"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO transactions (tx_hash, user_id, amount, status)
                VALUES (?, ?, ?, ?)
            ''', (tx_hash, user_id, amount, status))
            conn.commit()

    def is_transaction_processed(self, tx_hash: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM transactions WHERE tx_hash = ?', (tx_hash,))
            return cursor.fetchone() is not None
