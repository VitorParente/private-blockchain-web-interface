import json
from web3 import Web3

# Conexão com o nó Geth via HTTP
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Carrega as credenciais da conta
credentials_path = './config/account_credentials.json'  # Caminho para as credenciais
with open(credentials_path, 'r') as cred_file:
    account_credentials = json.load(cred_file)
account = account_credentials['address']
private_key = account_credentials['private_key']

# Carrega a configuração do contrato
contract_config_path = './config_contrato.json'
with open(contract_config_path, 'r') as config_file:
    contract_config = json.load(config_file)

contract_address = contract_config['address']
abi = contract_config['abi']

# Instância do contrato no endereço implantado
data_storage_instance = w3.eth.contract(address=contract_address, abi=abi)

# Exemplo: Armazenar dados no contrato
try:
    print("Armazenando dados no contrato...")

    # Cria a transação para armazenar dados
    tx_store = data_storage_instance.functions.storeData("40.7128, -74.0060").build_transaction({
        'from': account,
        'nonce': w3.eth.get_transaction_count(account),  # Usa o nonce atual
        'gas': 200000,  # Defina um limite de gás adequado
        'gasPrice': w3.to_wei('20', 'gwei'),  # Defina um preço de gás adequado
    })

    # Assina a transação
    signed_tx_store = w3.eth.account.sign_transaction(tx_store, private_key)

    # Envia a transação
    tx_hash_store = w3.eth.send_raw_transaction(signed_tx_store.raw_transaction)
    print(f"Transação enviada! Hash: {tx_hash_store.hex()}")
    w3.eth.wait_for_transaction_receipt(tx_hash_store)
    print("Dados armazenados com sucesso!")

    # Aguarda a confirmação do evento
    event_filter = data_storage_instance.events.DataStored.create_filter(from_block='latest')
    events = event_filter.get_all_entries()

    if events:
        last_event = events[-1]  # Pega o último evento
        print(f"Último ID armazenado: {last_event.args.id}")
        # Agora você pode usar esse ID para recuperar os dados
        data_record = data_storage_instance.functions.getData(last_event.args.id).call()
        print(f"Dados armazenados: ID: {data_record[0]}, Coordenadas: {data_record[1]}, Timestamp: {data_record[2]}, Sender: {data_record[3]}")
    else:
        print("Nenhum evento encontrado após o armazenamento.")

except Exception as e:
    print(f"Erro ao armazenar dados: {e}")
