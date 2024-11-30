from web3 import Web3
import json

# Conexão com o nó Ethereum
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# ABI do contrato (substitua pela ABI real)
contract_abi =[
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "id",
                    "type": "uint256"
                },
                {
                    "indexed": False,
                    "internalType": "string",
                    "name": "coordenadas",
                    "type": "string"
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "timestamp",
                    "type": "uint256"
                },
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "sender",
                    "type": "address"
                }
            ],
            "name": "DataStored",
            "type": "event"
        },
        {
            "inputs": [],
            "name": "dataCount",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "",
                    "type": "uint256"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "",
                    "type": "uint256"
                }
            ],
            "name": "dataRecords",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "id",
                    "type": "uint256"
                },
                {
                    "internalType": "string",
                    "name": "coordenadas",
                    "type": "string"
                },
                {
                    "internalType": "uint256",
                    "name": "timestamp",
                    "type": "uint256"
                },
                {
                    "internalType": "address",
                    "name": "sender",
                    "type": "address"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_id",
                    "type": "uint256"
                }
            ],
            "name": "getData",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "",
                    "type": "uint256"
                },
                {
                    "internalType": "string",
                    "name": "",
                    "type": "string"
                },
                {
                    "internalType": "uint256",
                    "name": "",
                    "type": "uint256"
                },
                {
                    "internalType": "address",
                    "name": "",
                    "type": "address"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "string",
                    "name": "_coordenadas",
                    "type": "string"
                }
            ],
            "name": "storeData",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

# Endereço do contrato (converta para checksum)
contract_address = "0x5373597cf0ce03cce9a834ef9fa3eddda1db564d"
checksum_address = Web3.to_checksum_address(contract_address)

# Instância do contrato
contract = w3.eth.contract(address=checksum_address, abi=contract_abi)

# Input da transação (obtido do bloco)
input_data = "0xfb218f5f0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001134302e373132382c202d37342e30303630000000000000000000000000000000"

# Decodificar os dados da transação
function_name, function_args = contract.decode_function_input(input_data)

print("Nome da função chamada:", function_name.fn_name)
print("Argumentos passados:", function_args)
