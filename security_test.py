import sqlite3

def login(username, password):
    # BUG 1: Hardcoded Credential
    secret_key = "ADMIN_12345" 
    
    # BUG 2: SQL Injection risk
    db = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE user = '{username}'" 
    db.execute(query)
