# app.py (Final Integrated Version with Online Data Display)

from flask import Flask, render_template, request, flash, Response, redirect, url_for, session
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, UserNotFound
import sqlite3
import json
import pandas as pd
import io
import time
from datetime import timedelta
import random
import threading

from tracker import process_links_from_sql

app = Flask(__name__)

app.secret_key = 'sdhnubsdfbvjcxhbds#' 
app.permanent_session_lifetime = timedelta(minutes=60)
DATABASE = 'instabot_data.db'

# --- Helper Functions ---
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def get_client():
    if 'client_state' not in session: return None
    cl = Client()
    try:
        cl.set_settings(session['client_state'])
        cl.get_timeline_feed() 
        return cl
    except LoginRequired:
        session.clear()
        flash('Your session expired. Please log in again.', 'danger')
        return None
    except Exception as e:
        print(f"Error validating client session: {e}")
        return cl

# --- Main Routes ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return redirect(url_for('login'))
        
        cl = Client()
        try:
            cl.login(username, password)
            session.permanent = True
            session['username'] = username
            session['password_temp'] = password # Temporary store for automation task
            session['client_state'] = cl.get_settings()
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'An error occurred during login: {e}', 'danger')
        return redirect(url_for('login'))
    
    if 'client_state' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'client_state' not in session:
        return redirect(url_for('login'))

    db = get_db()
    
    # 1. Logged-in user ka data
    follower_count, following_count, last_updated = 'N/A', 'N/A', 'Never'
    try:
        latest_snapshot = db.execute(
            'SELECT * FROM snapshots WHERE username = ? ORDER BY snapshot_date DESC LIMIT 1', 
            (session.get('username'),)
        ).fetchone()
        if latest_snapshot:
            follower_count = len(json.loads(latest_snapshot['followers_data']))
            following_count = len(json.loads(latest_snapshot['following_data']))
            last_updated = latest_snapshot['snapshot_date']
    except Exception as e:
        flash(f"Could not read your personal data: {e}", "danger")

    
    processed_users_data = []
    try:
        
        all_snapshots = db.execute('''
            SELECT s1.* FROM snapshots s1
            LEFT JOIN snapshots s2 ON (s1.username = s2.username AND s1.snapshot_date < s2.snapshot_date)
            WHERE s2.id IS NULL AND s1.username != ?
        ''', (session.get('username'),)).fetchall()

        for snapshot in all_snapshots:
            processed_users_data.append({
                'username': snapshot['username'],
                'followers': len(json.loads(snapshot['followers_data'])),
                'following': len(json.loads(snapshot['following_data'])),
                'date': snapshot['snapshot_date']
            })
    except Exception as e:
        flash(f"Could not read processed user data from the database: {e}", "danger")
    finally:
        db.close()


    return render_template('dashboard.html', 
                           username=session.get('username'),
                           follower_count=follower_count, 
                           following_count=following_count, 
                           last_updated=last_updated,
                           processed_users=processed_users_data) #

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ---  ---
@app.route('/run_automation', methods=['POST'])
def run_automation():
    if 'username' not in session or 'password_temp' not in session:
        flash("Session expired. Please log in again to start the task.", "danger")
        return redirect(url_for('login'))

    insta_username = session['username']
    insta_password = session['password_temp']

 
    thread = threading.Thread(target=process_links_from_sql, args=(insta_username, insta_password))
    thread.start()
    
    flash("✅ Automation task has started in the background. Check the console/terminal for progress. The page will show results once data is fetched.", "success")
    return redirect(url_for('dashboard'))


@app.route('/check_status', methods=['POST'])
def check_status():
    cl = get_client()
    if not cl: return redirect(url_for('login'))
    target_username = request.form.get('target_username', '').strip()
    check_type = request.form.get('check_type', '')
    try:
        target_user_info = cl.user_info_by_username(target_username)
        target_user_id = target_user_info.pk
        
        if check_type == 'follower':
            my_followers = cl.user_followers(cl.user_id)
            if target_user_id in my_followers: flash(f"✅ Yes, <strong>{target_username}</strong> follows you.", "success")
            else: flash(f"❌ No, <strong>{target_username}</strong> does not follow you.", "info")
        elif check_type == 'following':
            my_following = cl.user_following(cl.user_id)
            if target_user_id in my_following: flash(f"✅ Yes, you follow <strong>{target_username}</strong>.", "success")
            else: flash(f"❌ No, you do not follow <strong>{target_username}</strong>.", "info")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
    return redirect(url_for('dashboard'))

@app.route('/check_multi_account_status', methods=['POST'])
def check_multi_account_status():
    target_username = request.form.get('target_username', '').strip()
    my_accounts_str = request.form.get('my_accounts', '').strip()
    password = request.form.get('password', '')

    if not all([target_username, my_accounts_str, password]):
        flash("Please fill all fields for the Multi-Account Check.", "warning")
        return redirect(url_for('dashboard'))

    my_accounts_list = [acc.strip() for acc in my_accounts_str.split(',')]
    
    for account in my_accounts_list:
        if not account: continue
        cl_temp = Client()
        try:
            cl_temp.login(account, password)
            target_user_info = cl_temp.user_info_by_username(target_username)
            target_user_id = target_user_info.pk
            my_followers = cl_temp.user_followers(cl_temp.user_id)
            if target_user_id in my_followers:
                flash(f" <strong>{target_username}</strong> FOLLOWS <strong>{account}</strong>.", "success")
            else:
                flash(f" <strong>{target_username}</strong> does NOT follow <strong>{account}</strong>.", "info")
            time.sleep(2) 
        except UserNotFound:
            flash(f"User '{target_username}' not found. Please check the username.", "danger")
            break
        except Exception as e:
            flash(f"Could not check for account <strong>{account}</strong>. Error: {e}", "danger")
            
    return redirect(url_for('dashboard'))

@app.route('/export_latest', methods=['POST'])
def export_latest():
    db = get_db()
    try:
        latest_snapshot = db.execute('SELECT * FROM snapshots WHERE username = ? ORDER BY snapshot_date DESC LIMIT 1', (session.get('username'),)).fetchone()
        if not latest_snapshot:
            flash("No data snapshot found to export.", "warning")
            return redirect(url_for('dashboard'))

        followers_data = json.loads(latest_snapshot['followers_data'])
        following_data = json.loads(latest_snapshot['following_data'])
        db.close()

        followers_df = pd.DataFrame(followers_data)
        following_df = pd.DataFrame(following_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            followers_df.to_excel(writer, sheet_name='Followers', index=False)
            following_df.to_excel(writer, sheet_name='Following', index=False)
        output.seek(0)

        return Response(output,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f"attachment;filename=instagram_snapshot_{latest_snapshot['snapshot_date']}.xlsx"})
    except Exception as e:
        db.close()
        flash(f"An error occurred during export: {e}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/unfollow_non_followers', methods=['POST'])
def unfollow_non_followers():
    cl = get_client()
    if not cl: return redirect(url_for('login'))
    try:
        unfollow_limit = int(request.form.get('unfollow_count'))
        if unfollow_limit <= 0:
            flash('Please enter a valid number greater than 0.', 'warning')
            return redirect(url_for('dashboard'))
        flash("Checking who doesn't follow you back... This may take a while.", "info")
        non_followers_pks = list(set(cl.user_following(cl.user_id).keys()) - set(cl.user_followers(cl.user_id).keys()))
        if not non_followers_pks:
            flash("Great news! Everyone you follow also follows you back.", "success")
            return redirect(url_for('dashboard'))
        unfollowed_count = 0
        for user_id in non_followers_pks[:unfollow_limit]:
            cl.user_unfollow(user_id)
            unfollowed_count += 1
            time.sleep(random.uniform(5, 15))
        flash(f"Successfully unfollowed {unfollowed_count} users.", "success")
    except (ValueError, TypeError):
        flash('Invalid number provided.', 'warning')
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
    return redirect(url_for('dashboard'))

@app.route('/follow_users', methods=['POST'])
def follow_users():
    cl = get_client()
    if not cl: return redirect(url_for('login'))
    users_to_follow_str = request.form.get('usernames', '').strip()
    if not users_to_follow_str:
        flash("Please provide a list of usernames to follow.", "warning")
        return redirect(url_for('dashboard'))
    usernames = [u.strip() for u in users_to_follow_str.replace(',', '\n').split('\n') if u.strip()]
    followed_count = 0
    errors = []
    for username in usernames:
        try:
            user_id = cl.user_id_from_username(username)
            cl.user_follow(user_id)
            followed_count += 1
            flash(f"Successfully followed {username}.", "success")
            time.sleep(random.uniform(5, 15))
        except UserNotFound:
            errors.append(f"User '{username}' not found.")
        except Exception as e:
            errors.append(f"Could not follow {username}: {e}")
    if errors:
        for error in errors: flash(error, "danger")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
