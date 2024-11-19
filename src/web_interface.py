from flask import Flask, render_template, jsonify, request
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import os
import json
import threading
import time

# Load account credentials
credentials_path = './config/account_credentials.json'
try:
    with open(credentials_path, 'r') as cred_file:
        account_credentials = json.load(cred_file)
    account_address = account_credentials['address']
    private_key = account_credentials['private_key']
    print(f"Loaded account: {account_address}")
except FileNotFoundError:
    print(f"Account credentials not found at {credentials_path}.")
    account_address = None
    private_key = None

app = Flask(__name__)
rpc_url = os.getenv('RPC_URL', 'http://172.16.238.10:8545')
w3 = Web3(Web3.HTTPProvider(rpc_url))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

class NonceManager:
    def __init__(self, w3, account_address):
        self.w3 = w3
        self.account_address = account_address
        self.lock = threading.Lock()
        self.current_nonce = None

    def initialize_nonce(self):
        """Initialize nonce with infinite retry using exponential backoff."""
        retry_delay = 5  # Initial delay in seconds
        max_delay = 300  # Maximum delay of 5 minutes

        while True:
            try:
                self.current_nonce = self.w3.eth.get_transaction_count(self.account_address, 'pending')
                print(f"Nonce initialized: {self.current_nonce}")
                break  # Successfully initialized
            except Exception as e:
                print(f"Error initializing nonce: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)  # Exponential backoff

    def get_next_nonce(self):
        with self.lock:
            if self.current_nonce is None:
                self.initialize_nonce()
            next_nonce = self.current_nonce
            self.current_nonce += 1
            return next_nonce

# Global nonce manager and initialization lock
nonce_manager = None
nonce_lock = threading.Lock()

def initialize_app():
    """Application initialization logic with safe NonceManager initialization."""
    global nonce_manager
    with nonce_lock:
        if nonce_manager is None:
            nonce_manager = NonceManager(w3, account_address)
            nonce_manager.initialize_nonce()

# Run initialization logic when the app starts
initialize_app()

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No Content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    if not w3.provider.is_connected():
        print("Blockchain connection failed")
        return jsonify({"error": "Cannot connect to blockchain"}), 500
    logs = []
    latest_block = w3.eth.block_number
    print(f"Latest block: {latest_block}")
    for block_number in range(0, latest_block + 1):
        block = w3.eth.get_block(block_number, full_transactions=True)
        print(f"Processing block {block_number} with {len(block.transactions)} transactions")
        for tx in block.transactions:
            input_data = tx.input
            try:
                data_text = w3.to_text(hexstr=input_data.hex())
            except UnicodeDecodeError:
                data_text = input_data
            logs.append({
                "block": block.number,
                "transactionHash": tx.hash.hex(),
                "data": data_text
            })
    print(logs)
    print(f"Returning {len(logs)} transactions")
    return jsonify(logs)

@app.route('/send_transaction', methods=['POST'])
def send_transaction():
    if not w3.provider.is_connected():
        return jsonify({"error": "Cannot connect to blockchain"}), 500
    
    if not account_address or not private_key:
        return jsonify({"error": "No account configured"}), 500

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    message = data['message']

    for _ in range(3):  # Retry mechanism for nonce-related errors
        try:
            nonce = nonce_manager.get_next_nonce()
            print(f"Using nonce to POST: {nonce}")

            tx = {
                'to': account_address,  # Sending to self for demo
                'value': 0,
                'data': w3.to_hex(text=message),
                'gas': 2000000,
                'gasPrice': w3.to_wei('1', 'gwei'),
                'nonce': nonce,
            }

            signed_tx = Account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            return jsonify({"transactionHash": tx_hash.hex()})
        
        except ValueError as e:
            error_message = str(e)
            if 'nonce too low' in error_message or 'already used' in error_message:
                nonce_manager.current_nonce = w3.eth.get_transaction_count(account_address, 'pending')
                continue  # Retry with updated nonce
            return jsonify({"error": error_message}), 400
    
    return jsonify({"error": "Failed to send transaction after retries"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3055)