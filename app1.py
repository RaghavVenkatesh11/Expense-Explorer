import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import bcrypt

# Initialize database connection
conn = sqlite3.connect("expense_tracker1.db")
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    category TEXT,
                    date TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS budget_limits (
                    user_id INTEGER,
                    category TEXT,
                    "limit" REAL,
                    PRIMARY KEY(user_id, category),
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
conn.commit()

# Initialize session state if not set
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# User Authentication Functions
def register_user(username, password):
    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        st.success("User registered successfully!")
    except sqlite3.IntegrityError:
        st.error("Username already exists. Choose another.")

def check_password(stored_password, provided_password):
    # Check if the provided password matches the stored hashed password
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and check_password(user[2], password):  # user[2] is the stored hashed password
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.success("Login successful!")
    else:
        st.error("Incorrect username or password.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.info("You have been logged out.")

# Expense Tracker Class
class ExpenseTracker:
    def __init__(self, user_id, salary):
        self.user_id = user_id
        self.salary = salary
        self.budget_limits = self.load_budget_limits()

    def load_budget_limits(self):
        cursor.execute('SELECT category, "limit" FROM budget_limits WHERE user_id = ?', (self.user_id,))
        data = cursor.fetchall()
        return {category: limit for category, limit in data}

    def add_expense(self, amount, category, date):
        remaining_amount = self.salary - self.get_total_spent()
        if amount > remaining_amount:
            st.warning("Amount exceeds remaining budget.")
            return
        
        # Check if the category has a budget limit
        if category in self.budget_limits and amount > self.budget_limits[category]:
            st.warning(f"Amount exceeds budget limit for category {category}.")
            return

        cursor.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                       (self.user_id, amount, category, date.strftime("%Y-%m-%d")))
        conn.commit()
        st.success("Expense added successfully!")

    def get_total_spent(self):
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (self.user_id,))
        result = cursor.fetchone()[0]
        return result if result else 0

    def view_expenses(self, filter_category=None, start_date=None, end_date=None):
        query = "SELECT amount, category, date FROM expenses WHERE user_id = ?"
        params = [self.user_id]

        if filter_category:
            query += " AND category = ?"
            params.append(filter_category)
        if start_date and end_date:
            query += " AND date BETWEEN ? AND ?"
            params.extend([start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")])

        cursor.execute(query, tuple(params))
        expenses = cursor.fetchall()
        df = pd.DataFrame(expenses, columns=["Amount", "Category", "Date"])

        if df.empty:
            st.write("No expenses to display.")
        else:
            st.write("**Expense List:**")
            st.write(df)

    def delete_expense(self, expense_id):
        cursor.execute("DELETE FROM expenses WHERE user_id = ? AND id = ?", (self.user_id, expense_id))
        conn.commit()
        st.success("Expense deleted.")

    def view_remaining_budget(self):
        remaining_amount = self.salary - self.get_total_spent()
        st.write(f"Remaining amount: ${remaining_amount:.2f}")

    def set_budget_limit(self, category, limit):
        self.budget_limits[category] = limit
        cursor.execute('INSERT OR REPLACE INTO budget_limits (user_id, category, "limit") VALUES (?, ?, ?)', 
                       (self.user_id, category, limit))
        conn.commit()
        st.success(f"Budget limit of ${limit} set for {category}.")

    def plot_expense_distribution(self):
        cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category", (self.user_id,))
        data = cursor.fetchall()
        if not data:
            st.warning("No expenses to plot.")
            return

        df = pd.DataFrame(data, columns=["Category", "Total"])
        fig, ax = plt.subplots()
        ax.pie(df["Total"], labels=df["Category"], autopct="%1.1f%%", startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title("Category-wise Expense Distribution")
        st.pyplot(fig)

    def export_data(self):
        cursor.execute("SELECT amount, category, date FROM expenses WHERE user_id = ?", (self.user_id,))
        expenses = cursor.fetchall()
        df = pd.DataFrame(expenses, columns=["Amount", "Category", "Date"])
        return df

# Streamlit UI
def main():
    st.title("Expense Tracker")
    
    if st.session_state.logged_in:
        user_id = st.session_state.user_id
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        username = cursor.fetchone()[0]

        st.sidebar.header(f"Welcome, {username}")

        # Add salary input in the sidebar
        salary = st.sidebar.number_input("Enter Your Salary", min_value=0.01, format="%.2f", key="salary")
        
        if salary <= 0:
            st.warning("Please enter a valid salary.")
            return

        # Create ExpenseTracker instance using the entered salary
        tracker = ExpenseTracker(user_id, salary)

        if st.sidebar.button("Logout"):
            logout()

        # Expense Tracking Interface
        st.header("Track Your Expenses")
        action = st.selectbox("Choose an action", ["Add Expense", "View Expenses", "View Remaining Budget", 
                                                  "Set Budget Limit", "View Expense Distribution", "Export Data"])
        if action == "Add Expense":
            amount = st.number_input("Amount", min_value=0.01, format="%.2f")
            category = st.text_input("Category")
            date = st.date_input("Date", min_value=datetime.today())
            if st.button("Add Expense"):
                tracker.add_expense(amount, category, date)

        elif action == "View Expenses":
            filter_category = st.text_input("Filter by Category (optional)")
            start_date = st.date_input("Start Date (optional)")
            end_date = st.date_input("End Date (optional)")
            if st.button("View Expenses"):
                tracker.view_expenses(filter_category, start_date, end_date)

        elif action == "View Remaining Budget":
            tracker.view_remaining_budget()

        elif action == "Set Budget Limit":
            category = st.text_input("Category")
            limit = st.number_input("Budget Limit", min_value=0.01, format="%.2f")
            if st.button("Set Budget Limit"):
                tracker.set_budget_limit(category, limit)

        elif action == "View Expense Distribution":
            tracker.plot_expense_distribution()

        elif action == "Export Data":
            df = tracker.export_data()
            st.write(df)
            st.download_button(label="Download as CSV", data=df.to_csv(), file_name="expenses.csv")

    else:
        action = st.selectbox("Choose an action", ["Login", "Register"])

        if action == "Login":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                login_user(username, password)

        elif action == "Register":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Register"):
                register_user(username, password)

if __name__ == "__main__":
    main()