"""
Bot Telegram - Suivi des piqûres

Commandes :
- Piqûre 1, Piqûre 2, Piqûre 3, Piqûre 4 → envoie immédiatement
  💉 x N : heure actuelle → heure actuelle + 12h
- Perso → demande le nombre de piqûres puis l'heure exacte,
  et calcule heure saisie → heure saisie + 12h

Installation :
    pip install python-telegram-bot --upgrade

Configuration :
    Le token (donné par @BotFather sur Telegram) doit être défini
    dans une variable d'environnement BOT_TOKEN.

Lancement local :
    BOT_TOKEN="ton_token" python bot_piqures.py
"""

import logging
import os
from datetime import datetime, timedelta

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# --- Configuration ---------------------------------------------------------

BOT_TOKEN = os.environ["BOT_TOKEN"]

DELTA_HEURES = 12  # nombre d'heures ajoutées après la piqûre

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# États de la conversation "Perso"
CHOIX_NOMBRE, CHOIX_HEURE = range(2)

MENU_PRINCIPAL = [
    ["Piqûre 1", "Piqûre 2"],
    ["Piqûre 3", "Piqûre 4"],
    ["Perso"],
]


# --- Commandes simples -------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MENU_PRINCIPAL, resize_keyboard=True)
    await update.message.reply_text("Choisis une option :", reply_markup=reply_markup)


async def piqure_rapide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les boutons Piqûre 1 à Piqûre 4."""
    texte = update.message.text
    n = int(texte.split()[-1])
    emoji = "💉" * n

    maintenant = datetime.now()
    plus_tard = maintenant + timedelta(hours=DELTA_HEURES)

    message = f"{emoji} : {maintenant.strftime('%H:%M')} → {plus_tard.strftime('%H:%M')}"
    await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(MENU_PRINCIPAL, resize_keyboard=True))


# --- Conversation "Perso" -----------------------------------------------

async def perso_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clavier = [["💉", "💉💉"], ["💉💉💉", "💉💉💉💉"]]
    reply_markup = ReplyKeyboardMarkup(clavier, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Combien de piqûres ?", reply_markup=reply_markup)
    return CHOIX_NOMBRE


async def perso_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["emoji"] = update.message.text.strip()
    await update.message.reply_text(
        "À quelle heure ? (format HH:MM, ex : 07:13)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CHOIX_HEURE


async def perso_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = update.message.text.strip().replace("h", ":")
    try:
        heure, minute = map(int, texte.split(":"))
        heure_saisie = datetime.now().replace(
            hour=heure, minute=minute, second=0, microsecond=0
        )
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Format invalide, réessaie avec HH:MM (ex : 07:13)."
        )
        return CHOIX_HEURE

    plus_tard = heure_saisie + timedelta(hours=DELTA_HEURES)
    emoji = context.user_data.get("emoji", "💉")

    message = f"{emoji} : {heure_saisie.strftime('%H:%M')} → {plus_tard.strftime('%H:%M')}"
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(MENU_PRINCIPAL, resize_keyboard=True)
    )
    return ConversationHandler.END


async def annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Annulé.", reply_markup=ReplyKeyboardMarkup(MENU_PRINCIPAL, resize_keyboard=True)
    )
    return ConversationHandler.END


# --- Lancement du bot ----------------------------------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    conv_perso = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Perso$"), perso_start)],
        states={
            CHOIX_NOMBRE: [MessageHandler(filters.Regex("^💉+$"), perso_nombre)],
            CHOIX_HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, perso_heure)],
        },
        fallbacks=[CommandHandler("cancel", annuler)],
    )
    app.add_handler(conv_perso)

    app.add_handler(MessageHandler(filters.Regex("^Piqûre [1-4]$"), piqure_rapide))

    app.run_polling()


if __name__ == "__main__":
    main()
