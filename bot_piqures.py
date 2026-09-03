"""
Bot Telegram - Suivi des piqûres

Fonctionnement :
- /piqure1, /piqure2, /piqure3, /piqure4 → envoie immédiatement
  une seule ligne : "- 💉💉 : 09h49 → 21h49" (heure de Paris, + 12h)
- /perso → choix du nombre de piqûres (boutons), puis réglage de
  l'heure avec une horloge à flèches ▲▼, puis validation.

Ces 5 options apparaissent dans le menu natif de Telegram
(icône à côté du trombone) une fois configurées dans BotFather
(voir instructions fournies à côté de ce fichier).

Installation :
    pip install python-telegram-bot --upgrade

Configuration :
    Le token (donné par @BotFather) doit être dans la variable
    d'environnement BOT_TOKEN.

Lancement local :
    BOT_TOKEN="ton_token" python bot_piqures.py
"""

import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# --- Configuration -----------------------------------------------------

BOT_TOKEN = os.environ["BOT_TOKEN"]
DELTA_HEURES = 12
FUSEAU_PARIS = ZoneInfo("Europe/Paris")  # gère automatiquement été/hiver

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def formater_resultat(emoji: str, heure_depart: datetime) -> str:
    heure_fin = heure_depart + timedelta(hours=DELTA_HEURES)
    return f"- {emoji} : {heure_depart.strftime('%Hh%M')} → {heure_fin.strftime('%Hh%M')}"


# --- /piqure1 à /piqure4 : une seule ligne envoyée ----------------------

async def piqure_rapide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Enlève un éventuel "@NomDuBot" ajouté par Telegram dans les groupes
    commande = update.message.text.split("@")[0]
    n = int(commande[-1])
    emoji = "💉" * n
    maintenant = datetime.now(FUSEAU_PARIS)
    await update.message.reply_text(formater_resultat(emoji, maintenant))


# --- /perso : nombre de piqûres puis horloge à flèches -------------------

async def perso_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clavier = InlineKeyboardMarkup([
        [InlineKeyboardButton("💉", callback_data="n_1"),
         InlineKeyboardButton("💉💉", callback_data="n_2")],
        [InlineKeyboardButton("💉💉💉", callback_data="n_3"),
         InlineKeyboardButton("💉💉💉💉", callback_data="n_4")],
    ])
    await update.message.reply_text("Combien de piqûres ?", reply_markup=clavier)


def clavier_horloge(heure: int, minute: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▲", callback_data="h_plus"),
         InlineKeyboardButton("▲", callback_data="m_plus")],
        [InlineKeyboardButton(f"{heure:02d}", callback_data="noop"),
         InlineKeyboardButton(f"{minute:02d}", callback_data="noop")],
        [InlineKeyboardButton("▼", callback_data="h_moins"),
         InlineKeyboardButton("▼", callback_data="m_moins")],
        [InlineKeyboardButton("✅ Valider", callback_data="valider")],
    ])


async def gerer_boutons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("n_"):
        n = int(data.split("_")[1])
        context.user_data["emoji"] = "💉" * n
        maintenant = datetime.now(FUSEAU_PARIS)
        context.user_data["heure"] = maintenant.hour
        context.user_data["minute"] = maintenant.minute
        await query.edit_message_text(
            "Choisis l'heure :",
            reply_markup=clavier_horloge(maintenant.hour, maintenant.minute),
        )
        return

    if data == "noop":
        return

    if data in ("h_plus", "h_moins", "m_plus", "m_moins"):
        heure = context.user_data.get("heure", 0)
        minute = context.user_data.get("minute", 0)
        if data == "h_plus":
            heure = (heure + 1) % 24
        elif data == "h_moins":
            heure = (heure - 1) % 24
        elif data == "m_plus":
            minute = (minute + 1) % 60
        elif data == "m_moins":
            minute = (minute - 1) % 60
        context.user_data["heure"] = heure
        context.user_data["minute"] = minute
        await query.edit_message_text(
            "Choisis l'heure :", reply_markup=clavier_horloge(heure, minute)
        )
        return

    if data == "valider":
        emoji = context.user_data.get("emoji", "💉")
        heure = context.user_data.get("heure", 0)
        minute = context.user_data.get("minute", 0)
        heure_depart = datetime.now(FUSEAU_PARIS).replace(
            hour=heure, minute=minute, second=0, microsecond=0
        )
        await query.edit_message_text(formater_resultat(emoji, heure_depart))
        return


# --- Lancement -----------------------------------------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler(
        ["piqure1", "piqure2", "piqure3", "piqure4"], piqure_rapide
    ))
    app.add_handler(CommandHandler("perso", perso_start))
    app.add_handler(CallbackQueryHandler(gerer_boutons))

    app.run_polling()


if __name__ == "__main__":
    main()
  
