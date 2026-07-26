from database import Database
from quest_database import QUESTS, get_quest
from datetime import datetime, timedelta

class QuestManager:
    def __init__(self):
        self.db = Database()

    def get_user_quests(self, user_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quests WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def start_quest(self, user_id, quest_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        if cursor.fetchone():
            conn.close()
            return False, "Missione già iniziata!"
        cursor.execute("INSERT INTO user_quests (user_id, quest_id) VALUES (?, ?)", (user_id, quest_id))
        conn.commit()
        conn.close()
        return True, "Missione iniziata!"

    def update_progress(self, user_id, quest_id, amount=1):
        quest = get_quest(quest_id)
        if not quest:
            return False
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        if row["completed"]:
            conn.close()
            return False
        new_progress = row["progress"] + amount
        completed = 1 if new_progress >= quest["target"] else 0
        cursor.execute("""
            UPDATE user_quests SET progress = ?, completed = ?
            WHERE user_id = ? AND quest_id = ?
        """, (new_progress, completed, user_id, quest_id))
        conn.commit()
        conn.close()
        return completed == 1

    def claim_reward(self, user_id, quest_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        row = cursor.fetchone()
        if not row or not row["completed"] or row["claimed"]:
            conn.close()
            return False, "Non puoi riscattare questa ricompensa!"
        quest = get_quest(quest_id)
        cursor.execute("UPDATE user_quests SET claimed = 1 WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        cursor.execute("UPDATE users SET balance = balance + ?, xp = xp + ? WHERE user_id = ?",
                       (quest["reward_money"], quest["reward_xp"], user_id))
        conn.commit()
        conn.close()
        return True, f"Ricompensa riscattata! +{quest['reward_money']}€, +{quest['reward_xp']} XP"

    def auto_assign_daily(self, user_id):
        from quest_database import get_quests_by_type
        daily = get_quests_by_type("daily")
        for q in daily:
            self.start_quest(user_id, q["id"])
        return len(daily)

    def check_and_update(self, user_id, event_type, value=1):
        """event_type: 'revenue', 'business_created', 'employee_hired', 'upgrade', 'review', 'loan_paid', 'district_visited'"""
        mapping = {
            "revenue": ["daily_revenue", "weekly_revenue", "ach_100k", "chal_profit"],
            "business_created": ["weekly_business", "ach_5biz", "chal_districts"],
            "employee_hired": ["daily_employee"],
            "upgrade": ["daily_upgrade"],
            "review": ["weekly_reviews", "ach_reviews50"],
            "loan_paid": ["ach_loan"],
            "district_visited": ["daily_visit"]
        }
        quests = mapping.get(event_type, [])
        completed = []
        for qid in quests:
            if self.update_progress(user_id, qid, value):
                completed.append(qid)
        return completed
