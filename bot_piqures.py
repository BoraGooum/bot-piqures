"""
Bot Telegram - Suivi des piqûres

Fonctionnement :
- Un clavier avec 5 boutons (Piqûre 1-4, Perso) reste affiché en bas.
- Piqûre 1 à 4 → le message du bouton est supprimé, seul le résultat
  reste visible : "- 💉💉 : 09h49 → 21h49" (heure de Paris, + 12h)
- Perso → choix du nombre de piqûres (boutons), puis on écrit
  l'heure (0-23) et les minutes (0-59) au clavier. Chaque message
  intermédiaire est supprimé automatiquement ; seul le résultat final
  reste affiché (le message se transforme sur place).

Note : la suppression automatique des messages tapés par
l'utilisateur ne fonctionne nativement qu'en chat privé avec le bot.
Dans un groupe, il faut que le bot soit administrateur avec le droit
de supprimer les messages pour que ça marche aussi.

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
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- Configuration -----------------------------------------------------

BOT_TOKEN = os.environ["BOT_TOKEN"]
DELTA_HEURES = 12
FUSEAU_PARIS = ZoneInfo("Europe/Paris")  # gère automatiquement été/hiver

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

MENU_PRINCIPAL = [
    ["💉", "💉💉"],
    ["💉💉💉", "💉💉💉💉"],
    ["💉 + 🕑"],
]

BOUTON_PERSO = "💉 + 🕑"


def est_bouton_piqure_rapide(texte: str) -> bool:
    return 1 <= len(texte) <= 4 and set(texte) == {"💉"}


def formater_resultat(emoji: str, heure_depart: datetime) -> str:
    heure_fin = heure_depart + timedelta(hours=DELTA_HEURES)
    return f"- {emoji} : {heure_depart.strftime('%Hh%M')} → {heure_fin.strftime('%Hh%M')}"


REGEX_HEURE = re.compile(r"^(\d{1,2})[h:]?(\d{2})$")


def parser_heure(texte: str):
    """Accepte 10h46, 10:46 ou 1046. Renvoie (heure, minute) ou None si invalide."""
    match = REGEX_HEURE.match(texte.strip())
    if not match:
        return None
    heure, minute = int(match.group(1)), int(match.group(2))
    if 0 <= heure <= 23 and 0 <= minute <= 59:
        return heure, minute
    return None


async def supprimer_silencieux(message):
    try:
        await message.delete()
    except Exception:
        pass  # pas les droits (ex: dans un groupe sans permission), on ignore


# --- Menu du bas, toujours visible ---------------------------------------

async def afficher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MENU_PRINCIPAL, resize_keyboard=True)
    await update.message.reply_text("Menu prêt ⬇️", reply_markup=reply_markup)


# --- Piqûre 1 à 4 : uniquement le résultat reste visible ------------------

async def piqure_rapide(update: Update, context: ContextTypes.DEFAULT_TYPE, texte: str):
    emoji = texte  # le bouton est déjà la suite de 💉 voulue
    maintenant = datetime.now(FUSEAU_PARIS)
    resultat = formater_resultat(emoji, maintenant)
    chat_id = update.effective_chat.id

    await supprimer_silencieux(update.message)
    await context.bot.send_message(chat_id=chat_id, text=resultat)


# --- Perso : nombre puis saisie texte de l'heure/minute -------------------

async def perso_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await supprimer_silencieux(update.message)

    clavier = InlineKeyboardMarkup([
        [InlineKeyboardButton("💉", callback_data="n_1"),
         InlineKeyboardButton("💉💉", callback_data="n_2")],
        [InlineKeyboardButton("💉💉💉", callback_data="n_3"),
         InlineKeyboardButton("💉💉💉💉", callback_data="n_4")],
    ])
    msg = await context.bot.send_message(
        chat_id=chat_id, text="Combien de piqûres ?", reply_markup=clavier
    )
    context.user_data["message_id"] = msg.message_id
    context.user_data["chat_id"] = chat_id


async def gerer_choix_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    n = int(query.data.split("_")[1])
    context.user_data["emoji"] = "💉" * n
    context.user_data["etape"] = "attente_heure"
    context.user_data["message_id"] = query.message.message_id
    context.user_data["chat_id"] = query.message.chat_id

    await query.edit_message_text("À quelle heure ? (ex : 10h46, 10:46 ou 1046)")


async def gerer_saisie_heure_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite le texte tapé pour l'heure pendant le flux Perso."""
    texte = update.message.text.strip()
    chat_id = context.user_data.get("chat_id", update.effective_chat.id)
    message_id = context.user_data.get("message_id")

    await supprimer_silencieux(update.message)

    if message_id is None:
        return

    resultat_heure = parser_heure(texte)
    if resultat_heure is None:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Format non reconnu. Écris par exemple 10h46, 10:46 ou 1046 :",
        )
        return

    heure, minute = resultat_heure
    emoji = context.user_data.get("emoji", "💉")
    heure_depart = datetime.now(FUSEAU_PARIS).replace(
        hour=heure, minute=minute, second=0, microsecond=0
    )
    resultat = formater_resultat(emoji, heure_depart)
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=resultat)
    context.user_data.clear()


# --- Répartiteur de texte --------------------------------------------------

async def gerer_texte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    etape = context.user_data.get("etape")
    if etape == "attente_heure":
        await gerer_saisie_heure_minute(update, context)
        return

    texte = update.message.text.strip()
    if est_bouton_piqure_rapide(texte):
        await piqure_rapide(update, context, texte)
        return
    if texte == BOUTON_PERSO:
        await perso_start(update, context)
        return

    await afficher_menu(update, context)


# --- Lancement -----------------------------------------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", afficher_menu))
    app.add_handler(CallbackQueryHandler(gerer_choix_nombre, pattern="^n_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gerer_texte))

    app.run_polling()


if __name__ == "__main__":
    main()
