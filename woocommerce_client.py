import requests
import polars as pl
import datetime
import random
import streamlit as st
from typing import Dict, List, Tuple, Any, Optional

class WooCommerceClient:
    """
    A robust client to interface with the WooCommerce REST API and process data using Polars.
    """
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str, verify_ssl: bool = True):
        self.store_url = store_url.strip().rstrip('/')
        self.consumer_key = consumer_key.strip()
        self.consumer_secret = consumer_secret.strip()
        self.verify_ssl = verify_ssl
        self.auth = (self.consumer_key, self.consumer_secret)
        self.api_base_url = f"{self.store_url}/wp-json/wc/v3"

    def test_connection(self) -> Tuple[bool, str]:
        """
        Verify credentials by querying the system status or a small batch of products.
        """
        try:
            url = f"{self.api_base_url}/system_status"
            # Attempt system status first
            response = requests.get(url, auth=self.auth, verify=self.verify_ssl, timeout=10)
            if response.status_code == 200:
                return True, "Successfully connected to WooCommerce REST API."
            
            # Fallback to products if system status endpoint is restricted
            url = f"{self.api_base_url}/products"
            response = requests.get(url, auth=self.auth, params={"per_page": 1}, verify=self.verify_ssl, timeout=10)
            if response.status_code == 200:
                return True, "Successfully connected to WooCommerce REST API (Products endpoint)."
            else:
                return False, f"API returned status code {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def _fetch_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Fetches all pages of data from a given WooCommerce API endpoint.
        """
        if params is None:
            params = {}
        
        params = params.copy()
        params["per_page"] = 100
        params["page"] = 1
        
        all_data = []
        url = f"{self.api_base_url}/{endpoint}"
        
        while True:
            response = requests.get(url, auth=self.auth, params=params, verify=self.verify_ssl, timeout=20)
            if response.status_code != 200:
                raise Exception(f"WooCommerce API error fetching {endpoint} (page {params['page']}): {response.status_code} - {response.text}")
            
            data = response.json()
            if not data:
                break
                
            all_data.extend(data)
            
            # Check pagination headers
            total_pages_header = response.headers.get("X-WP-TotalPages") or response.headers.get("x-wp-totalpages")
            if total_pages_header:
                total_pages = int(total_pages_header)
                if params["page"] >= total_pages:
                    break
            else:
                # If header is missing, we check if we received less than 100 items
                if len(data) < 100:
                    break
            
            params["page"] += 1
            
        return all_data

    def get_orders(self, date_range: Optional[Tuple[datetime.date, datetime.date]] = None) -> pl.DataFrame:
        """
        Retrieves orders and parses them into a Polars DataFrame.
        """
        params = {}
        if date_range:
            start_date, end_date = date_range
            # WooCommerce expects ISO 8601 strings
            params["after"] = f"{start_date}T00:00:00"
            params["before"] = f"{end_date}T23:59:59"

        orders_raw = self._fetch_all("orders", params)
        if not orders_raw:
            return self._empty_orders_df()
        
        return self._process_orders_to_polars(orders_raw)

    def get_products(self) -> pl.DataFrame:
        """
        Retrieves all products and parses them into a Polars DataFrame.
        """
        products_raw = self._fetch_all("products")
        if not products_raw:
            return self._empty_products_df()
            
        return self._process_products_to_polars(products_raw)

    def get_customers(self) -> pl.DataFrame:
        """
        Retrieves all customers and parses them into a Polars DataFrame.
        """
        customers_raw = self._fetch_all("customers")
        if not customers_raw:
            return self._empty_customers_df()
            
        return self._process_customers_to_polars(customers_raw)

    def _process_orders_to_polars(self, raw_orders: List[Dict[str, Any]]) -> pl.DataFrame:
        """
        Processes WooCommerce orders raw JSON list into an optimized Polars DataFrame.
        """
        processed_orders = []
        for o in raw_orders:
            billing = o.get("billing", {})
            # Flatten essential order data
            order_record = {
                "order_id": int(o.get("id", 0)),
                "status": o.get("status", "unknown"),
                "currency": o.get("currency", "USD"),
                "date_created": o.get("date_created"), # String format, we will convert to datetime in polars
                "total": float(o.get("total", 0.0) or 0.0),
                "discount_total": float(o.get("discount_total", 0.0) or 0.0),
                "shipping_total": float(o.get("shipping_total", 0.0) or 0.0),
                "total_tax": float(o.get("total_tax", 0.0) or 0.0),
                "customer_id": int(o.get("customer_id", 0)),
                "customer_email": billing.get("email", ""),
                "customer_name": f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
                "city": billing.get("city", "Unknown"),
                "state": billing.get("state", "Unknown"),
                "country": billing.get("country", "Unknown"),
                "items_count": sum(int(item.get("quantity", 0)) for item in o.get("line_items", [])),
                "item_names": ", ".join([item.get("name", "") for item in o.get("line_items", [])])
            }
            
            # Sub-records for line items (could be useful for deep analysis)
            # For simplicity, we also store flattened list of items in session state if needed
            processed_orders.append(order_record)
            
        df = pl.DataFrame(processed_orders)
        
        # Cast types properly
        if "date_created" in df.columns:
            # WooCommerce date format is typically "YYYY-MM-DDTHH:MM:SS" or similar
            df = df.with_columns([
                pl.col("date_created").str.to_datetime().alias("datetime_created")
            ])
            df = df.with_columns([
                pl.col("datetime_created").dt.date().alias("date")
            ])
            
        return df

    def _process_products_to_polars(self, raw_products: List[Dict[str, Any]]) -> pl.DataFrame:
        """
        Processes WooCommerce products raw JSON list into a Polars DataFrame.
        """
        processed_products = []
        for p in raw_products:
            categories = [cat.get("name", "") for cat in p.get("categories", [])]
            primary_category = categories[0] if categories else "Uncategorized"
            
            product_record = {
                "product_id": int(p.get("id", 0)),
                "name": p.get("name", ""),
                "price": float(p.get("price", 0.0) or 0.0),
                "regular_price": float(p.get("regular_price", 0.0) or 0.0),
                "sale_price": float(p.get("sale_price", 0.0) or 0.0),
                "stock_quantity": p.get("stock_quantity"), # Can be None if unmanaged
                "stock_status": p.get("stock_status", "instock"),
                "category": primary_category,
                "all_categories": ", ".join(categories),
                "total_sales": int(p.get("total_sales", 0) or 0)
            }
            processed_products.append(product_record)
            
        df = pl.DataFrame(processed_products)
        # Handle None in stock quantity by filling with 0 or a placeholder
        df = df.with_columns([
            pl.col("stock_quantity").fill_null(0).cast(pl.Int64)
        ])
        return df

    def _process_customers_to_polars(self, raw_customers: List[Dict[str, Any]]) -> pl.DataFrame:
        """
        Processes WooCommerce customers raw JSON list into a Polars DataFrame.
        """
        processed_customers = []
        for c in raw_customers:
            customer_record = {
                "customer_id": int(c.get("id", 0)),
                "email": c.get("email", ""),
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "orders_count": int(c.get("orders_count", 0) or 0),
                "total_spent": float(c.get("total_spent", 0.0) or 0.0),
                "username": c.get("username", "")
            }
            processed_customers.append(customer_record)
            
        return pl.DataFrame(processed_customers)

    def _empty_orders_df(self) -> pl.DataFrame:
        schema = {
            "order_id": pl.Int64, "status": pl.Utf8, "currency": pl.Utf8, "date_created": pl.Utf8,
            "total": pl.Float64, "discount_total": pl.Float64, "shipping_total": pl.Float64, "total_tax": pl.Float64,
            "customer_id": pl.Int64, "customer_email": pl.Utf8, "customer_name": pl.Utf8, "city": pl.Utf8,
            "state": pl.Utf8, "country": pl.Utf8, "items_count": pl.Int64, "item_names": pl.Utf8,
            "datetime_created": pl.Datetime, "date": pl.Date
        }
        return pl.DataFrame(schema=schema)

    def _empty_products_df(self) -> pl.DataFrame:
        schema = {
            "product_id": pl.Int64, "name": pl.Utf8, "price": pl.Float64, "regular_price": pl.Float64,
            "sale_price": pl.Float64, "stock_quantity": pl.Int64, "stock_status": pl.Utf8,
            "category": pl.Utf8, "all_categories": pl.Utf8, "total_sales": pl.Int64
        }
        return pl.DataFrame(schema=schema)

    def _empty_customers_df(self) -> pl.DataFrame:
        schema = {
            "customer_id": pl.Int64, "email": pl.Utf8, "first_name": pl.Utf8, "last_name": pl.Utf8,
            "orders_count": pl.Int64, "total_spent": pl.Float64, "username": pl.Utf8
        }
        return pl.DataFrame(schema=schema)


def generate_mock_data(num_orders: int = 450, num_products: int = 15, num_customers: int = 120) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """
    Generates synthetic, highly realistic business data for WooCommerce Demo Mode.
    Produces Polars DataFrames matching the exact WooCommerce schema.
    """
    # 1. Generate Products
    categories = ["Electronics", "Apparel", "Home & Living", "Books", "Fitness", "Beauty"]
    product_names = {
        "Electronics": ["Pro Wireless Headphones", "Smart Fitness Watch", "Mechanical RGB Keyboard", "Portable USB-C SSD", "Noise Cancelling Earbuds"],
        "Apparel": ["Premium Cotton Hoodie", "Slim Fit Stretch Chinos", "Activewear Performance Tee", "Waterproof Windbreaker Jacket"],
        "Home & Living": ["Ergonomic Desk Chair", "Minimalist Ceramic Vase", "Smart LED Desk Lamp", "Double-Walled Glass Set"],
        "Books": ["The Art of Coding", "Business Strategies for Scale", "Mindfulness & Productivity"],
        "Fitness": ["Adjustable Dumbbell Set", "Eco-Friendly Yoga Mat", "Resistance Band Pack"],
        "Beauty": ["Organic Hydrating Serum", "Charcoal Detox Face Mask", "Essential Oil Diffuser"]
    }
    
    products_list = []
    pid_counter = 101
    
    # Flat list of names for drawing sales
    all_available_products = []
    
    for cat in categories:
        for name in product_names.get(cat, [f"{cat} Item"]):
            price = round(random.uniform(15.0, 150.0), 2)
            if cat == "Electronics" or name == "Ergonomic Desk Chair":
                price = round(random.uniform(80.0, 350.0), 2)
            
            regular_price = price
            # 30% chance of being on sale
            on_sale = random.random() < 0.3
            sale_price = round(price * random.uniform(0.75, 0.95), 2) if on_sale else regular_price
            price_active = sale_price if on_sale else regular_price
            
            stock_qty = random.randint(0, 150)
            # some low stock and out of stock items
            if random.random() < 0.15:
                stock_qty = random.randint(0, 5)
                
            stock_status = "instock" if stock_qty > 0 else "outofstock"
            if stock_qty > 0 and stock_qty <= 10:
                stock_status = "onbackorder"
                
            prod = {
                "product_id": pid_counter,
                "name": name,
                "price": float(price_active),
                "regular_price": float(regular_price),
                "sale_price": float(sale_price),
                "stock_quantity": stock_qty,
                "stock_status": stock_status,
                "category": cat,
                "all_categories": cat,
                "total_sales": 0 # Will be updated dynamically based on orders generated
            }
            products_list.append(prod)
            all_available_products.append(prod)
            pid_counter += 1
            
    # 2. Generate Customers
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "San Francisco", "Seattle", "Miami"]
    states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA", "TX", "FL", "CA", "WA", "FL"]
    
    customers_list = []
    cid_counter = 1001
    
    for i in range(num_customers):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        email = f"{fname.lower()}.{lname.lower()}{random.randint(10,99)}@example.com"
        username = f"{fname.lower()}{random.randint(100,999)}"
        
        cust = {
            "customer_id": cid_counter,
            "email": email,
            "first_name": fname,
            "last_name": lname,
            "orders_count": 0, # Update based on generated orders
            "total_spent": 0.0, # Update based on generated orders
            "city": random.choice(cities),
            "state": "",
            "country": "US",
            "username": username
        }
        # align state with city
        city_idx = cities.index(cust["city"])
        cust["state"] = states[city_idx]
        
        customers_list.append(cust)
        cid_counter += 1
        
    # Guest customer id = 0
    
    # 3. Generate Orders
    orders_list = []
    order_id_counter = 5001
    
    # Create a timeframe: last 365 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    # Generate dates with weekend dips and seasonal trends (e.g. higher volume in November/December)
    date_pool = []
    current_date = start_date
    while current_date <= end_date:
        # Determine weight for this date
        weight = 1
        # Weekend dip (Saturday=5, Sunday=6)
        if current_date.weekday() in [5, 6]:
            weight = 0.7
        # Nov/Dec Holiday sales peak
        if current_date.month in [11, 12]:
            weight *= 1.8
        # Summer sales dip
        if current_date.month in [6, 7]:
            weight *= 0.8
            
        # Add date multiple times to represent probability weight
        num_sales_on_day = int(random.choices(
            [0, 1, 2, 3, 4, 5], 
            weights=[10, 20*weight, 30*weight, 25*weight, 10*weight, 5*weight]
        )[0])
        
        for _ in range(num_sales_on_day):
            date_pool.append(current_date)
        current_date += datetime.timedelta(days=1)
        
    # Limit number of orders to pool or trim
    random.shuffle(date_pool)
    order_dates = date_pool[:num_orders]
    order_dates.sort() # Chronological orders
    
    # Pre-select active recurring customer distribution to make cohorts realistic
    # Let's say top 20% of customers place 50% of orders.
    vip_customers = customers_list[:int(num_customers * 0.2)]
    normal_customers = customers_list[int(num_customers * 0.2):]
    
    for o_date in order_dates:
        # Decide if guest or registered customer
        is_guest = random.random() < 0.15
        
        if is_guest:
            customer_id = 0
            cust_email = f"guest.{random.randint(10000, 99999)}@example.com"
            cust_name = "Guest Customer"
            city = random.choice(cities)
            city_idx = cities.index(city)
            state = states[city_idx]
            country = "US"
        else:
            # Select customer (biased towards VIPs)
            if random.random() < 0.5:
                cust = random.choice(vip_customers)
            else:
                cust = random.choice(normal_customers)
                
            customer_id = cust["customer_id"]
            cust_email = cust["email"]
            cust_name = f"{cust['first_name']} {cust['last_name']}"
            city = cust["city"]
            state = cust["state"]
            country = cust["country"]
            
        # Select items for this order (1 to 4 items)
        num_items = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
        selected_prods = random.sample(all_available_products, num_items)
        
        line_items = []
        subtotal = 0.0
        
        for item_prod in selected_prods:
            qty = random.choices([1, 2, 3], weights=[85, 12, 3])[0]
            item_total = item_prod["price"] * qty
            subtotal += item_total
            line_items.append({
                "id": random.randint(20000, 30000),
                "name": item_prod["name"],
                "product_id": item_prod["product_id"],
                "quantity": qty,
                "total": str(round(item_total, 2))
            })
            
            # Increment product sales count
            item_prod["total_sales"] += qty
            
        # Financial adjustments
        discount = 0.0
        if random.random() < 0.2: # 20% of orders have discount
            discount = round(subtotal * random.choices([0.1, 0.15, 0.2], weights=[50, 30, 20])[0], 2)
            
        shipping = round(random.choice([0.0, 5.99, 9.99, 14.99]), 2)
        tax = round((subtotal - discount) * 0.08, 2)
        total = round(subtotal - discount + shipping + tax, 2)
        
        # Order status (mostly completed, some processing, refunded or cancelled)
        status = random.choices(
            ["completed", "processing", "refunded", "cancelled"], 
            weights=[85, 8, 4, 3]
        )[0]
        
        # Update customer cumulative records
        if not is_guest:
            for cust in customers_list:
                if cust["customer_id"] == customer_id:
                    if status in ["completed", "processing"]:
                        cust["orders_count"] += 1
                        cust["total_spent"] = round(cust["total_spent"] + total, 2)
                    break
                    
        # Generate datetime with random hour/minute
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        dt_str = f"{o_date}T{hour:02d}:{minute:02d}:{second:02d}"
        
        order_record = {
            "order_id": order_id_counter,
            "status": status,
            "currency": "USD",
            "date_created": dt_str,
            "total": float(total),
            "discount_total": float(discount),
            "shipping_total": float(shipping),
            "total_tax": float(tax),
            "customer_id": customer_id,
            "customer_email": cust_email,
            "customer_name": cust_name,
            "city": city,
            "state": state,
            "country": country,
            "items_count": sum(item["quantity"] for item in line_items),
            "item_names": ", ".join(item["name"] for item in line_items)
        }
        
        orders_list.append(order_record)
        order_id_counter += 1
        
    # Convert lists to Polars DataFrames
    orders_df = pl.DataFrame(orders_list)
    products_df = pl.DataFrame(products_list)
    
    # Re-calculate customers counts to be accurate based on final completed/processing orders
    customers_df = pl.DataFrame(customers_list)
    
    # Cast date fields
    orders_df = orders_df.with_columns([
        pl.col("date_created").str.to_datetime().alias("datetime_created")
    ])
    orders_df = orders_df.with_columns([
        pl.col("datetime_created").dt.date().alias("date")
    ])
    
    return orders_df, products_df, customers_df


def load_woocommerce_data(date_range: Optional[Tuple[datetime.date, datetime.date]] = None, use_demo: bool = False) -> Dict[str, pl.DataFrame]:
    """
    Primary data loader function. Checks Streamlit secrets for credentials.
    If credentials exist and use_demo is False, connects to live WooCommerce.
    Otherwise, returns mock datasets. Results are packaged in a dictionary.
    """
    # Check if credentials exist in secrets
    has_credentials = False
    store_url = ""
    consumer_key = ""
    consumer_secret = ""
    
    if not use_demo:
        try:
            if "woocommerce" in st.secrets:
                store_url = st.secrets["woocommerce"].get("store_url", "")
                consumer_key = st.secrets["woocommerce"].get("consumer_key", "")
                consumer_secret = st.secrets["woocommerce"].get("consumer_secret", "")
                
                # Check that they aren't the placeholders
                if (store_url and store_url != "https://your-store.com" and
                    consumer_key and consumer_key != "ck_your_consumer_key_here" and
                    consumer_secret and consumer_secret != "cs_your_consumer_secret_here"):
                    has_credentials = True
        except Exception:
            # Secrets file doesn't exist or isn't structured correctly
            pass
            
    if has_credentials and not use_demo:
        try:
            client = WooCommerceClient(store_url, consumer_key, consumer_secret)
            
            # Retrieve data from API
            orders_df = client.get_orders(date_range)
            products_df = client.get_products()
            customers_df = client.get_customers()
            
            return {
                "orders": orders_df,
                "products": products_df,
                "customers": customers_df,
                "is_demo": False,
                "store_name": store_url.replace("https://", "").replace("http://", "").split("/")[0]
            }
        except Exception as e:
            # Log error and fall back to demo mode with warning
            st.sidebar.error(f"Live API Fetch Error: {str(e)}. Falling back to Demo Mode.")
            
    # Demo Mode fallback
    orders_df, products_df, customers_df = generate_mock_data()
    
    # Filter orders by date range if specified in Demo Mode
    if date_range:
        start_date, end_date = date_range
        orders_df = orders_df.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )
        
    return {
        "orders": orders_df,
        "products": products_df,
        "customers": customers_df,
        "is_demo": True,
        "store_name": "Demo Electronics & Lifestyle Store"
    }
