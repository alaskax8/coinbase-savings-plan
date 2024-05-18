from enum import Enum
import uuid
from argparse import ArgumentParser
import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient

load_dotenv()

API_KEY = os.getenv('COINBASE_API_KEY')
API_SECRET = os.getenv('COINBASE_API_SECRET')

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

class Side(Enum):
    BUY = 1
    SELL = 0

class Method(Enum):
    POST = "POST"
    GET = "GET"

def generate_client_order_id():
    return str(uuid.uuid4())

def place_order(product: str, side: Side, amount: float):
    order = client.market_order_buy(client_order_id=generate_client_order_id(), product_id=product, quote_size=str(amount))  
    success = order['success']
    if success is True:
        order_id = order.get('success_response').get('order_id')
    else:
        order_id = order['error_response']
    return order['success'], order_id


def show_balances():
    accounts = client.get_accounts()['accounts']
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
    