import json
from datetime import datetime
from config import SEASONAL_MULTIPLIERS

def get_current_season():
    month = datetime.now().month
    if month in [6, 7, 8]:
        return "estate"
    elif month in [12, 1, 2]:
        return "inverno"
    elif month in [3, 4, 5]:
        return "primavera"
    else:
        return "autunno"

def get_seasonal_multiplier():
    return SEASONAL_MULTIPLIERS.get(get_current_season(), 1.0)

# ===== EVENTI SPECIALI =====
SPECIAL_EVENTS = {
    "barcolana": {
        "name": "⛵ Barcolana",
        "description": "La regata più affollata del Mediterraneo! Traffico ×3 a Barcola.",
        "month": 10,
        "day_range": [1, 15],
        "multiplier": 2.5,
        "affected_districts": ["Barcola"],
        "affected_categories": ["food", "industry"],
        "duration_hours": 72
    },
    "bora": {
        "name": "❄️ Bora Extrema",
        "description": "La Bora soffia a 150km/h! Traffico ridotto del 60% in tutta la città.",
        "month": 1,
        "day_range": [1, 31],
        "multiplier": 0.4,
        "affected_districts": [],  # Tutti
        "affected_categories": [],  # Tutti
        "duration_hours": 48
    },
    "fiori": {
        "name": "🌸 Fiera dei Fiori",
        "description": "Colori e profumi invadono Trieste! Vendite +80% in centro.",
        "month": 4,
        "day_range": [15, 30],
        "multiplier": 1.8,
        "affected_districts": ["Piazza Unità d'Italia", "Viale XX Settembre"],
        "affected_categories": ["food", "tech"],
        "duration_hours": 120
    },
    "ictp_conf": {
        "name": "🔬 ICTP Conference",
        "description": "Conferenza internazionale a Basovizza! Tech +200%.",
        "month": 9,
        "day_range": [1, 30],
        "multiplier": 2.0,
        "affected_districts": ["Basovizza"],
        "affected_categories": ["tech"],
        "duration_hours": 96
    },
    "natale": {
        "name": "🎄 Mercatini di Natale",
        "description": "Luci e mercatini natalizi! Centro storico +100%.",
        "month": 12,
        "day_range": [8, 26],
        "multiplier": 1.5,
        "affected_districts": ["Piazza Unità d'Italia", "Città Vecchia", "San Giusto"],
        "affected_categories": ["food", "tech"],
        "duration_hours": 168
    },
    "carnevale": {
        "name": "🎭 Carnevale di Muggia",
        "description": "Maschere e feste a Muggia! Turismo +150%.",
        "month": 2,
        "day_range": [1, 28],
        "multiplier": 2.0,
        "affected_districts": ["Muggia"],
        "affected_categories": ["food", "industry"],
        "duration_hours": 72
    },
    "festa_unita": {
        "name": "🇮🇹 Festa dell'Unità",
        "description": "Celebrazioni in Piazza Unità! Eventi e vendite +120%.",
        "month": 3,
        "day_range": [15, 20],
        "multiplier": 2.2,
        "affected_districts": ["Piazza Unità d'Italia"],
        "affected_categories": [],
        "duration_hours": 48
    }
}

def check_active_events():
    """Controlla quali eventi speciali dovrebbero essere attivi oggi."""
    now = datetime.now()
    active = []
    for event_id, event in SPECIAL_EVENTS.items():
        if now.month == event["month"]:
            if event["day_range"][0] <= now.day <= event["day_range"][1]:
                active.append({"id": event_id, **event})
    return active

def get_event_multiplier_for_business(business_type, district, active_events):
    """Calcola il moltiplicatore evento per un specifico business."""
    btype_category = {
        "Caffè Storico": "food", "Ristorante": "food", "Gelateria Artigianale": "food",
        "Hotel Boutique": "food", "Libreria Indipendente": "tech",
        "Tech Startup": "tech", "Hub Logistico": "industry",
        "Compagnia di Navigazione": "industry"
    }
    category = btype_category.get(business_type, "")

    total_mult = 1.0
    for event in active_events:
        mult = event["multiplier"]
        districts_ok = not event["affected_districts"] or district in event["affected_districts"]
        cats_ok = not event["affected_categories"] or category in event["affected_categories"]
        if districts_ok and cats_ok:
            total_mult *= mult
    return total_mult

def calculate_revenue(business_type, district, business_level, employees, upgrades, active_events=None):
    base_revenue = {
        "Caffè Storico": 80, "Ristorante": 120, "Hub Logistico": 150,
        "Tech Startup": 200, "Compagnia di Navigazione": 180,
        "Hotel Boutique": 160, "Gelateria Artigianale": 70, "Libreria Indipendente": 50
    }
    district_multiplier = {
        "Piazza Unità d'Italia": 2.5, "Porto Vecchio": 2.0, "Viale XX Settembre": 1.8,
        "Città Vecchia": 1.2, "San Giusto": 1.5, "Barcola": 1.6,
        "Opicina": 0.8, "Basovizza": 1.0, "Muggia": 1.1
    }
    base = base_revenue.get(business_type, 50)
    dist_mult = district_multiplier.get(district, 1.0)
    level_bonus = 1 + (business_level - 1) * 0.15
    employee_bonus = 1 + employees * 0.05
    upgrade_bonus = 1 + len(upgrades) * 0.08
    season_mult = get_seasonal_multiplier()
    event_mult = get_event_multiplier_for_business(business_type, district, active_events or [])

    revenue = base * dist_mult * level_bonus * employee_bonus * upgrade_bonus * season_mult * event_mult
    return round(revenue, 2)

def calculate_expenses(business_type, employees):
    base_expenses = {
        "Caffè Storico": 30, "Ristorante": 50, "Hub Logistico": 60,
        "Tech Startup": 40, "Compagnia di Navigazione": 70,
        "Hotel Boutique": 55, "Gelateria Artigianale": 25, "Libreria Indipendente": 20
    }
    base = base_expenses.get(business_type, 30)
    employee_cost = employees * 15
    return round(base + employee_cost, 2)

def get_level_title(level):
    titles = {
        1: "Imprenditore Esordiente", 2: "Commerciante Locale",
        3: "Manager Esperto", 4: "Imprenditore Affermato",
        5: "Magnate di Trieste", 6: "Barone del Carso",
        7: "Duca del Porto", 8: "Principe della Bora",
        9: "Re di Trieste", 10: "Leggenda dell'Adriatico"
    }
    return titles.get(level, "Leggenda Eterna")

def get_upgrade_cost(upgrade_type):
    costs = {
        "Potenzia Struttura": 500, "Equipaggiamento": 800,
        "WiFi Premium": 600, "Dehors Esterno": 1200,
        "Assumi Dipendente": 300, "Forma Staff": 200
    }
    return costs.get(upgrade_type, 500)

def get_upgrade_effect(upgrade_type):
    effects = {
        "Potenzia Struttura": "+15% ricavi", "Equipaggiamento": "+8% efficienza",
        "WiFi Premium": "+5% soddisfazione clienti", "Dehors Esterno": "+10% ricavi estate",
        "Assumi Dipendente": "+5% produttività", "Forma Staff": "+10% produttività"
    }
    return effects.get(upgrade_type, "Miglioramento generico")
