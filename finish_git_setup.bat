@echo off
echo [ANTIGRAVITY] Setting up Git Identity...
git config user.email "tusharmagar09@gmail.com"
git config user.name "tusharmagar09"

echo [ANTIGRAVITY] Initializing Repository...
git init
git remote add origin https://github.com/tusharmagar09/MyKiteBot09.git

echo [ANTIGRAVITY] Committing Files...
git add .
git commit -m "Initialize Dashboard Automation"
git branch -M main

echo [ANTIGRAVITY] Pushing to GitHub...
git push -u origin main

echo [ANTIGRAVITY] DONE! Your dashboard automation is now active.
pause
