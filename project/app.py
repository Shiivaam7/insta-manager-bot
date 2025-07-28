# project/app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, TwoFactorRequired
import pandas as pd
import io
import os
from datetime import timedelta
import time

app = Flask(__name__)
# It's crucial to set a secret key for session management.
# In a real application, use a more secure, randomly generated key
# and store it as an environment variable.
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30) # Keep session for 30 mins

# Helper function to get the client from session
def get_client():
    """
    Retrieves the Instagram client from the session.
    If client state is not in session, returns None.
    """
    if 'client_state' not in session:
        return None
    
    cl = Client()
    try:
        # FIXED: Use set_settings to load the session state from the dictionary
        cl.set_settings(session['client_state'])
        cl.login(session['username'], session['password'])
        return cl
    except (LoginRequired, BadPassword):
        # If credentials fail, clear the session
        session.clear()
        flash('Your session expired or credentials changed. Please log in again.', 'danger')
        return None
    except Exception as e:
        session.clear()
        flash(f'An unexpected error occurred: {e}', 'danger')
        return None


@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Handles the user login. On a POST request, it attempts to log in to Instagram.
    On success, it saves the client state to the session and redirects to the dashboard.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return redirect(url_for('login'))

        cl = Client()
        try:
            cl.login(username, password)
            # Store credentials and client state in session
            session.permanent = True
            session['username'] = username
            session['password'] = password
            # FIXED: Use get_settings() which returns a dictionary to store in the session
            session['client_state'] = cl.get_settings()
            
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        except BadPassword:
            flash('Incorrect password. Please try again.', 'danger')
        except TwoFactorRequired:
            flash('Two-factor authentication is enabled. This app does not support it.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """
    Displays the main dashboard. If the user is not logged in,
    it redirects them to the login page.
    """
    if 'client_state' not in session:
        flash('You must be logged in to view the dashboard.', 'warning')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session.get('username'))


@app.route('/logout')
def logout():
    """
    Clears the session to log the user out.
    """
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


def get_non_followers(cl):
    """
    Helper function to fetch users who do not follow you back.
    """
    user_id = cl.user_id_from_username(session['username'])
    following = cl.user_following(user_id)
    followers = cl.user_followers(user_id)
    
    following_pks = set(following.keys())
    followers_pks = set(followers.keys())
    
    non_followers_pks = following_pks - followers_pks
    
    non_followers = {pk: following[pk] for pk in non_followers_pks}
    return non_followers


@app.route('/unfollow_non_followers', methods=['POST'])
def unfollow_non_followers():
    """
    Unfollows a specified number of users who do not follow the logged-in user back.
    """
    cl = get_client()
    if not cl:
        return redirect(url_for('login'))

    unfollow_limit_str = request.form.get('unfollow_count')

    # Validate input
    try:
        unfollow_limit = int(unfollow_limit_str)
        if unfollow_limit <= 0:
            flash('Please enter a number greater than 0.', 'warning')
            return redirect(url_for('dashboard'))
    except (ValueError, TypeError):
        flash('Invalid number provided. Please enter a valid number.', 'warning')
        return redirect(url_for('dashboard'))

    try:
        non_followers = get_non_followers(cl)
        if not non_followers:
            flash('No non-followers to unfollow. Great!', 'success')
            return redirect(url_for('dashboard'))

        # Get the list of user IDs to unfollow
        user_ids_to_unfollow = list(non_followers.keys())
        
        # Take only the number of users specified by the limit
        actual_unfollow_list = user_ids_to_unfollow[:unfollow_limit]

        if not actual_unfollow_list:
            flash('Could not find any non-followers to unfollow (maybe you already unfollowed them all).', 'info')
            return redirect(url_for('dashboard'))

        count = 0
        for user_id in actual_unfollow_list:
            cl.user_unfollow(user_id)
            count += 1
            # Add a delay to avoid being rate-limited by Instagram
            time.sleep(1) 

        flash(f'Successfully unfollowed {count} users.', 'success')
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/follow_users', methods=['POST'])
def follow_users():
    """
    Follows a list of users provided in a textarea.
    """
    cl = get_client()
    if not cl:
        return redirect(url_for('login'))

    usernames_to_follow = request.form.get('usernames')
    if not usernames_to_follow:
        flash('Please provide a list of usernames to follow.', 'warning')
        return redirect(url_for('dashboard'))

    # Split by newlines, commas, or spaces and filter out empty strings
    user_list = [u.strip() for u in usernames_to_follow.replace(',', ' ').replace('\n', ' ').split(' ') if u.strip()]

    if not user_list:
        flash('The provided list is empty.', 'warning')
        return redirect(url_for('dashboard'))

    followed_count = 0
    errors = []
    for username in user_list:
        try:
            user_id = cl.user_id_from_username(username)
            cl.user_follow(user_id)
            followed_count += 1
            time.sleep(1)
        except Exception as e:
            errors.append(f"Could not follow {username}: {e}")

    flash(f'Successfully followed {followed_count} users.', 'success')
    if errors:
        for error in errors:
            flash(error, 'danger')

    return redirect(url_for('dashboard'))


@app.route('/export_csv', methods=['POST'])
def export_csv():
    """
    Exports a CSV file of users who do not follow you back.
    """
    cl = get_client()
    if not cl:
        return redirect(url_for('login'))

    try:
        non_followers = get_non_followers(cl)
        if not non_followers:
            flash('You have no non-followers to export.', 'info')
            return redirect(url_for('dashboard'))
        
        # Prepare data for pandas DataFrame
        non_followers_data = [
            {'username': user.username, 'full_name': user.full_name} 
            for user in non_followers.values()
        ]
        
        df = pd.DataFrame(non_followers_data)
        
        # Create an in-memory CSV file
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=non_followers.csv"}
        )

    except Exception as e:
        flash(f'An error occurred while exporting: {e}', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # For local development. For production, use a WSGI server like Gunicorn.
    app.run(debug=True)
