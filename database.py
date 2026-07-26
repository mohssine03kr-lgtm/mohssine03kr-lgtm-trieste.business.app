import sqlite3
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH, STARTING_BALANCE

class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Utenti
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 5000.0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                total_earned REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                businesses_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily TIMESTAMP
            )
        """)

        # Business
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                type TEXT,
                district TEXT,
                level INTEGER DEFAULT 1,
                revenue REAL DEFAULT 0,
                expenses REAL DEFAULT 0,
                employees INTEGER DEFAULT 0,
                upgrades TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Prestiti
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                interest_rate REAL DEFAULT 0.05,
                months INTEGER,
                remaining REAL,
                monthly_payment REAL,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Missioni utente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quest_id TEXT,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                claimed INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Recensioni
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                customer_name TEXT,
                rating INTEGER,
                comment TEXT,
                sentiment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id)
            )
        """)

        # Notifiche
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Eventi speciali attivi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                event_name TEXT,
                description TEXT,
                multiplier REAL DEFAULT 1.0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ends_at TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        """)

        # Storico eventi per utente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id TEXT,
                participated INTEGER DEFAULT 0,
                reward_claimed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Leaderboard
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                score INTEGER DEFAULT 0,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leaderboard_user_category 
            ON leaderboard(user_id, category)
        """)

        conn.commit()
        conn.close()

    def get_or_create_user(self, user_id, username=None, first_name=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
        conn.close()
        return dict(user)

    def update_balance(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        if amount > 0:
            cursor.execute("UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?", (amount, user_id))
        else:
            cursor.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (abs(amount), user_id))
        conn.commit()
        conn.close()

    def add_xp(self, user_id, xp):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp, user_id))
        cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        xp_total, level = row["xp"], row["level"]
        level_thresholds = {1: 0, 2: 50, 3: 200, 4: 500, 5: 1000, 6: 2500, 7: 5000, 8: 10000, 9: 20000, 10: 50000}
        new_level = level
        for lvl, threshold in sorted(level_thresholds.items()):
            if xp_total >= threshold:
                new_level = lvl
        if new_level > level:
            cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, user_id))
        conn.commit()
        conn.close()
        return new_level > level, new_level

    def update_businesses_count(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM businesses WHERE user_id = ?", (user_id,))
        cnt = cursor.fetchone()["cnt"]
        cursor.execute("UPDATE users SET businesses_count = ? WHERE user_id = ?", (cnt, user_id))
        conn.commit()
        conn.close()

    def get_user_businesses(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_business(self, user_id, name, btype, district):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO businesses (user_id, name, type, district)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, btype, district))
        business_id = cursor.lastrowid
        conn.commit()
        conn.close()
        self.update_businesses_count(user_id)
        return business_id

    def upgrade_business(self, business_id, upgrade_type, cost):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT upgrades FROM businesses WHERE id = ?", (business_id,))
        row = cursor.fetchone()
        upgrades = json.loads(row["upgrades"])
        upgrades.append(upgrade_type)
        cursor.execute("UPDATE businesses SET upgrades = ? WHERE id = ?", (json.dumps(upgrades), business_id))
        conn.commit()
        conn.close()

    def add_review(self, business_id, customer_name, rating, comment, sentiment):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (business_id, customer_name, rating, comment, sentiment)
            VALUES (?, ?, ?, ?, ?)
        """, (business_id, customer_name, rating, comment, sentiment))
        conn.commit()
        conn.close()

    def get_reviews(self, business_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews WHERE business_id = ? ORDER BY created_at DESC", (business_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_loan(self, user_id, amount, months):
        conn = self.get_connection()
        cursor = conn.cursor()
        interest = amount * 0.05 * (months / 12)
        total = amount + interest
        monthly = total / months
        cursor.execute("""
            INSERT INTO loans (user_id, amount, months, remaining, monthly_payment)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, months, total, monthly))
        conn.commit()
        conn.close()
        return total, monthly

    def get_loans(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM loans WHERE user_id = ? AND remaining > 0", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_notification(self, user_id, message):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))
        conn.commit()
        conn.close()

    def get_notifications(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_active_event(self, event_id, event_name, description, multiplier, duration_hours=24):
        conn = self.get_connection()
        cursor = conn.cursor()
        ends = datetime.now() + timedelta(hours=duration_hours)
        cursor.execute("""
            INSERT INTO active_events (event_id, event_name, description, multiplier, ends_at)
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, event_name, description, multiplier, ends))
        conn.commit()
        conn.close()

    def get_active_events(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM active_events 
            WHERE active = 1 AND ends_at > ?
            ORDER BY started_at DESC
        """, (datetime.now(),))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def deactivate_expired_events(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE active_events SET active = 0 
            WHERE ends_at < ? AND active = 1
        """, (datetime.now(),))
        conn.commit()
        conn.close()

    def update_leaderboard(self, user_id, username, score, category='general'):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leaderboard (user_id, username, score, category, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET
                score = excluded.score,
                username = excluded.username,
                updated_at = excluded.updated_at
        """, (user_id, username, score, category, datetime.now()))
        conn.commit()
        conn.close()

    def get_leaderboard(self, category='general', limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, score, updated_at 
            FROM leaderboard 
            WHERE category = ?
            ORDER BY score DESC
            LIMIT ?
        """, (category, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_stats(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) as cnt FROM businesses WHERE user_id = ?", (user_id,))
        biz_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM reviews r JOIN businesses b ON r.business_id = b.id WHERE b.user_id = ?", (user_id,))
        review_count = cursor.fetchone()["cnt"]
        conn.close()
        if user:
            u = dict(user)
            u["businesses_count"] = biz_count
            u["reviews_count"] = review_count
            return u
        return None

if __name__ == "__main__":
    db = Database()
    print("Database inizializzato con successo!")
