import jwt
from cryptography.hazmat.primitives import serialization
import time
import http.client
import json
from enum import Enum
import uuid
from argparse import ArgumentParser
import os
from dotenv import load_dotenv

load_dotenv()

KEY_NAME = os.getenv('COINBASE_API_KEY_NAME')
KEY_SECRET = os.getenv('COINBASE_API_KEY_SECRET')

REQUEST_HOST   = "api.coinbase.com"
REQUEST_PATH_ACCOUNTS   = "/api/v3/brokerage/accounts"
REQUEST_PATH_ORDERS   = "/api/v3/brokerage/orders"
SERVICE_NAME   = "retail_rest_api_proxy"

class Side(Enum):
    BUY = 1
    SELL = 0

class Method(Enum):
    POST = "POST"
    GET = "GET"

def generate_client_order_id():
    return str(uuid.uuid4())

def build_jwt(service, uri):
    private_key_bytes = KEY_SECRET.encode('utf-8')
    private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
    jwt_payload = {
        'sub': KEY_NAME,
        'iss': "coinbase-cloud",
        'nbf': int(time.time()),
        'exp': int(time.time()) + 60,
        'aud': [service],
        'uri': uri,
    }
    return jwt.encode(
            jwt_payload,
            private_key,
            algorithm='ES256',
            headers={'kid': KEY_NAME, 'nonce': str(int(time.time()))},
        )

def get_accounts(jwt_token: str):
    conn = http.client.HTTPSConnection("api.coinbase.com")
    headers = {
    'Content-Type': 'application/json',
    'Authorization': f"Bearer {jwt_token}",
    }
    conn.request("GET", "/api/v3/brokerage/accounts", '', headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8")).get('accounts')

def place_order(product: str, side: Side, amount: float):
    conn = http.client.HTTPSConnection("api.coinbase.com")
    payload = json.dumps({
    "product_id": product,
    "client_order_id": generate_client_order_id(),
    "side": side.name,
    "order_configuration": {
        "market_market_ioc": {
        "quote_size": str(amount)
        }
    }
    })
    headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {build_jwt(SERVICE_NAME, f"{Method.POST.value} {REQUEST_HOST}{REQUEST_PATH_ORDERS}")}',
    }
    conn.request("POST", "/api/v3/brokerage/orders", payload, headers)
    res = conn.getresponse()
    response_dict = json.loads(res.read())
    success = response_dict['success']
    if success is True:
        order_id = response_dict.get('success_response').get('order_id')
    else:
        order_id = response_dict['error_response']
    return success, order_id


def show_balances():
    accounts = get_accounts(jwt_token=build_jwt(SERVICE_NAME, f"{Method.GET.value} {REQUEST_HOST}{REQUEST_PATH_ACCOUNTS}"))
    for account in accounts:
        print(f"{account.get('currency')}: {account.get('available_balance').get('value')}")

def parse_arguments():
    parser = ArgumentParser(
                prog='CSP - Coinbase Savings Plan',
                description='Executes orders on coinbase',
                epilog='')
    parser.add_argument('--product', dest='product', required=True,
                    help='Specifies the product to place an order for. E.g. BTC-EUR')
    parser.add_argument('--side', dest='side', required=True,
                    help='Specifies the order type - BUY or SELL')
    parser.add_argument('--amount', dest='amount', required=True, type=float,
                    help='Specifies the amount for the order')
    parser.add_argument('--show-balances', dest='show_balances', default=True, type=bool,
                    help='Show the account balances before and after the order has been placed.')
    return parser.parse_args()



if __name__ == "__main__":
    assert KEY_NAME is not None, "Please set environment variable COINBASE_API_KEY_NAME. You can also put it into a '.env' file."
    assert KEY_SECRET is not None, "Please set environment variable COINBASE_API_KEY_SECRET. You can also put it into a '.env' file."

    args = parse_arguments()
    assert args.side in ['BUY', 'SELL'], "Side arguments should be BUY or SELL"
    assert args.amount > 0, "Amount needs to be greater than 0"

    if args.show_balances:
        print("--------------------------------------------BEFORE--------------------------------------------")
        show_balances()

    print(f"Placing order {args.side} {args.amount} for {args.product}")
    order_success, order_id = place_order(product=args.product, side=Side[args.side], amount=args.amount)

    if order_success:
        print(f"Successfully executed order with ID {order_id}")
    else:
        print(f"Failed to place order. ERROR: {order_id.get('error')} PREVIEW_FAILURE_REASON: {order_id.get('preview_failure_reason')}")

    if args.show_balances:
        print("--------------------------------------------AFTER--------------------------------------------")
        show_balances()
    