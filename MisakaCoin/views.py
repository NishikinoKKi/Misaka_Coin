from urllib.parse import urlparse
import requests
from django.http import HttpResponse

import hashlib
import json
from time import time
from uuid import uuid4

# 御坂网络 (Misaka Network) V2.0，去中心化的御坂网络！


class Blockchain(object):
    def __init__(self):
        self.chain = []  # 存储区块链
        self.current_transactions = []  # 存储交易
        self.new_block(previous_hash=1, proof=100)  # 创建新的区块
        self.nodes = set()  # 节点集合

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,  # 区块索引
            'timestamp': time(),  # 时间戳
            'transactions': self.current_transactions,  # 交易列表
            'proof': proof,  # 工作量证明
            'previous_hash': previous_hash or self.hash(self.chain[-1]),  # 上一个区块的Hash
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    '''
    标准区块结构：
    block = {
        'index': 1,
        'timestamp': 1506057125.900785,
        'transactions': [
            {
                'sender': "8527147fe1f5426f9dd545de4b27ee00",
                'recipient': "a77f5cdfa2934df3954a5c7c7da5df1f",
                'amount': 5,
            }
        ],
        'proof': 324984774000,
        'previous_hash': "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    }
    '''

    def new_transaction(self, sender, recipient, amount):  # 新的交易
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index']+1

    @staticmethod
    def hash(block):  # 产生区块Hash
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):  # 上一个区块
        return self.chain[-1]

    def proof_of_work(self, last_proof):  # 工作量证明
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):  # 挖矿
        guess = str(last_proof*proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:5] == "00000"

    def valid_chain(self, chain):  # 验证有效性
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(last_block)
            print(block)
            print("\n-----------\n")
            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get('http://'+str(node)+'/chain')

            if response.status_code == 200:
                length = json.loads(response)['length']
                chain = json.loads(response)['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()


def mine(request):
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    print(proof)
    blockchain.new_transaction(
         sender="0",
         recipient=node_identifier,
         amount=1,
     )
    if len(blockchain.chain) < 20002:
        block = blockchain.new_block(proof)
    else:
        return HttpResponse('The number of Misaka Coin is already enough')
    response = {
         'message': "New Misaka Coin Forged",
         'index': block['index'],
         'transactions': block['transactions'],
         'proof': block['proof'],
         'previous_hash': block['previous_hash'],
    }
    print(response)
    return HttpResponse(json.dumps(response))


def new_transaction(request):
    values = json.loads(request.body.decode('utf-8'))
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values'
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    print(index)
    response = {'message': 'Transaction will be added to Block %s'%index}
    return HttpResponse(json.dumps(response))


def full_chain(request):
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return HttpResponse(json.dumps(response))


def register_nodes(request):
    values = json.loads(request.body.decode('utf-8'))
    nodes = values.get('node')
    print(nodes)
    if nodes is None:
        return "Error: Please supply a valid list of nodes"
    for node in nodes:
        blockchain.register_node(node)
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return HttpResponse(json.dumps(response))


def consensus(request):
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return HttpResponse(json.dumps(response))