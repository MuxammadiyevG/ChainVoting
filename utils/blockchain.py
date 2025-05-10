import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from flask import current_app

class BlockchainClient:
    def __init__(self, provider_url=None, contract_address=None):
        if provider_url is None:
            provider_url = current_app.config['BLOCKCHAIN_PROVIDER']
        
        if contract_address is None:
            contract_address = current_app.config['CONTRACT_ADDRESS']
        
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # ABI ni o'qish
        with open('contracts/abi.json', 'r') as file:
            contract_abi = json.load(file)
        
        # Kontraktni yaratish
        self.contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        
        # Admin akkountni sozlash
        self.admin_address = current_app.config['ADMIN_ADDRESS']
        self.admin_private_key = current_app.config['ADMIN_PRIVATE_KEY']
    
    def is_connected(self):
        return self.w3.is_connected()
    
    def get_candidates_count(self):
        return self.contract.functions.candidatesCount().call()
    
    def get_candidate(self, candidate_id):
        return self.contract.functions.getCandidate(candidate_id).call()
    
    def has_voted(self, voter_address):
        return self.contract.functions.hasVoted(voter_address).call()
    
    def is_election_active(self):
        started = self.contract.functions.electionStarted().call()
        ended = self.contract.functions.electionEnded().call()
        return started and not ended
    
    def add_candidate(self, name):
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.addCandidate(name).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def start_election(self):
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.startElection().build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def end_election(self):
        nonce = self.w3.eth.get_transaction_count(self.admin_address)
        
        txn = self.contract.functions.endElection().build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': self.admin_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def vote(self, voter_private_key, voter_address, candidate_id):
        nonce = self.w3.eth.get_transaction_count(voter_address)
        
        txn = self.contract.functions.vote(candidate_id).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'from': voter_address
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=voter_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    
    def get_all_candidates(self):
        candidates = []
        count = self.get_candidates_count()
        
        for i in range(1, count + 1):
            candidate_data = self.get_candidate(i)
            candidates.append({
                'id': candidate_data[0],
                'name': candidate_data[1],
                'votes': candidate_data[2]
            })
            
        return candidates