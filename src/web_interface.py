from flask import Flask, render_template, jsonify, request
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from datetime import datetime
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
    
    try:
        for block_number in range(0, latest_block + 1):
            block = w3.eth.get_block(block_number, full_transactions=True)
            print(f"Processing block {block_number} with {len(block.transactions)} transactions")
            for tx in block.transactions:
                input_data = tx.input
                try:
                    data_text = w3.to_text(hexstr=input_data.hex())
                except UnicodeDecodeError:
                    data_text = input_data.hex()  # Retorna a representação hexadecimal em caso de erro

                logs.append({
                    "block": block.number,
                    "transactionHash": tx.hash.hex(),
                    "from": tx['from'],
                    "to": tx.to,
                    "value": Web3.from_wei(tx.value, 'ether'),  # Corrigido aqui
                    "data": data_text
                })
    except Exception as e:
        app.logger.error(f"Erro ao processar blocos: {str(e)}")
        return jsonify({"error": "Não foi possível obter as transações"}), 500

    print(f"Returning {len(logs)} transactions")
    return jsonify(logs), 200


@app.route('/get_transaction_data', methods=['GET'])
def get_transaction_data():
    tx_hash = request.args.get('tx_hash')
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400
    
    try:
        # Obtém os detalhes da transação a partir do hash
        tx = w3.eth.get_transaction(tx_hash)

        # Converte campos que podem ser HexBytes para strings
        transaction_data = {
            "hash": tx.hash.hex(),  # Converte o hash para string
            "from": tx['from'],
            "to": tx['to'],
            "value": w3.from_wei(tx['value'], 'ether'),  # Converte de Wei para Ether
            "input": w3.to_text(hexstr=tx['input'].hex()) if tx['input'] else None  # Converte o input
        }

        # Verifica se a transação contém dados
        if transaction_data['input']:
            # Decodifica os dados da transação
            transaction_data.update(json.loads(transaction_data['input']))  # Adiciona dados decodificados
            return jsonify(transaction_data), 200
        else:
            return jsonify({"error": "No data found for this transaction"}), 404

    except Exception as e:
        return jsonify({"error": f"Error retrieving transaction: {str(e)}"}), 500

@app.route('/send_transaction', methods=['POST'])
def send_transaction():
    if not w3.provider.is_connected():
        return jsonify({"error": "Cannot connect to blockchain"}), 500
    
    if not account_address or not private_key:
        return jsonify({"error": "No account configured"}), 500

    data = request.get_json()
    if not data or 'message' not in data or 'sender_id' not in data or 'coordinates' not in data:
        return jsonify({"error": "Invalid data format"}), 400

    message = data['message']
    sender_id = data['sender_id']
    coordinates = data['coordinates']
    timestamp = datetime.utcnow().isoformat() + "Z"

    transaction_data = {
        "sender_id": sender_id,
        "timestamp": timestamp,
        "coordinates": coordinates,
        "message": message
    }

    # Converte os dados para JSON e depois para hexadecimal
    encoded_data = w3.to_hex(text=json.dumps(transaction_data))

    retry_count = 5  # Limite de tentativas de envio
    retry_delay = 5  # Delay entre as tentativas (segundos)

    for attempt in range(retry_count):
        try:
            # Atualiza o nonce antes de cada tentativa
            nonce = nonce_manager.get_next_nonce()
            tx = {
                'to': account_address,  # Sending to self for demo
                'value': 0,
                'data': encoded_data,
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
                print(f"Attempt {attempt + 1}: Nonce error. Retrying...")
                # Atualiza o nonce antes da próxima tentativa
                nonce_manager.current_nonce = w3.eth.get_transaction_count(account_address, 'pending')
                time.sleep(retry_delay)  # Delay antes de tentar novamente
                continue  # Retry with updated nonce

            return jsonify({"error": error_message}), 400
    
    return jsonify({"error": "Failed to send transaction after retries"}), 500

    if not w3.provider.is_connected():
        return jsonify({"error": "Cannot connect to blockchain"}), 500
    
    if not account_address or not private_key:
        return jsonify({"error": "No account configured"}), 500

    data = request.get_json()
    if not data or 'message' not in data or 'sender_id' not in data or 'coordinates' not in data:
        return jsonify({"error": "Invalid data format"}), 400

    message = data['message']
    sender_id = data['sender_id']
    coordinates = data['coordinates']
    timestamp = datetime.utcnow().isoformat() + "Z"

    transaction_data = {
        "sender_id": sender_id,
        "timestamp": timestamp,
        "coordinates": coordinates,
        "message": message
    }

    # Converte os dados para JSON e depois para hexadecimal
    encoded_data = w3.to_hex(text=json.dumps(transaction_data))

    for _ in range(3):  # Retry mechanism for nonce-related errors
        try:
            nonce = nonce_manager.get_next_nonce()
            tx = {
                'to': account_address,  # Sending to self for demo
                'value': 0,
                'data': encoded_data,
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


@app.route('/save_to_contract', methods=['POST'])
def save_to_contract():
    # Carregar o endereço e ABI do contrato
    with open('./config_contrato.json') as f:
        contract_config = json.load(f)

    contract_address = contract_config['contract_address']
    contract_abi = contract_config['contract_abi']

    # Criar a instância do contrato
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    data = request.get_json()
    if not data or 'data_to_store' not in data:
        return jsonify({"error": "Invalid data format"}), 400

    data_to_store = data['data_to_store']

    # Crie a transação para chamar a função do contrato
    try:
        nonce = nonce_manager.get_next_nonce()
        tx = contract.functions.storeData(data_to_store).build_transaction({
            'chainId': 1,  # ou a ID da sua rede
            'gas': 2000000,
            'gasPrice': w3.to_wei('1', 'gwei'),
            'nonce': nonce,
        })

        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return jsonify({"transactionHash": tx_hash.hex()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3055)
