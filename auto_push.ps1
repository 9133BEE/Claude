cd "C:\Users\Authma\Desktop\Claude"
git add .
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "auto backup $timestamp"
git push
