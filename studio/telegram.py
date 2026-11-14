"""Invio di messaggi Telegram.

Uso: python studio/telegram.py "testo"     (messaggio di prova)

Servono due variabili d'ambiente (sul PC) o due Secret del repository (su GitHub Actions):
  TELEGRAM_BOT_TOKEN   token dato da @BotFather
  TELEGRAM_CHAT_ID     numero della tua chat (si legge da /getUpdates dopo aver scritto "ciao" al bot)
Se mancano, invia() non fa nulla e ritorna False: la raccolta serale non si ferma per un bot non configurato.
"""
import os
import sys

import requests

LIMITE = 4000   # Telegram accetta 4096 caratteri per messaggio


def invia(testo: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("Telegram non configurato (mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).")
        return False
    ok = True
    for i in range(0, len(testo), LIMITE):
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": testo[i:i + LIMITE]}, timeout=20)
        if not r.ok:
            print(f"Telegram: errore {r.status_code} {r.json().get('description', '')}")
            ok = False
    return ok


if __name__ == "__main__":
    invia(" ".join(sys.argv[1:]) or "Prova: il bot funziona.")
