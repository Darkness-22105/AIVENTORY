from pymongo import MongoClient

# MongoDB connection string (update if needed)
MONGO_URI = "mongodb+srv://aryanzeal22105:19DKatRulmvelMCN@shadow.giscmli.mongodb.net/inventory_management?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['inventory_management']
products = db['products']

# New sample data
sample_products = [
    {"name": "Wireless Mouse", "category": "Electronics", "price": 1200, "stock": 40},
    {"name": "Denim Jeans", "category": "Clothing", "price": 1500, "stock": 25},
    {"name": "Organic Honey", "category": "Food", "price": 450, "stock": 60},
    {"name": "Notebook", "category": "Books", "price": 200, "stock": 100},
    {"name": "Bluetooth Speaker", "category": "Electronics", "price": 3200, "stock": 12},
    {"name": "Running Shoes", "category": "Clothing", "price": 3500, "stock": 18},
    {"name": "Dark Chocolate", "category": "Food", "price": 250, "stock": 80},
    {"name": "Cookbook", "category": "Books", "price": 600, "stock": 30},
    {"name": "Smartwatch", "category": "Electronics", "price": 7000, "stock": 7},
    {"name": "Jacket", "category": "Clothing", "price": 2200, "stock": 10}
]

# Optional: Clear existing products
products.delete_many({})

# Insert new sample products
products.insert_many(sample_products)

print("Sample products inserted successfully!") 