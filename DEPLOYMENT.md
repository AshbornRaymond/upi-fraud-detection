# 🚀 Deployment Guide - Running Your Project for FREE

This guide shows you how to deploy your UPI Fraud Detection system for free using cloud platforms.

## 📋 Prerequisites

1. Your code is already pushed to GitHub ✅
2. You have a GitHub account
3. That's it! No credit card needed for most platforms.

---

## 🎯 Option 1: Render (Recommended - Easiest)

### Why Render?
- ✅ Completely free (750 hours/month)
- ✅ No credit card required
- ✅ Auto-deploys from GitHub
- ⚠️ Sleeps after 15 min inactivity (wakes in ~30 seconds)

### Steps:

1. **Go to Render**: https://render.com
2. **Sign Up** with your GitHub account
3. **Create New Web Service**:
   - Click "New +" button → "Web Service"
   - Click "Connect GitHub" and authorize Render
   - Select your repository

4. **Configure Settings**:
   ```
   Name: upi-fraud-detection
   Environment: Python 3
   Build Command: pip install -r requirements.txt && playwright install chromium --with-deps
   Start Command: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
   ```

5. **Deploy**:
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deployment
   - You'll get a URL like: `https://your-app-name.onrender.com`

6. **Access Your App**:
   - Open the provided URL in your browser
   - The static files will be served automatically

### Important Notes:
- First request after sleep takes ~30 seconds
- Your app stays alive while being used
- Free plan: 750 hours/month (31 days = 744 hours)

---

## 🎯 Option 2: Railway

### Why Railway?
- ✅ Free $5 credit/month (~500 hours)
- ✅ Better performance than Render
- ✅ Easy setup
- ℹ️ Also sleeps after inactivity

### Steps:

1. **Go to Railway**: https://railway.app
2. **Sign Up** with GitHub
3. **New Project** → "Deploy from GitHub repo"
4. **Select your repository**
5. **Add Settings**:
   - Railway auto-detects Python
   - Add custom start command if needed:
     ```
     uvicorn backend.app:app --host 0.0.0.0 --port $PORT
     ```
6. **Add Environment Variable** (if needed):
   ```
   PORT=8000
   ```
7. **Deploy** and get your URL

---

## 🎯 Option 3: Fly.io (24/7 Running)

### Why Fly.io?
- ✅ Actually free (not trial)
- ✅ Runs 24/7 without sleeping
- ✅ Better for production
- ⚠️ Requires credit card (but won't charge on free tier)
- ⚠️ More technical setup

### Steps:

1. **Install Fly CLI**:
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Sign Up and Login**:
   ```bash
   fly auth signup
   fly auth login
   ```

3. **Launch App** (from your project directory):
   ```bash
   cd "d:\major project"
   fly launch
   ```

4. **Configure** when prompted:
   - App name: choose unique name
   - Region: choose closest to you
   - Don't add PostgreSQL
   - Don't deploy yet

5. **Edit `fly.toml`** (created automatically):
   ```toml
   [build]
     [build.args]
       PYTHON_VERSION = "3.11"

   [env]
     PORT = "8080"

   [[services]]
     http_checks = []
     internal_port = 8080
     protocol = "tcp"
   ```

6. **Deploy**:
   ```bash
   fly deploy
   ```

---

## 🔧 Troubleshooting

### Playwright Issues:
If browser automation fails on deployment, you may need to:
- Use Render/Railway/Fly.io (they support Playwright)
- Ensure build command includes: `playwright install chromium --with-deps`

### Port Issues:
- Always use `$PORT` environment variable (provided by platform)
- In code: `port=int(os.environ.get("PORT", 8000))`

### Static Files Not Loading:
- Ensure `backend/static/` folder is in your repository
- Check that FastAPI mounts static files correctly

### App Crashes:
- Check logs in platform dashboard
- Ensure all dependencies in `requirements.txt`
- Verify Python version compatibility

---

## 📊 Comparison Table

| Platform | Free Hours | Sleeps? | Setup Difficulty | Best For |
|----------|-----------|---------|------------------|----------|
| **Render** | 750/month | Yes (15 min) | ⭐ Easy | Quick demos |
| **Railway** | ~500/month | Yes | ⭐⭐ Easy | Better performance |
| **Fly.io** | 24/7 | No | ⭐⭐⭐ Medium | Production apps |

---

## 🎉 After Deployment

Once deployed, your app will be available at a public URL. You can:

1. **Test the API**:
   ```bash
   curl https://your-app.onrender.com/
   ```

2. **Share the URL** with others

3. **Monitor Usage** in the platform dashboard

4. **Auto-Deploy**: Push to GitHub = automatic deployment

---

## 💡 Pro Tips

1. **Keep App Awake** (Render/Railway):
   - Use a free service like UptimeRobot to ping your URL every 5 minutes
   - Or accept the sleep behavior for demos

2. **Environment Variables**:
   - Add secrets in platform dashboard, not in code
   - Never commit API keys to GitHub

3. **Custom Domain** (Optional):
   - Most platforms offer free custom domains
   - Configure in platform settings

---

## 🆘 Need Help?

- **Render Docs**: https://render.com/docs
- **Railway Docs**: https://docs.railway.app
- **Fly.io Docs**: https://fly.io/docs

Good luck with your deployment! 🚀
