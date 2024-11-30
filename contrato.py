import solcx
import json
from solcx import compile_source, install_solc, set_solc_version, get_solc_version
from web3 import Web3

# Conexão com o nó Geth via HTTP
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Verifica e instala a versão do Solc necessária
try:
    print("Versão do Solc instalada:", get_solc_version())
except solcx.exceptions.SolcNotInstalled:
    print("Solc não encontrado. Instalando a versão necessária...")
    install_solc("0.8.28")  # Ajuste a versão conforme necessário
    set_solc_version("0.8.28")
    print("Instalação concluída. Versão instalada:", get_solc_version())

# Certifique-se de que a conexão está funcionando
if not w3.is_connected():
    print("Erro ao conectar com o nó Geth")
    exit()

# Código do contrato inteligente
contract_source_code = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract DataStorage {
    struct Data {
        uint256 id;
        string coordenadas;
        uint256 timestamp;
        address sender;
    }

    mapping(uint256 => Data) public dataRecords;
    uint256 public dataCount;

    // Definindo limite de caracteres para coordenadas e intervalo de timestamp
    uint256 public maxCoordenadasLength = 100; // Limite de 100 caracteres para as coordenadas
    uint256 public minTimestamp = 1609459200; // 01/01/2021 (timestamp Unix)
    uint256 public maxTimestamp = block.timestamp; // O timestamp máximo é o atual

    event DataStored(uint256 id, string coordenadas, uint256 timestamp, address sender);

    // Função para validar se as coordenadas têm o formato correto
    function isValidCoordenadas(string memory _coordenadas) internal pure returns (bool) {
        bytes memory coordenadas = bytes(_coordenadas);
        bool hasComma = false;

        // Verificar se existe uma vírgula para separar latitude e longitude
        for (uint i = 0; i < coordenadas.length; i++) {
            if (coordenadas[i] == ",") {
                hasComma = true;
                break;
            }
        }
        return hasComma;
    }

    function storeData(string memory _coordenadas) public {
        // Validação de tamanho de coordenadas
        require(bytes(_coordenadas).length <= maxCoordenadasLength, "Coordenadas muito grandes, limite de 100 caracteres");
        
        // Validação de formato de coordenadas (precisa ter uma vírgula separando latitude e longitude)
        require(isValidCoordenadas(_coordenadas), "Formato de coordenadas invalido, deve ser 'latitude,longitude'");

        // Validação de intervalo do timestamp (exemplo: garantir que o timestamp esteja dentro de um intervalo)
        uint256 currentTimestamp = block.timestamp;
        require(currentTimestamp >= minTimestamp && currentTimestamp <= maxTimestamp, 
                "Timestamp fora do intervalo permitido");

        // Armazenamento dos dados
        dataCount++;
        dataRecords[dataCount] = Data(dataCount, _coordenadas, currentTimestamp, msg.sender);

        // Emitir o evento
        emit DataStored(dataCount, _coordenadas, currentTimestamp, msg.sender);
    }

    // Função para obter os dados armazenados
    function getData(uint256 _id) public view returns (uint256, string memory, uint256, address) {
        Data memory data = dataRecords[_id];
        return (data.id, data.coordenadas, data.timestamp, data.sender);
    }
}

'''

# Compila o código do contrato
compiled_sol = compile_source(contract_source_code)
contract_id, contract_interface = compiled_sol.popitem()

# Obtém bytecode e ABI
bytecode = contract_interface['bin']
abi = contract_interface['abi']

# Load account credentials
credentials_path = './config/account_credentials.json'
try:
    with open(credentials_path, 'r') as cred_file:
        account_credentials = json.load(cred_file)
    account = account_credentials['address']
    private_key = account_credentials['private_key']
    print(f"Loaded account: {account}")
except FileNotFoundError:
    print(f"Account credentials not found at {credentials_path}.")
    account_address = None
    private_key = None

account_from_private_key = w3.eth.account.from_key(private_key).address
if account_from_private_key.lower() != account.lower():
    print(f"A chave privada não corresponde ao endereço. Endereço gerado: {account_from_private_key}")
else:
    print("A chave privada corresponde ao endereço.")

balance = w3.eth.get_balance(account)
print(f"Saldo da conta: {w3.from_wei(balance, 'ether')} ETH")

# Cria a transação para implantar o contrato
try:
    print("Implantando o contrato, aguarde...")
    nonce = w3.eth.get_transaction_count(account)

    # Cria a transação
    tx = {
        'from': account,
        'data': bytecode,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.to_wei('20', 'gwei'),
    }

    # Assina a transação
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)

    # Envia a transação
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print(f"Contrato implantado com sucesso! Endereço: {contract_address}")

    # Salva o endereço do contrato e o ABI em um arquivo JSON
    contract_config = {
        "address": contract_address,
        "abi": abi
    }
    with open('config_contrato.json', 'w') as json_file:
        json.dump(contract_config, json_file, indent=4)
    print("Configuração do contrato salva em config_contrato.json")

except Exception as e:
    print(f"Erro ao implantar o contrato: {e}")
    exit()

