# tracker.py 

import os
import sqlite3
import json
import time
import requests
import mysql.connector
from instagrapi import Client
from datetime import datetime

# --- Configuration ---

# 1. Local Database for storing user data snapshots
LOCAL_DATABASE = 'instabot_data.db'

# 2. MySQL Database Configuration 
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # paste your mysql password if it is their..
    "database": "" #  .sql file ka database name hai
}

# --- Database Initialization ---

def init_local_db():
    """Local SQLite database ko initialize karta hai."""
    db = sqlite3.connect(LOCAL_DATABASE)
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            followers_data TEXT,
            following_data TEXT,
            UNIQUE(username, snapshot_date)
        );
    ''')
    db.commit()
    db.close()
    print(f"Local SQLite DB '{LOCAL_DATABASE}' is ready.")

def get_mysql_connection():
    """MySQL database se connection banata hai."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print(" Successfully connected to MySQL database.")
        return conn
    except mysql.connector.Error as err:
        print(f" MySQL Connection Error: {err}")
        return None

# --- Core Instagram Logic ---

def save_snapshot_for_user(cl_client, target_username):
    """
    Ek specific user ka followers aur following data fetch karke local DB mein save karta hai.
    """
    try:
        print(f"Fetching data for '{target_username}'...")
        user_id = cl_client.user_id_from_username(target_username)
        today = datetime.now().strftime('%Y-%m-%d')
        
        print("  -> Fetching followers list...")
        followers_dict = cl_client.user_followers(user_id)
        
        print("  -> Fetching following list...")
        following_dict = cl_client.user_following(user_id)

        followers_data = [{'pk': pk, 'username': user.username, 'full_name': user.full_name} for pk, user in followers_dict.items()]
        following_data = [{'pk': pk, 'username': user.username, 'full_name': user.full_name} for pk, user in following_dict.items()]

        db = sqlite3.connect(LOCAL_DATABASE)
        cursor = db.cursor()

        print(f"  -> Saving snapshot for '{target_username}' to local DB...")
        cursor.execute(
            'INSERT OR REPLACE INTO snapshots (username, snapshot_date, followers_data, following_data) VALUES (?, ?, ?, ?)',
            (target_username, today, json.dumps(followers_data), json.dumps(following_data))
        )
        db.commit()
        db.close()
        print(f" Successfully saved snapshot for '{target_username}'.")
        return True

    except Exception as e:
        print(f" An error occurred while processing {target_username}: {e}")
        return False

# --- Main Automation Function () ---

def process_links_from_sql(insta_username, insta_password):
    """
    MySQL se links process karta hai, data save karta hai, 1 min wait karta hai, aur flag update karta hai.
    """
    # Instagram me login karo
    cl = Client()
    try:
        cl.login(insta_username, insta_password)
        print(f" Logged into Instagram as {insta_username} for the automation task.")
    except Exception as e:
        print(f" Instagram login failed: {e}")
        return

    # MySQL se connect
    conn = get_mysql_connection()
    if not conn:
        return
        
    cursor = conn.cursor(dictionary=True)

    try:
        # Step 1: Check karo ki 'processed' column hai ya nahi, agar nahi to banao
        print("Checking 'links' table structure...")
        cursor.execute("ALTER TABLE links ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT 0;")
        conn.commit()
        print("✅ 'processed' column ensured in 'links' table.")

        # Step 2: Sirf unprocessed links (processed = 0) fetch karo
        cursor.execute("SELECT * FROM links WHERE processed = 0")
        links_to_process = cursor.fetchall()
        
        if not links_to_process:
            print("✅ No new links to process. Everything is up to date.")
            return

        print(f"Found {len(links_to_process)} new links to process.")

        # Step 3: Har link ko process karo
        for link_row in links_to_process:
            url = link_row["url"]
            link_id = link_row["id"]
            target_username = url.split("instagram.com/")[-1].strip("/")

            print(f"\n▶ Processing URL: {url} (Username: {target_username})")
            
            # Instagram profile data fetch karke save karo
            success = save_snapshot_for_user(cl, target_username)

            if success:
                # Agar data save ho gaya to 'processed' flag ko 1 set karo
                print(f"  -> Marking link ID {link_id} as processed.")
                cursor.execute("UPDATE links SET processed = 1 WHERE id = %s", (link_id,))
                conn.commit()
            else:
                print(f"  -> Skipping 'processed' mark for link ID {link_id} due to an error.")

            # Step 4: Agle link se pehle 60 seconds ruko
            print("⏳ Pausing for 60 seconds before processing the next link...")
            time.sleep(60)

    except Exception as e:
        print(f"❌ A critical error occurred during the SQL link processing: {e}")
    finally:
        cursor.close()
        conn.close()
        print("\n✅ Automation task finished.")


if __name__ == '__main__':
    # Yeh script direct run karne ke liye hai 
    INSTA_USERNAME = ""  # Apna username yahan daalo
    INSTA_PASSWORD = ""  # Apna password yahan daalo

    if INSTA_USERNAME == "your_username" or INSTA_PASSWORD == "your_password":
        print(" Please set your Instagram credentials in the tracker.py file before running.")
    else:
        init_local_db()
        process_links_from_sql(INSTA_USERNAME, INSTA_PASSWORD)