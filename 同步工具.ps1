while ($true) {
    Clear-Host
    Write-Host "==============================="
    Write-Host "       GitHub Sync Tool        "
    Write-Host "==============================="
    Write-Host "  1. Upload (push to GitHub)"
    Write-Host "  2. Download (pull from GitHub)"
    Write-Host "  3. Sync Memory only"
    Write-Host "==============================="
    $choice = Read-Host "Enter 1, 2 or 3"

    Set-Location "C:\Users\Authma\Desktop\Claude"

    switch ($choice) {
        "1" {
            Write-Host "Uploading..." -ForegroundColor Cyan
            git add .
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
            git commit -m "backup $timestamp"
            git push
            Write-Host "Done!" -ForegroundColor Green
        }
        "2" {
            Write-Host "Downloading..." -ForegroundColor Cyan
            git pull
            Write-Host "Done!" -ForegroundColor Green
        }
        "3" {
            Write-Host "Syncing memory..." -ForegroundColor Cyan
            git add .claude/
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
            git commit -m "sync memory $timestamp"
            git push
            Write-Host "Done!" -ForegroundColor Green
        }
        default {
            Write-Host "Please enter 1, 2 or 3" -ForegroundColor Red
        }
    }

    Read-Host "Press Enter to continue"
}
