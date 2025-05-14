import json
import os
from solcx import compile_standard, install_solc
from web3 import Web3
install_solc('0.8.0')

def compile_contract():
    with open("contracts/Voting.sol", "r") as file:
        voting_file = file.read()
        
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"Voting.sol": {"content": voting_file}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
                }
            },
        },
        solc_version="0.8.0",
    )
    with open("contracts/compiled_code.json", "w") as file:
        json.dump(compiled_sol, file)
    
    return compiled_sol

def deploy_contract(provider_url, private_key):
    compiled_sol = compile_contract()
    contract_data = compiled_sol["contracts"]["Voting.sol"]["Voting"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]
    w3 = Web3(Web3.HTTPProvider(provider_url))
    account = w3.eth.account.from_key(private_key)
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    transaction = Contract.constructor().build_transaction(
        {
            "chainId": w3.eth.chain_id,
            "gasPrice": w3.eth.gas_price,
            "from": account.address,
            "nonce": nonce,
        }
    )
    
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    with open("contracts/abi.json", "w") as file:
        json.dump(abi, file)
    
    print(f"Kontrakt manzili: {tx_receipt.contractAddress}")
    return tx_receipt.contractAddress, abi

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    provider_url = os.getenv("BLOCKCHAIN_PROVIDER", "http://127.0.0.1:7545")
    private_key = os.getenv("ADMIN_PRIVATE_KEY")
    if not private_key:
        print("ADMIN_PRIVATE_KEY .env faylida topilmadi")
    else:
        contract_address, abi = deploy_contract(provider_url, private_key)
        with open(".env", "a") as env_file:
            env_file.write(f"\nCONTRACT_ADDRESS={contract_address}\n")