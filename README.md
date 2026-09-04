# Crypto Daily Trading Bot (TradingView -> OKX)

Bot d'execució automàtica dissenyat per rebre senyals d'un indicador de **TradingView (temporalitat diària 1D)** i executar ordres de compra a **OKX** amb gestió de capital per a **fins a 14 cryptos simultànies**.

---

## 1. Característiques Principals

- **Divisió de Capital Garantida (14 Slots):**
  - Si el compte té 1.000$ d'equity, divideix el capital en 14 parts iguals (~71,42$ per posició).
  - Garanteix que sempre hi ha capital disponible encara que les 14 cryptos donin senyal de compra alhora.
- **Protecció de Duplicats:** Evita comprar dues vegades la mateixa crypto si ja té una posició oberta.
- **Límit Màxim de Risc:** No permet superar les 14 posicions simultànies.
- **Suport per a Spot i Futurs Perpètus (SWAP):** Configurable amb un simple paràmetre a `.env`.
- **Mode Demo (Paper Trading):** Permet provar amb l'entorn de proves d'OKX sense arriscar diners reals.
- **Avisos per Telegram:** T'envia una notificació a l'instant de la compra recordant-te que entris a OKX a col·locar el Stop Loss (SL) i Take Profit (TP) manuals.

---

## 2. Instal·lació i Posada en Marxa

### Pas 1: Entorn Virtual i Dependències
El projecte ja compta amb el seu entorn virtual `venv` creat. Si cal reinstal·lar:
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Pas 2: Configuració de l'arxiu `.env`
Obre el fitxer `.env` i afegeix les teves dades:
```ini
# Claus d'API d'OKX (recomanat crear-les dins del subcompte)
OKX_API_KEY=la_teva_api_key
OKX_SECRET_KEY=la_teva_secret_key
OKX_PASSPHRASE=la_teva_passphrase

# Posa 'true' per a mode Demo (proves) o 'false' per a diners reals
OKX_IS_DEMO=true

# Tipus de mercat: 'SWAP' (Futurs) o 'SPOT' (Comptat)
INSTRUMENT_TYPE=SWAP

# Màxim de posicions i slots
MAX_OPEN_POSITIONS=14
CAPITAL_SLOTS=14
LEVERAGE=2

# Secret per autenticar el webhook
WEBHOOK_SECRET=el_teu_token_secret_123

# Opcional: Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### Pas 3: Iniciar el Servidor
```bash
./venv/bin/python server.py
```
El servidor quedarà escoltant a `http://0.0.0.0:8000`.

---

## 3. Connectar amb TradingView (Exposar a Internet)

Perquè TradingView pugui enviar el Webhook al teu ordinador o servidor:

### Opció A: Utilitzant Ngrok (Local / Mac)
1. Descarrega i executa ngrok:
   ```bash
   ngrok http 8000
   ```
2. Ngrok et donarà una URL pública com:
   `https://a1b2-c3d4.ngrok-free.app`
3. La teva URL de Webhook per a TradingView serà:
   `https://a1b2-c3d4.ngrok-free.app/webhook`

### Opció B: En un Servidor Cloud / VPS
Si el desglos a un VPS (DigitalOcean, Hetzner, AWS, etc.), la URL serà:
`http://IP_DEL_TEU_VPS:8000/webhook` (o amb domini i HTTPS via Nginx/Caddy).

---

## 4. Configuració de l'Alerta a TradingView

A cadascun dels **14 gràfics de cryptos** (ex: SOL, BTC, ETH, AVAX, etc.) en **temporalitat diària (1D)**:

1. Fes clic a **Create Alert (Alt + A)**.
2. **Condition:**
   - Selecciona l'indicador: `ML Supertrend Alert (...)`
   - Selecciona la subcondició: `Lorentzian BUY`
3. **Trigger:**
   - ⚠️ **MOLT IMPORTANT:** Canvia de *Once only* a **Once Per Bar Close**.
   - *(En 1D, això fa que l'alerta només es dispari quan l'espelma diària es tanca confirmant la compra, i es manté activa per a tots els dies futurs).*
4. **Notifications:**
   - Marca la casella **Webhook URL**.
   - Introdueix la teva URL (ex: `https://el-teu-ngrok.ngrok-free.app/webhook`).
5. **Message:**
   Enganxa aquest JSON exactament:
   ```json
   {
     "secret": "el_teu_token_secret_123",
     "ticker": "{{ticker}}",
     "price": {{close}},
     "action": "BUY"
   }
   ```
6. Fes clic a **Create**.

---

## 5. Prova de Senyal Local (Simulació)

Pots provar el funcionament del bot sense esperar que TradingView enviï una senyal utilitzant l'script `test_signal.py`:

```bash
# Amb el servidor en funcionament en un altre terminal:
./venv/bin/python test_signal.py SOLUSDT.P 75.13
```

---

## 6. Execució dels Tests Automàtics

Per verificar que tota la lògica matemàtica i el mapa de símbols funcionen al 100%:
```bash
./venv/bin/pytest -v
```
