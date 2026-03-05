# Hosting Guide for VGN Recruitment System

This guide explains how to host your Flask application so that applicants can fill it out online.

## Recommendation: Render.com (Easiest & Free Tier Available)

Render is a modern cloud platform that is very easy to use for Flask apps.

### Step 1: Prepare Your Code
1.  **Create a GitHub Repository**: Sign up at [github.com](https://github.com) and create a new private repository.
2.  **Upload Your Files**: Upload all the files in your project directory (except for the ones listed in `.gitignore`) to your GitHub repository.

### Step 2: Create a Web Service on Render
1.  Go to [Render.com](https://render.com) and sign up with your GitHub account.
2.  Click **"New +"** and select **"Web Service"**.
3.  Connect your GitHub repository.
4.  Configure the service:
    *   **Name**: `vgn-recruitment` (or anything you like)
    *   **Region**: Choose the one closest to you (e.g., Oregon or Frankfurt).
    *   **Runtime**: `Python`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn app:app`
5.  **Environment Variables**:
    *   Click on the **"Environment"** tab.
    *   Add a new variable: `SECRET_KEY` and give it a random long string (e.g., `aVeryLongAndSecureRandomString123!`).

### Step 3: Persistence (CRITICAL for SQLite)
Since you are using SQLite (`database.db`), Render's files are "ephemeral" (they disappear when the app restarts) unless you add a **Disk**.
1.  In your Render dashboard, go to the **"Disks"** tab.
2.  Click **"Add Disk"**.
    *   **Name**: `vgn-data`
    *   **Mount Path**: `/data`
    *   **Size**: `1GB` (enough for thousands of applications).
3.  **Update `app.py`**:
    You will need to update the database path in `app.py` to point to `/data/database.db` instead of `database.db`.

---

## Alternative: PythonAnywhere (Great for Beginners)
If Render seems too complex due to the disk setup, PythonAnywhere is a great alternative that doesn't need "Disks" for SQLite.

1.  Sign up at [PythonAnywhere.com](https://www.pythonanywhere.com).
2.  Upload your files using their "Files" tab.
3.  Follow their [Flask Deployment Guide](https://help.pythonanywhere.com/pages/Flask/).

## How to Share the Link
Once the deployment is finished, Render (or PythonAnywhere) will give you a link like:
`https://vgn-recruitment.onrender.com`

**Congratulations!** You can now share this link with applicants through SMS, WhatsApp, or your official channels.
