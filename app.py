from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

APP_ACCESS_TOKEN = 'git'
VERIFY_TOKEN = 'YhQw8qN6RmBUUOQ'
CRYPTO_API_URL = 'https://api.coingecko.com/api/v3'
COINMARKETCAP_API_URL = 'https://pro-api.coinmarketcap.com/v1'
COINMARKETCAP_API_KEY = '1f3c28d5-97e7-4aa3-b765-d4e9ed661e14'  # Replace with your CoinMarketCap API key
admins = '100031096454833'
is_bot_active = True
user_wallets = {}


def get_crypto_price_coin_gecko(symbol):
    url = f"{CRYPTO_API_URL}/simple/price?ids={symbol}&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    if symbol in data:
        return data[symbol]['usd']
    else:
        return None


def get_crypto_details_coin_gecko(symbol):
    url = f"{CRYPTO_API_URL}/coins/markets?vs_currency=usd&ids={symbol}"
    response = requests.get(url)
    data = response.json()
    if data:
        details = data[0]
        return {
            'current_price': details['current_price'],
            'high_24h': details['high_24h'],
            'low_24h': details['low_24h'],
            'price_change_percentage_7d': details['price_change_percentage_7d_in_currency'],
            'total_volume': details['total_volume'],
            'market_cap': details['market_cap']
        }
    else:
        return None


def get_crypto_details_coin_market_cap(symbol):
    url = f"{COINMARKETCAP_API_URL}/cryptocurrency/quotes/latest"
    params = {
        'symbol': symbol,
        'convert': 'USD'
    }
    headers = {
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if 'data' in data and symbol.upper() in data['data']:
        details = data['data'][symbol.upper()]['quote']['USD']
        return {
            'current_price': details['price'],
            'high_24h': details['high_24h'],
            'low_24h': details['low_24h'],
            'price_change_percentage_7d': details['percent_change_7d'],
            'total_volume': details['volume_24h'],
            'market_cap': details['market_cap']
        }
    else:
        return None


def send_message(recipient_id, message):
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": "Personal Bot: " + message}
    }
    params = {"access_token": APP_ACCESS_TOKEN}
    response = requests.post("https://graph.facebook.com/v12.0/me/messages", json=data, params=params)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")


def stop_bot():
    global is_bot_active
    is_bot_active = False


@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            return challenge
        else:
            return 'Invalid verification token'
    elif request.method == 'POST':
        if not is_bot_active:
            return 'Bot is stopped'

        data = request.json
        for entry in data['entry']:
            messaging = entry.get('messaging')
            if messaging:
                for event in messaging:
                    sender_id = event['sender']['id']
                    if event.get('message'):
                        message_text = event['message'].get('text')
                        group_id = event['recipient']['id']

                        if 'group_id' in event:
                            if message_text.lower() == '/stopbot' and sender_id in admins:
                                stop_bot()
                                send_message(sender_id, "Bot has been stopped by the admin.")
                            elif message_text.lower().startswith('/price'):
                                parts = message_text.split()
                                if len(parts) == 2:
                                    symbol = parts[1].lower()
                                    details = get_crypto_details_coin_gecko(symbol)
                                    if not details:
                                        details = get_crypto_details_coin_market_cap(symbol)
                                    if details:
                                        send_message(group_id,
                                                     f"The current price of {symbol} is ${details['current_price']}\n"
                                                     f"24h High: ${details['high_24h']}\n"
                                                     f"24h Low: ${details['low_24h']}\n"
                                                     f"7-day Change: {details['price_change_percentage_7d']}%\n"
                                                     f"Volume: ${details['total_volume']}\n"
                                                     f"Market Cap: ${details['market_cap']}")
                                    else:
                                        send_message(group_id, f"Sorry, could not retrieve details for {symbol}")
                                else:
                                    send_message(group_id, "Invalid command. Usage: /price <crypto_symbol>")
                            elif message_text.lower().startswith('/addwallet'):
                                parts = message_text.split()
                                if len(parts) == 2:
                                    wallet = parts[1]
                                    user_wallets[sender_id] = wallet
                                    send_message(group_id, f"Wallet {wallet} added successfully.")
                                else:
                                    send_message(group_id, "Invalid command. Usage: /addwallet <wallet_address>")
                            elif message_text.lower().startswith('/removewallet'):
                                if sender_id in user_wallets:
                                    del user_wallets[sender_id]
                                    send_message(group_id, "Your wallet has been removed.")
                                else:
                                    send_message(group_id, "No wallet found to remove.")
                            elif message_text.lower().startswith('/mywallet'):
                                if sender_id in user_wallets:
                                    wallet = user_wallets[sender_id]
                                    send_message(group_id, f"Your wallet address is {wallet}")
                                else:
                                    send_message(group_id, "No wallet found. Add one using /addwallet <wallet_address>")

        return 'OK'


if __name__ == '__main__':
    app.run(debug=False)
