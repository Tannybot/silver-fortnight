import tkinter as tk
from tkinter import messagebox
import json
import subprocess

# Create a sample users file if it doesn't exist
try:
    with open('users.json', 'r') as f:
        users = json.load(f)
except FileNotFoundError:
    users = {"admin": "password123"}
    with open('users.json', 'w') as f:
        json.dump(users, f)

def login():
    username = entry_user.get()
    password = entry_pass.get()
    if users.get(username) == password:
        root.destroy()
        subprocess.run(["streamlit", "run", "app.py"])
    else:
        messagebox.showerror("Login Failed", "Invalid username or password")

root = tk.Tk()
root.title("Event Management System - Government Use")
root.geometry("450x500")

tk.Label(root, text="Smart Government Event Scheduler", font=("Helvetica", 16)).pack(pady=10)
tk.Label(root, text="Objective:\nTo design and implement a smart and user-friendly event management system for local community engagement. Features include scheduling, registration, announcements, reminders, tracking, and analytics.", wraplength=400, justify="left").pack(pady=20)

tk.Label(root, text="Username").pack()
entry_user = tk.Entry(root)
entry_user.pack()

tk.Label(root, text="Password").pack()
entry_pass = tk.Entry(root, show="*")
entry_pass.pack()

tk.Button(root, text="Login", command=login).pack(pady=20)

root.mainloop()
