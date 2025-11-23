# Git Setup Guide

This guide will help you set up Git version control for your UPI Fraud Detection project and push it to GitHub.

## What is Git?

Git is a version control system that helps you:
- Track changes in your code over time
- Collaborate with others
- Backup your code to the cloud (GitHub)
- Revert to previous versions if something breaks

## Prerequisites

1. **Install Git** on your computer:
   - Windows: Download from https://git-scm.com/download/win
   - During installation, use default settings

2. **Create a GitHub account** (if you don't have one):
   - Go to https://github.com
   - Click "Sign up" and follow the instructions

## Step-by-Step Git Setup

### Step 1: Configure Git

Open Command Prompt (cmd) and run these commands (replace with your name and email):

```cmd
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Step 2: Initialize Git Repository

Navigate to your project folder:

```cmd
cd "d:\major project ultra pro max\major project"
```

Initialize Git:

```cmd
git init
```

This creates a hidden `.git` folder that tracks your project's history.

### Step 3: Add Files to Git

Add all files to Git tracking:

```cmd
git add .
```

The `.` means "add everything". You can also add specific files:

```cmd
git add backend/app.py
git add README.md
```

### Step 4: Create Your First Commit

A "commit" is like taking a snapshot of your project at this moment:

```cmd
git commit -m "Initial commit: UPI Fraud Detection System"
```

The `-m` flag lets you add a message describing what changed.

### Step 5: Create a GitHub Repository

1. Go to https://github.com
2. Click the **+** icon in top right → "New repository"
3. Enter repository details:
   - **Repository name**: `upi-fraud-detection`
   - **Description**: `Intelligent System for UPI Fraud Detection using ML`
   - **Visibility**: Choose "Public" or "Private"
   - **DO NOT** check "Initialize with README" (we already have one)
4. Click "Create repository"

### Step 6: Connect to GitHub

After creating the repository, GitHub will show you commands. Use these:

```cmd
git remote add origin https://github.com/YOUR-USERNAME/upi-fraud-detection.git
git branch -M main
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username.

**Note**: If you're using SSH instead of HTTPS:
```cmd
git remote add origin git@github.com:YOUR-USERNAME/upi-fraud-detection.git
```

### Step 7: Enter GitHub Credentials

When you push for the first time, Git will ask for credentials:

**Option 1: Personal Access Token (Recommended)**
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
2. Generate new token (classic)
3. Select scopes: `repo` (all repo permissions)
4. Copy the token
5. Use the token as your password when Git prompts

**Option 2: GitHub Desktop**
- Download GitHub Desktop app
- It handles authentication automatically

## Common Git Commands

### Checking Status

See which files have changed:

```cmd
git status
```

### Making More Commits

After you make changes to files:

```cmd
git add .
git commit -m "Add feature X" 
git push
```

### Viewing History

See all commits:

```cmd
git log
```

Short version:

```cmd
git log --oneline
```

### Creating Branches

Branches let you work on features without affecting the main code:

```cmd
git branch feature-name
git checkout feature-name
```

Or create and switch in one command:

```cmd
git checkout -b feature-name
```

Switch back to main:

```cmd
git checkout main
```

### Pulling Latest Changes

If you're working on multiple computers or with others:

```cmd
git pull
```

### Undoing Changes

Discard changes in a file:

```cmd
git checkout -- filename.py
```

Undo last commit (but keep changes):

```cmd
git reset --soft HEAD~1
```

## Git Workflow for This Project

### Daily Work Cycle

1. **Start**: Pull latest changes
   ```cmd
   git pull
   ```

2. **Work**: Make your changes to the code

3. **Check**: See what changed
   ```cmd
   git status
   git diff
   ```

4. **Stage**: Add files to commit
   ```cmd
   git add .
   ```

5. **Commit**: Save your changes
   ```cmd
   git commit -m "Describe what you changed"
   ```

6. **Push**: Upload to GitHub
   ```cmd
   git push
   ```

### Good Commit Messages

Write clear commit messages that explain what you did:

**Good examples**:
- `Add VPA validation feature`
- `Fix bug in link validator`
- `Update README with installation instructions`
- `Improve Stage 2 ML model accuracy`

**Bad examples**:
- `update`
- `fixed stuff`
- `asdf`
- `final version` (there's never really a final version!)

## Important Files

### .gitignore

This file tells Git which files NOT to track:
- `__pycache__/` - Python cache files
- `*.pkl` - Large ML model files (should be downloaded separately)
- `.env` - Environment variables with secrets
- `venv/` - Virtual environment

We've already created this file for you!

### README.md

This is the first file people see on GitHub. It should explain:
- What your project does
- How to install it
- How to use it
- How to contribute

We've created a comprehensive README for you!

## Troubleshooting

### Problem: "Permission denied"

**Solution**: You might need to set up SSH keys or use HTTPS with a Personal Access Token.

### Problem: "Large files"

**Solution**: Don't commit ML model files (`.pkl`). They're in `.gitignore` for this reason.

### Problem: "Merge conflicts"

**Solution**: This happens when the same file is edited in two places. Git will mark the conflicts in the file:

```python
<<<<<<< HEAD
# Your version
=======
# Other version
>>>>>>> branch-name
```

Manually edit the file to keep what you want, then:

```cmd
git add conflicted-file.py
git commit -m "Resolve merge conflict"
```

### Problem: "Detached HEAD"

**Solution**: Get back to main branch:

```cmd
git checkout main
```

## GitHub Features

### Issues

Track bugs and feature requests:
1. Go to your repo on GitHub
2. Click "Issues" tab
3. Create new issue

### Pull Requests

Propose changes to the code:
1. Create a branch
2. Make changes
3. Push branch to GitHub
4. Click "New pull request"

### Releases

Mark specific versions:
1. Go to "Releases"
2. Click "Create a new release"
3. Tag version (e.g., `v1.0.0`)

## Best Practices

### Do:
✅ Commit often (small, logical changes)
✅ Write clear commit messages
✅ Pull before you push
✅ Use branches for new features
✅ Review your changes before committing
✅ Keep sensitive info out of Git (use `.env` files)

### Don't:
❌ Commit large binary files
❌ Commit passwords or API keys
❌ Commit `__pycache__` or virtual environments
❌ Force push (`git push -f`) unless you know what you're doing
❌ Commit directly to main for big changes (use branches)

## Next Steps

After setting up Git:

1. **Make regular commits** as you work
2. **Create branches** for new features
3. **Write good commit messages** 
4. **Push regularly** to back up your work
5. **Use GitHub Issues** to track todos

## Additional Resources

- **Git Documentation**: https://git-scm.com/doc
- **GitHub Guides**: https://guides.github.com
- **Interactive Git Tutorial**: https://learngitbranching.js.org
- **Git Cheat Sheet**: https://education.github.com/git-cheat-sheet-education.pdf

---

**Remember**: Git is there to help you, not scare you! It's okay to make mistakes - that's what version control is for! 🚀
