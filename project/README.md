InstaBot: Full-Stack Instagram Automation & Analytics Tool

<!-- TODO: Replace this placeholder with a high-quality screenshot of the project dashboard. -->

InstaBot is a full-stack web application built with Python and Flask, designed to automate Instagram tasks and perform user account analysis. It features a user-friendly web interface, making it accessible even for non-technical users.

This project goes beyond a simple script by incorporating advanced concepts, including a distinct frontend and backend, multiple database integrations, and a robust background automation engine.

✨ Key Features

Comprehensive Web Interface: Eliminates the need for command-line interaction, with all features managed through a clean and intuitive dashboard.

Secure User Login: Implemented a secure authentication system using Flask's session management to protect user credentials and data.

Dashboard Analytics: Displays a real-time count of followers and following for the logged-in user, providing an at-a-glance overview.

Multi-Database Integration:

SQLite: Stores daily snapshots of user data for historical tracking and analysis.

MySQL: Manages a queue of user profiles from an online source for automated processing.

Powerful Automation Engine:

Automatically fetches unprocessed profiles from the MySQL database queue.

Implements a 1-minute delay between processing each profile to respect rate limits and prevent account blocking.

Marks processed profiles to avoid redundant executions and ensure efficiency.

Displays all fetched data in real-time on the dashboard for live monitoring.

Core Instagram Tools:

Check the follow status of any user (e.g., if they follow you back).

Unfollow users who don't follow you back with a single click.

Follow multiple users from a provided list.

Check the follow status of a target user across multiple accounts.

🛠️ Tech Stack

Backend: Python, Flask

Databases: MySQL, SQLite

Frontend: HTML, CSS, Bootstrap

Instagram Interaction: instagrapi library

Version Control: Git, GitHub

🚀 Getting Started: Setup and Installation

Follow the steps below to set up and run this project on your local machine.

Prerequisites

Python 3.8+

pip (Python package installer)

A running MySQL Server instance (e.g., via XAMPP, WAMP, or a standalone installation)

1. Clone the Repository

git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
cd your-repository-name


2. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate


3. Install Dependencies

Install all the required libraries from the requirements.txt file.
(Note: If a requirements.txt file is not present, you can create one using pip freeze > requirements.txt after installing the packages manually.)

pip install -r requirements.txt


4. Set Up the MySQL Database

Create a new database named iglinks in your MySQL server.

Import the provided .sql data file (e.g., links.sql) into this newly created database.

5. Configure Your Credentials

Before running the application, you must configure your credentials in the source code.

In tracker.py:
Add your MySQL database password to the MYSQL_CONFIG dictionary.

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_MYSQL_PASSWORD", // Add your password here
    "database": "iglinks"
}


In app.py:
Set a strong, unique secret_key for Flask session management.

app.secret_key = 'generate-a-new-random-secret-key' // Replace this


6. Run the Application

You are now ready to launch the web application.

python app.py


Open your web browser and navigate to http://127.0.0.1:5000.

💡 How to Use

Login: Use your Instagram credentials to log in through the web interface.

Dashboard: View a summary of your account's analytics.

Run Automation: Click the "Start Automation Task" button to begin processing profiles from the MySQL queue. Monitor the terminal for live progress updates.

Use Other Tools: Utilize the other tools available on the dashboard, such as Unfollow, Follow, and Status Check.

⚠️ Disclaimer

This project is intended for educational purposes only. Automating interactions on Instagram may violate their Terms of Service. Use this tool at your own risk. The developer is not responsible for any account blocking or banning that may occur as a result of using this software.
