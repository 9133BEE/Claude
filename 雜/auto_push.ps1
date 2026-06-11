$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

# 先推 snazzy 網站
cd "C:\Users\Authma\Desktop\Claude\受眾資料庫網頁"
git add .
git commit -m "auto backup $timestamp" 2>$null
git push

# 再推 Claude 主倉庫
cd "C:\Users\Authma\Desktop\Claude"
git add .
git commit -m "auto backup $timestamp" 2>$null
git push
