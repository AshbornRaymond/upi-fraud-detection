# Complete Git Commands for Push

Follow these commands in order to set up Git and push your project to GitHub.

## 1. Initial Setup (One-Time Only)

Open Command Prompt and configure your Git identity:

```cmd
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## 2. Navigate to Project Directory

```cmd
cd "d:\major project ultra pro max\major project"
```

## 3. Initialize Git Repository

```cmd
git init
```

## 4. Add All Files to Staging

```cmd
git add .
```

This adds all files except those listed in `.gitignore`.

## 5. Create Your First Commit

```cmd
git commit -m "Initial commit: UPI Fraud Detection System with comprehensive documentation"
```

## 6. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `upi-fraud-detection-system`
3. Description: `Intelligent ML-based system for detecting UPI fraud in real-time`
4. Choose Public or Private
5. **DO NOT** initialize with README (we already have one)
6. Click "Create repository"

## 7. Connect to GitHub

Replace `YOUR-USERNAME` with your actual GitHub username:

```cmd
git remote add origin https://github.com/YOUR-USERNAME/upi-fraud-detection-system.git
```

## 8. Rename Branch to Main

```cmd
git branch -M main
```

## 9. Push to GitHub

```cmd
git push -u origin main
```

**Note**: You'll be prompted for authentication. Use a Personal Access Token (not password).

### Creating a Personal Access Token:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Name: `UPI Fraud Detection Project`
4. Select scopes: Check `repo` (all repository permissions)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)
7. When Git prompts for password, paste the token

## 10. Verify Upload

Go to your GitHub repository URL to see all files uploaded!

---

## Daily Git Workflow (After Initial Setup)

### Making Changes and Pushing

```cmd
# 1. Check what changed
git status

# 2. Add all changes
git add .

# 3. Commit with descriptive message
git commit -m "Your descriptive message here"

# 4. Push to GitHub
git push
```

### Common Commit Messages

```cmd
git commit -m "Add new fraud detection feature"
git commit -m "Fix bug in link validator"
git commit -m "Update documentation"
git commit -m "Improve ML model accuracy"
git commit -m "Add VPA whitelisting"
```

### Pulling Latest Changes

If you work on multiple computers or with teammates:

```cmd
git pull
```

### Viewing History

```cmd
# Detailed history
git log

# Compact history
git log --oneline --graph

# Last 5 commits
git log -5
```

### Checking Status

```cmd
# See what files changed
git status

# See actual changes in files
git diff
```

---

## Troubleshooting Commands

### Undo Last Commit (Keep Changes)

```cmd
git reset --soft HEAD~1
```

### Discard All Local Changes

```cmd
git reset --hard HEAD
```

### Remove File from Staging

```cmd
git reset HEAD filename.py
```

### View Remote Repository URL

```cmd
git remote -v
```

### Change Remote URL

```cmd
git remote set-url origin https://github.com/NEW-USERNAME/new-repo.git
```

---

## What Gets Pushed?

Based on your `.gitignore`, these files **will be pushed**:

✅ All Python source code (`.py` files)
✅ README.md and documentation files
✅ requirements.txt
✅ HTML/CSS/JS files
✅ Configuration files (`.json`)
✅ Training data CSV files (in `data/` folder)

These files **will NOT be pushed** (as configured in `.gitignore`):

❌ `__pycache__/` directories
❌ `.pkl` model files (too large)
❌ Virtual environment (`venv/`)
❌ IDE settings (`.vscode/`, `.idea/`)
❌ Log files

**Note**: ML model files (`.pkl`) are in `.gitignore` because they're large. Users should train their own models using `python stage1/links_stage1.py`.

---

## Repository Structure on GitHub

```
your-repo/
├── README.md                  ← Will show on GitHub homepage
├── QUICK_START.md
├── GIT_SETUP_GUIDE.md
├── requirements.txt
├── .gitignore
├── backend/
│   ├── app.py
│   ├── orchestrator.py
│   └── static/
├── link_validation/
├── message_validation/
├── qr_validation/
├── stage1/
├── stage2_dynamic/
├── vpa_validation/
└── data/
```

---

## Additional Tips

### Add Specific Files Only

```cmd
git add backend/app.py
git add README.md
```

### Commit Specific Files

```cmd
git add backend/app.py
git commit -m "Update main server file"
```

### View Changes Before Committing

```cmd
git diff
```

### Create a New Branch

```cmd
git checkout -b feature-name
```

### Switch Back to Main

```cmd
git checkout main
```

### Merge Branch into Main

```cmd
git checkout main
git merge feature-name
```

---

## Complete First-Time Push Script

Copy and paste this entire block (update YOUR-USERNAME):

```cmd
cd "d:\major project ultra pro max\major project"
git init
git add .
git commit -m "Initial commit: UPI Fraud Detection System"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/upi-fraud-detection-system.git
git push -u origin main
```

---

## Verification Checklist

After pushing, verify on GitHub:

- [ ] README.md displays properly
- [ ] All source code files are present
- [ ] File structure matches local project
- [ ] .gitignore is working (no `__pycache__` or `.pkl` files)
- [ ] Documentation files are readable
- [ ] requirements.txt is present

---

## Need Help?

- **Forgot GitHub password**: Use Personal Access Token instead
- **Large files rejected**: They should be in `.gitignore` already
- **"Failed to push"**: Check internet connection and GitHub status
- **Merge conflicts**: Pull first with `git pull`, resolve conflicts, then push

---

**Your project is now ready for version control! 🎉**

For detailed Git learning, see `GIT_SETUP_GUIDE.md`
