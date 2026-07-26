import sqlite3
from config import DATABASE_PATH

QUESTS = [
    # DAILY
    {"id": "daily_revenue", "title": "Giornata di Guadagni", "description": "Guadagna 500€ in un giorno", "type": "daily", "target": 500, "reward_xp": 20, "reward_money": 100},
    {"id": "daily_visit", "title": "Turista del Giorno", "description": "Visita 3 quartieri diversi", "type": "daily", "target": 3, "reward_xp": 15, "reward_money": 50},
    {"id": "daily_employee", "title": "Assunzione Rapida", "description": "Assumi 1 dipendente", "type": "daily", "target": 1, "reward_xp": 10, "reward_money": 75},
    {"id": "daily_upgrade", "title": "Miglioramento Quotidiano", "description": "Fai 1 upgrade", "type": "daily", "target": 1, "reward_xp": 15, "reward_money": 100},

    # WEEKLY
    {"id": "weekly_revenue", "title": "Settimana d'Oro", "description": "Guadagna 3000€ in una settimana", "type": "weekly", "target": 3000, "reward_xp": 100, "reward_money": 500},
    {"id": "weekly_business", "title": "Espansione", "description": "Apri 2 nuovi business", "type": "weekly", "target": 2, "reward_xp": 80, "reward_money": 300},
    {"id": "weekly_reviews", "title": "Reputazione", "description": "Ricevi 5 recensioni", "type": "weekly", "target": 5, "reward_xp": 60, "reward_money": 200},

    # STORY
    {"id": "story_caffe", "title": "Caffè degli Specchi", "description": "Apri un Caffè in Piazza Unità", "type": "story", "target": 1, "reward_xp": 50, "reward_money": 500},
    {"id": "story_barcolana", "title": "Barcolana", "description": "Apri un business a Barcola", "type": "story", "target": 1, "reward_xp": 40, "reward_money": 400},
    {"id": "story_ictp", "title": "ICTP Partnership", "description": "Apri un Tech Startup a Basovizza", "type": "story", "target": 1, "reward_xp": 60, "reward_money": 600},
    {"id": "story_muggia", "title": "Pescatore di Muggia", "description": "Apri un Ristorante a Muggia", "type": "story", "target": 1, "reward_xp": 45, "reward_money": 450},
    {"id": "story_bora", "title": "Sopravvissuto alla Bora", "description": "Sopravvivi all'inverno con profitto", "type": "story", "target": 1, "reward_xp": 70, "reward_money": 700},

    # ACHIEVEMENTS
    {"id": "ach_5biz", "title": "Impero Commerciale", "description": "Possiedi 5 business", "type": "achievement", "target": 5, "reward_xp": 200, "reward_money": 2000},
    {"id": "ach_level3", "title": "Manager Esperto", "description": "Raggiungi Livello 3", "type": "achievement", "target": 1, "reward_xp": 150, "reward_money": 1500},
    {"id": "ach_100k", "title": "Primo Milione", "description": "Guadagna 100,000€ totali", "type": "achievement", "target": 100000, "reward_xp": 500, "reward_money": 10000},
    {"id": "ach_loan", "title": "Banchiere", "description": "Paga 3 prestiti", "type": "achievement", "target": 3, "reward_xp": 100, "reward_money": 1000},
    {"id": "ach_reviews50", "title": "Amato dai Clienti", "description": "Ricevi 50 recensioni", "type": "achievement", "target": 50, "reward_xp": 250, "reward_money": 2500},

    # CHALLENGES
    {"id": "chal_profit", "title": "Profitto Estremo", "description": "Guadagna 10,000€ in un giorno", "type": "challenge", "target": 10000, "reward_xp": 300, "reward_money": 5000},
    {"id": "chal_districts", "title": "Conquistatore", "description": "Apri business in tutti i 9 quartieri", "type": "challenge", "target": 9, "reward_xp": 400, "reward_money": 8000},
]

def get_quest(quest_id):
    for q in QUESTS:
        if q["id"] == quest_id:
            return q
    return None

def get_quests_by_type(quest_type):
    return [q for q in QUESTS if q["type"] == quest_type]

def init_quests_table():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quest_id TEXT,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_quests_table()
    print(f"{len(QUESTS)} missioni caricate!")
