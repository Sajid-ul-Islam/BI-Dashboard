import tomllib
import requests
from woocommerce_client import WooCommerceClient

def test():
    try:
        with open(".streamlit/secrets.toml", "rb") as f:
            secrets = tomllib.load(f)
        wc = secrets["woocommerce"]
        url = wc["store_url"]
        ck = wc["consumer_key"]
        cs = wc["consumer_secret"]
        print(f"Testing WooCommerce API Connection...")
        print(f"URL: {url}")
        print(f"CK: {ck[:10]}...")
        print(f"CS: {cs[:10]}...")
        
        client = WooCommerceClient(url, ck, cs)
        success, msg = client.test_connection()
        print(f"Handshake success: {success}")
        print(f"Message: {msg}")
        
        # If handshake succeeded, try to fetch products or orders to see if pagination/fetching errors out
        if success:
            print("\nAttempting to fetch a small batch of products...")
            prods = client.get_products()
            print(f"Fetched {prods.height} products successfully.")
            
            print("\nAttempting to fetch a small batch of orders (last 30 days)...")
            import datetime
            today = datetime.date.today()
            date_range = (today - datetime.timedelta(days=30), today)
            orders = client.get_orders(date_range)
            print(f"Fetched {orders.height} orders successfully.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
