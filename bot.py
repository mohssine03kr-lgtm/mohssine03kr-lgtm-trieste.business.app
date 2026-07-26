import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

from config import BOT_TOKEN, WEBAPP_URL
from database import Database
from game_logic import (
    calculate_revenue, calculate_expenses, get_level_title,
    get_current_season, get_seasonal_multiplier, get_upgrade_cost, get_upgrade_effect,
    check_active_events, SPECIAL_EVENTS
)
from quest_database import QUESTS, get_quest, get_quests_by_type
from quest_integration import QuestManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
qm = QuestManager()

# ========== COMANDI ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    qm.auto_assign_daily(user.id)

    # Check eventi attivi
    events = check_active_events()
    event_text = ""
    if events:
        event_text = "\n\n🎉 **Eventi Speciali Attivi:**\n"
        for e in events:
            event_text += f"• {e['name']}: {e['description']}\n"

    keyboard = [
        [InlineKeyboardButton("🗺️ Apri Mappa", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("💰 Bilancio", callback_data="balance"),
         InlineKeyboardButton("🏢 Negozi", callback_data="businesses")],
        [InlineKeyboardButton("🎯 Missioni", callback_data="quests"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏆 Classifica", callback_data="leaderboard"),
         InlineKeyboardButton("🎉 Eventi", callback_data="events")],
        [InlineKeyboardButton("💳 Prestito", callback_data="loan"),
         InlineKeyboardButton("❓ Aiuto", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎮 **Benvenuto in Trieste Business Tycoon!** 🏙️\n\n"
        f"Ciao {user.first_name}! Sei pronto a diventare il magnate di Trieste?\n\n"
        f"🗺️ Esplora i 9 quartieri reali della città\n"
        f"🏢 Apri e gestisci la tua attività commerciale\n"
        f"🎯 Completa missioni e guadagna ricompense\n"
        f"🎉 Partecipa a eventi speciali stagionali\n"
        f"⬆️ Sali di livello e sblocca nuovi quartieri!\n\n"
        f"🌤️ Stagione: **{get_current_season().capitalize()}** (×{get_seasonal_multiplier()})"
        f"{event_text}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_or_create_user(user.id)
    businesses = db.get_user_businesses(user.id)
    events = check_active_events()

    total_revenue = sum(calculate_revenue(b["type"], b["district"], b["level"], b["employees"], json.loads(b["upgrades"]), events) for b in businesses)
    total_expenses = sum(calculate_expenses(b["type"], b["employees"]) for b in businesses)
    profit = total_revenue - total_expenses

    text = (f"💰 **Bilancio di {u.get('first_name') or 'Giocatore'}**\n\n"
            f"💵 Saldo: **{u['balance']:.2f}€**\n"
            f"⭐ XP: **{u['xp']}** | Livello: **{u['level']}** ({get_level_title(u['level'])})\n"
            f"🏢 Negozi: **{len(businesses)}**\n"
            f"💰 Totale Guadagnato: {u.get('total_earned', 0):.0f}€\n"
            f"💸 Totale Speso: {u.get('total_spent', 0):.0f}€\n\n"
            f"📊 **Entrate giornaliere:**\n"
            f"💶 Ricavi: +{total_revenue:.2f}€\n"
            f"💸 Spese: -{total_expenses:.2f}€\n"
            f"📈 Profitto: {'+' if profit >= 0 else ''}{profit:.2f}€")

    if events:
        text += "\n\n🎉 **Eventi attivi:**\n"
        for e in events:
            text += f"• {e['name']} (×{e['multiplier']})\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def businesses_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    businesses = db.get_user_businesses(user.id)
    events = check_active_events()

    if not businesses:
        await update.message.reply_text("🏢 Non hai ancora nessun business! Apri la mappa per acquistarne uno.")
        return

    text = "🏢 **I tuoi Negozi:**\n\n"
    for b in businesses:
        rev = calculate_revenue(b["type"], b["district"], b["level"], b["employees"], json.loads(b["upgrades"]), events)
        exp = calculate_expenses(b["type"], b["employees"])
        upgrades = json.loads(b["upgrades"])
        text += (f"📍 **{b['name']}** ({b['type']}) - {b['district']}\n"
                 f"   Livello: {b['level']} | Dipendenti: {b['employees']} | Upgrades: {len(upgrades)}\n"
                 f"   💶 +{rev:.0f}€ / 💸 -{exp:.0f}€ = 📈 +{rev-exp:.0f}€/giorno\n\n")

    await update.message.reply_text(text, parse_mode="Markdown")

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_or_create_user(user.id)

    if u.get("last_daily"):
        last = datetime.fromisoformat(u["last_daily"])
        if (datetime.now() - last).total_seconds() < 86400:
            remaining = 86400 - (datetime.now() - last).total_seconds()
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            await update.message.reply_text(f"⏰ Ricompensa giornaliera già riscattata! Torna tra {hours}h {mins}m.")
            return

    daily_reward = 200 + (u["level"] * 50)
    db.update_balance(user.id, daily_reward)
    leveled_up, new_level = db.add_xp(user.id, 10)

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()

    text = f"🎁 **Ricompensa Giornaliera!**\n\n💵 +{daily_reward}€\n⭐ +10 XP"
    if leveled_up:
        text += f"\n\n🎉 **LEVEL UP!** Sei ora Livello {new_level} - {get_level_title(new_level)}!"
    text += "\n\nTorna domani per altri premi!"

    await update.message.reply_text(text, parse_mode="Markdown")

async def quests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_quests = qm.get_user_quests(user.id)

    if not user_quests:
        qm.auto_assign_daily(user.id)
        user_quests = qm.get_user_quests(user.id)

    text = "🎯 **Le tue Missioni:**\n\n"
    for uq in user_quests:
        quest = get_quest(uq["quest_id"])
        if not quest:
            continue
        status = "✅" if uq["claimed"] else ("🎁" if uq["completed"] else "⏳")
        text += f"{status} **{quest['title']}** ({quest['type']})\n"
        text += f"   {quest['description']}\n"
        text += f"   Progresso: {uq['progress']}/{quest['target']} | 🎁 {quest['reward_money']}€ + {quest['reward_xp']} XP\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Uso: /claim <quest_id>")
        return

    quest_id = context.args[0]
    success, msg = qm.claim_reward(user.id, quest_id)
    if success:
        db.add_xp(user.id, 0)  # trigger level check
    await update.message.reply_text(msg)

async def loan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        text = ("💳 **Sistema Prestiti**\n\n"
                "Tasso d'interesse: **5% annuo**\n"
                "Durata massima: **12 mesi**\n\n"
                "Uso: `/loan <importo> <mesi>`\n"
                "Esempio: `/loan 5000 6`")
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    try:
        amount = float(context.args[0])
        months = int(context.args[1])
        if months < 1 or months > 12:
            raise ValueError
        if amount < 100:
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Parametri non validi. Usa: /loan <importo> <mesi> (max 12 mesi, min 100€)")
        return

    total, monthly = db.add_loan(user.id, amount, months)
    db.update_balance(user.id, amount)

    text = (f"💳 **Prestito Approvato!**\n\n"
            f"Importo: {amount:.2f}€\n"
            f"Interessi: {total - amount:.2f}€\n"
            f"Totale da ripagare: {total:.2f}€\n"
            f"Rata mensile: {monthly:.2f}€\n"
            f"Durata: {months} mesi")
    await update.message.reply_text(text, parse_mode="Markdown")

async def notifications_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    notifs = db.get_notifications(user.id)

    if not notifs:
        await update.message.reply_text("📭 Nessuna notifica.")
        return

    text = "📢 **Notifiche:**\n\n"
    for n in notifs:
        status = "🔴" if not n["read"] else "⚪"
        text += f"{status} {n['message']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# ===== NUOVI COMANDI: STATS, LEADERBOARD, EVENTI =====

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = db.get_user_stats(user.id)
    if not stats:
        await update.message.reply_text("❌ Utente non trovato.")
        return

    businesses = db.get_user_businesses(user.id)
    events = check_active_events()
    total_rev = sum(calculate_revenue(b["type"], b["district"], b["level"], b["employees"], json.loads(b["upgrades"]), events) for b in businesses)
    total_exp = sum(calculate_expenses(b["type"], b["employees"]) for b in businesses)

    text = (f"📊 **Statistiche di {stats.get('first_name') or stats.get('username') or 'Giocatore'}**\n\n"
            f"🏆 Livello: **{stats['level']}** - {get_level_title(stats['level'])}\n"
            f"⭐ XP: **{stats['xp']}** / prossimo livello\n"
            f"💰 Saldo: **{stats['balance']:.0f}€**\n"
            f"📈 Totale Guadagnato: **{stats.get('total_earned', 0):.0f}€**\n"
            f"💸 Totale Speso: **{stats.get('total_spent', 0):.0f}€**\n"
            f"🏢 Negozi: **{stats.get('businesses_count', 0)}**\n"
            f"⭐ Recensioni Ricevute: **{stats.get('reviews_count', 0)}**\n"
            f"📅 Registrato dal: {stats['created_at'][:10]}\n\n"
            f"📊 **Profitto Giornaliero:** +{total_rev - total_exp:.0f}€\n"
            f"🌤️ Stagione: {get_current_season().capitalize()} (×{get_seasonal_multiplier()})")

    await update.message.reply_text(text, parse_mode="Markdown")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Aggiorna leaderboard prima di mostrarla
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, xp, balance FROM users")
    users = cursor.fetchall()
    conn.close()

    for u in users:
        score = int(u["xp"] + u["balance"] * 0.1)
        name = u["first_name"] or u["username"] or "Giocatore"
        db.update_leaderboard(u["user_id"], name, score, "general")

    board = db.get_leaderboard("general", 10)

    text = "🏆 **Classifica Globale - Top 10**\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, entry in enumerate(board):
        medal = medals[i] if i < 10 else f"{i+1}."
        text += f"{medal} **{entry['username']}** - {entry['score']} punti\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def events_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = check_active_events()
    db.deactivate_expired_events()
    active_db = db.get_active_events()

    if not events and not active_db:
        # Mostra prossimi eventi
        now = datetime.now()
        upcoming = []
        for eid, e in SPECIAL_EVENTS.items():
            if e["month"] >= now.month:
                upcoming.append((eid, e))

        text = "📅 **Prossimi Eventi Speciali:**\n\n"
        for eid, e in upcoming[:5]:
            text += f"🗓️ **{e['name']}** (mese {e['month']})\n{e['description']}\n\n"
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    text = "🎉 **Eventi Speciali Attivi:**\n\n"
    for e in events:
        text += (f"{e['name']}\n"
                 f"📍 {e['description']}\n"
                 f"💰 Moltiplicatore: ×{e['multiplier']}\n"
                 f"⏱️ Durata: {e['duration_hours']}h\n\n")

    for e in active_db:
        text += (f"📢 {e['event_name']}\n"
                 f"⏳ Scade: {e['ends_at'][:16]}\n\n")

    await update.message.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("🎮 **Trieste Business Tycoon - Guida**\n\n"
            "📍 **Comandi:**\n"
            "/start - Menu principale\n"
            "/balance - Bilancio e statistiche\n"
            "/businesses - I tuoi negozi\n"
            "/daily - Ricompensa giornaliera\n"
            "/quests - Missioni attive\n"
            "/claim <id> - Riscatta ricompensa\n"
            "/loan <importo> <mesi> - Richiedi prestito\n"
            "/stats - Statistiche dettagliate\n"
            "/leaderboard - Classifica globale\n"
            "/events - Eventi speciali\n"
            "/notifications - Notifiche\n"
            "/help - Questa guida\n\n"
            "🗺️ Apri la WebApp dalla tastiera per gestire la mappa interattiva!")
    await update.message.reply_text(text, parse_mode="Markdown")

# ========== CALLBACKS ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == "balance":
        await balance_cmd(update, context)
    elif data == "businesses":
        await businesses_cmd(update, context)
    elif data == "quests":
        await quests_cmd(update, context)
    elif data == "stats":
        await stats_cmd(update, context)
    elif data == "leaderboard":
        await leaderboard_cmd(update, context)
    elif data == "events":
        await events_cmd(update, context)
    elif data == "notifications":
        await notifications_cmd(update, context)
    elif data == "loan":
        await loan_cmd(update, context)
    elif data == "help":
        await help_cmd(update, context)

# ========== JOB: CHECK EVENTS ==========

async def check_events_job(context: ContextTypes.DEFAULT_TYPE):
    """Job che controlla e attiva eventi speciali."""
    events = check_active_events()
    db.deactivate_expired_events()

    for event in events:
        # Controlla se già attivo nel DB
        active = db.get_active_events()
        active_ids = [e["event_id"] for e in active]
        if event["id"] not in active_ids:
            db.add_active_event(
                event["id"], event["name"],
                event["description"], event["multiplier"],
                event["duration_hours"]
            )
            # Notifica tutti gli utenti
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            conn.close()
            for u in users:
                db.add_notification(u["user_id"], f"🎉 Evento speciale: {event['name']} è iniziato! {event['description']}")

# ========== MAIN ==========

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance_cmd))
    application.add_handler(CommandHandler("businesses", businesses_cmd))
    application.add_handler(CommandHandler("daily", daily_cmd))
    application.add_handler(CommandHandler("quests", quests_cmd))
    application.add_handler(CommandHandler("claim", claim_cmd))
    application.add_handler(CommandHandler("loan", loan_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    application.add_handler(CommandHandler("events", events_cmd))
    application.add_handler(CommandHandler("notifications", notifications_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Job per controllare eventi ogni ora
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_events_job, interval=3600, first=10)

    print("🤖 Bot avviato! Premi Ctrl+C per fermare.")
    application.run_polling()

if __name__ == "__main__":
    main()
