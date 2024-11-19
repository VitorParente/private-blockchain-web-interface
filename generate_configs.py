# run this script to generate the configuration files for the blockchain network
# run this script on the Docker host.

import os
import json
from eth_account import Account
from eth_keys import keys
import shutil

# Set paths for generated files and data
CONFIG_DIR = './config'
DATA_DIR = './data'
GENESIS_PATH = os.path.join(CONFIG_DIR, 'genesis.json')
STATIC_NODES_PATH = os.path.join(CONFIG_DIR, 'static-nodes.json')

# Ensure necessary directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def clear_existing_configs():
    """Delete existing configuration files and container data."""
    print("Clearing existing configuration files...")
    if os.path.exists(GENESIS_PATH):
        os.remove(GENESIS_PATH)
    if os.path.exists(STATIC_NODES_PATH):
        os.remove(STATIC_NODES_PATH)

    print("Clearing existing container data...")
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

def generate_account():
    """Generate a new Ethereum account."""
    account = Account.create()
    private_key = account.key.hex()[2:]  # Strip '0x' prefix
    private_key = private_key.zfill(64)  # Ensure private key is 64 characters
    print(f"DEBUG: Generated private key: {private_key}")
    print(f"DEBUG: Generated address: {account.address}")
    address = account.address

    # Save credentials to a file
    credentials_path = './config/account_credentials.json'
    with open(credentials_path, 'w') as cred_file:
        json.dump({'address': address, 'private_key': private_key}, cred_file, indent=4)
    
    print(f"Generated account saved at {credentials_path}")
    return {"address": address, "private_key": private_key}

def create_genesis(validators):
    """Generate genesis.json for Clique."""
    genesis = {
        "config": {
            "chainId": 1234,
            "homesteadBlock": 0,
            "eip150Block": 0,
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "londonBlock": 0,
            "clique": {
                "period": 5,
                "epoch": 30000
            }
        },
        "nonce": "0x0",
        "timestamp": "0x0",
        "extraData": create_extra_data(validators),
        "gasLimit": "0x1fffffffffffff",
        "difficulty": "0x1",
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase": "0x0000000000000000000000000000000000000000",
        "alloc": {addr[2:]: {"balance": "0x200000000000000000000000000000000000000000000000000000000000000"} for addr in validators},
        "number": "0x0",
        "gasUsed": "0x0",
        "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000"
    }

    with open(GENESIS_PATH, 'w') as genesis_file:
        json.dump(genesis, genesis_file, indent=4)
    print(f"Created {GENESIS_PATH}")


def create_extra_data(validators):
    """Create the extraData field for Clique genesis block."""
    vanity = bytes(32)  # 32 bytes of zero

    # Convert validator addresses to 20-byte binary values and concatenate
    validators_bytes = b''.join([bytes.fromhex(addr[2:]) for addr in validators])

    signature = bytes(65)  # 65 bytes of zero for genesis block

    extra_data = vanity + validators_bytes + signature

    # Debug: print the extraData
    print(f"DEBUG: extraData = {extra_data.hex()}")
    return '0x' + extra_data.hex()

def create_static_nodes(enodes):
    """Generate static-nodes.json with the provided enodes."""
    with open(STATIC_NODES_PATH, 'w') as static_nodes_file:
        json.dump(enodes, static_nodes_file, indent=4)
    print(f"Created {STATIC_NODES_PATH}")
    
    # Copy static-nodes.json to each node's data directory
    for i in range(3):
        data_dir = f'./data/authority{i+1}'
        os.makedirs(data_dir, exist_ok=True)
        shutil.copy(STATIC_NODES_PATH, data_dir)

def generate_configs():
    """Main function to generate all configurations."""
    clear_existing_configs()

    print("Generating node keys...")
    node_keys = []
    for i in range(3):
        key_info = generate_account()
        private_key = key_info['private_key']
        node_keys.append(private_key)
        data_dir = f'./data/authority{i+1}'
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, 'nodekey'), 'w') as key_file:
            key_file.write(private_key)

    print("Creating genesis.json...")
    validator_addresses = [Account.from_key(key).address for key in node_keys]
    create_genesis(validator_addresses)

    print("Generating enodes and static-nodes.json...")
    ips = ['172.16.238.10', '172.16.238.11', '172.16.238.12']  # Use service names
    enodes = []
    for key, ip in zip(node_keys, ips):
        private_key_bytes = bytes.fromhex(key)
        private_key = keys.PrivateKey(private_key_bytes)
        public_key = private_key.public_key
        node_id = public_key.to_hex()[2:]  # Remove '0x' prefix
        enode = f"enode://{node_id}@{ip}:30303"
        enodes.append(enode)
    
    create_static_nodes(enodes)

    print("Configuration files and data cleanup complete.")

if __name__ == '__main__':
    generate_configs()