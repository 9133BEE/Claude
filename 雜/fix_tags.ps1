
# 讀取中→英翻譯表 CSV
$csvPath = "C:\Users\Authma\Desktop\Claude\trans_chn2eng.csv"
$chnToEng = @{}
Import-Csv $csvPath -Encoding UTF8 | ForEach-Object { $chnToEng[$_.Chinese] = $_.English }

# 補漏翻譯（CSV 未收錄或特殊格式）
$missing = @{
  "Netflix（串流服務"="Netflix (Streaming Service)"
  "工業設計"="Industrial Design"
  "化學工程"="Chemical Engineering"
  "主管"="Manager / Executive"
  "主管級和管理階層工作"="Senior and Managerial Jobs"
  "生活"="Lifestyle / Daily Life"
  "生活要事：遠離家鄉"="Life Events: Away from Hometown"
  "生產"="Production / Manufacturing"
  "企業級軟體"="Enterprise Software"
  "企劃"="Planning / Project"
  "地方政府"="Local Government"
  "自動化技術"="Automation Technology"
  "自然科學"="Natural Sciences"
  "折扣卡 (優惠券"="Discount Card (Coupon)"
  "折扣和購物回饋)"="Discounts and Shopping Cashback"
  "夜生活 (酒吧"="Nightlife (Bar)"
  "夜店（酒吧"="Nightclub (Bar)"
  "法学"="Law (Academic)"
  "社會科學"="Social Sciences"
  "保護服務"="Protective Services"
  "品牌管理"="Brand Management"
  "建築工程"="Building Engineering"
  "建築風格"="Architectural Style"
  "建築與工程"="Architecture and Engineering"
  "建築與採石"="Construction and Mining"
  "政府員工（全球）, 生活要事：不與家人同住"="Government Employee (Global) - Not Living with Family"
  "眉毛（身體部位"="Eyebrow (Body Part)"
  "研究"="Research"
  "美食家（美食和餐飲）, 生活要事：遠離家鄉"="Foodie (Food and Dining) - Away from Hometown"
  "風險管理"="Risk Management"
  "俱樂部"="Club"
  "俱樂部和夜生活)"="Club and Nightlife"
  "俱樂部與夜生活）"="Club and Nightlife"
  "酒吧 (酒吧"="Bar (Nightlife)"
  "酒吧（酒吧"="Bar (Nightlife)"
  "會員集點計畫 (優惠券"="Member Points Program (Coupon)"
  "裝飾風藝術"="Art Deco"
  "潛水"="Diving / Scuba Diving"
  "燒瓶子。大肆の鍋 彰化店"="Yakiniku Restaurant - Changhua Store"
  "優乃克"="Unac (Brand)"
  "優惠券"="Coupon / Voucher"
  "環境工程"="Environmental Engineering"
  "環境科技"="Environmental Technology"
  "礦物和採礦)"="Minerals and Mining"
  "生產率, 生活要事：新婚"="Productivity - Life Events: Newly Married"
}
$missing.GetEnumerator() | ForEach-Object { $chnToEng[$_.Key] = $_.Value }

# 英→中翻譯表（純英文標籤補中文說明）
$engToChn = @{
  "5G"="5G行動網路"; "Acqua di Parma"="帕爾瑪之水（香氛）"; "Adobe Illustrator"="向量繪圖軟體";
  "Adobe InDesign"="排版設計軟體"; "AI"="人工智慧"; "Algorithmic trading"="演算法交易";
  "AMD Radeon"="AMD顯示卡"; "Android Wear"="智慧手錶系統"; "Apple Music"="音樂串流服務";
  "Apple Pay"="行動支付"; "Architecture & Interior Design"="建築與室內設計";
  "Art auction"="藝術品拍賣"; "Art school"="藝術學校"; "Aveda"="卡詩（美髮品牌）";
  "Beauty Dior"="迪奧美妝"; "Bilingual education"="雙語教育"; "Biomedical sciences"="生物醫學科學";
  "BMW i"="BMW i電動車系列"; "Bottega Veneta"="葆蝶家（精品）"; "Boutique hotel"="精品飯店";
  "Business analysis"="商業分析"; "Business networking"="商業社交"; "C++"="程式語言（C++）";
  "C#"="程式語言（C#）"; "C♯"="程式語言（C♯）"; "Canva"="設計工具"; "Cash on delivery"="貨到付款";
  "Celebrity News"="名人新聞"; "CeraVe Skincare"="CeraVe醫療護膚"; "Certified Financial Planner"="認證理財規劃師";
  "Cetaphil"="絲塔芙護膚"; "Christmas Holiday"="聖誕假期"; "Commercial fishing"="商業漁業";
  "Compensation and benefits"="薪酬與福利"; "Continuing education"="繼續教育"; "Convenience food"="即食食品";
  "Country club"="鄉村俱樂部"; "Craft Beer and Brewing"="精釀啤酒"; "Cultural tourism"="文化旅遊";
  "Cultural travel"="文化之旅"; "Customer support"="客戶服務"; "DHC"="DHC日系保養品";
  "Digital transformation"="數位轉型"; "Diptyque"="蒂普提克（香氛）"; "Diving equipment"="潛水設備";
  "DJI"="大疆無人機"; "Doctor of Medicine"="醫學博士"; "Early Learning Centre"="兒童早期學習";
  "Electric vehicle conversion"="電動車改裝"; "Electrical wiring"="電氣配線";
  "Employee Benefit News"="員工福利新聞"; "Entertainment News"="娛樂新聞"; "EToro"="eToro社交投資平台";
  "Family Fresh Meals"="家庭新鮮餐食"; "FamilyMart"="全家便利商店"; "Farm-to-table"="農場直送餐桌";
  "Fashion & Make Up"="時尚與彩妝"; "Financial technology"="金融科技（FinTech）";
  "FineDiningLovers"="精緻餐飲愛好者"; "Food storage"="食物儲存"; "Fragrance oil"="香氛精油";
  "Freight transport"="貨運運輸"; "Gadget & Gear"="科技小物與裝備"; "Garmin Fitness"="Garmin健身裝置";
  "Gift card"="禮品卡"; "Giorgio Armani Beauty"="亞曼尼美妝"; "GitHub"="程式碼託管平台";
  "Glamping"="豪華露營"; "Google"="Google搜尋引擎"; "Google AdWords"="Google廣告平台";
  "Google Flights"="Google機票搜尋"; "GoPro"="GoPro運動相機"; "Gourmet"="美食饕客";
  "Gourmet Food Lovers"="美食愛好者"; "Government agency"="政府機關"; "Health News"="健康新聞";
  "High-end audio"="高端音響"; "Hoka One One"="HOKA跑鞋"; "Horse training"="馬術訓練";
  "Housewarming party"="喬遷派對"; "HydraFacial"="水飢餓護膚療程"; "Industrial technology"="工業技術";
  "International business"="國際商務"; "International education"="國際教育"; "Investment club"="投資俱樂部";
  "iPad"="蘋果平板電腦"; "iPhone Lovers"="iPhone愛好者"; "iTunes"="蘋果媒體軟體";
  "Java"="Java程式語言"; "JavaScript"="JavaScript程式語言"; "Jewelry"="珠寶首飾";
  "Jo Malone London"="祖馬龍（香氛）"; "Kaohsiung; Tainan"="高雄；台南";
  "KIND Healthy Snacks"="KIND健康零食"; "Kitchen Design"="廚房設計"; "Korean pop idol"="韓國流行偶像";
  "La mer"="海藍之謎（護膚）"; "Leadership development"="領導力發展"; "Lifestyle brand"="生活風格品牌";
  "LifeStyle Food"="生活風格飲食"; "LifeStyle Home"="生活風格居家"; "Lifestyle Travel"="生活風格旅遊";
  "Light fixture"="燈具"; "LINE"="LINE通訊軟體"; "Linux"="Linux作業系統"; "loewe"="羅意威（精品）";
  "Love Nature"="愛自然"; "Lunch box"="便當"; "MacBook"="蘋果筆記型電腦"; "MacBook Pro"="蘋果專業筆電";
  "Medical education"="醫學教育"; "MetaTrader 4"="MetaTrader 4外匯平台"; "Miaoli"="苗栗";
  "Miaoli County"="苗栗縣"; "Microsoft Excel"="Excel試算表軟體"; "Microsoft Office"="Office辦公軟體";
  "Mobile application development"="行動應用程式開發"; "Nantou"="南投";
  "National Center for Immunization and Respiratory Diseases"="美國免疫和呼吸疾病中心";
  "NVIDIA GeForce"="NVIDIA顯示卡"; "Office Space"="辦公空間"; "Oracle CRM"="Oracle客戶關係管理";
  "Outdoor Living"="戶外生活"; "Payment service provider"="支付服務提供商"; "PC Gamer"="PC遊戲玩家";
  "Pet Care"="寵物護理"; "PHP"="PHP程式語言"; "Pinterest"="Pinterest圖片社群";
  "PlayStation 4"="PlayStation 4遊戲主機"; "PlayStation Store"="PlayStation遊戲商城";
  "PlayStation VR"="PlayStation虛擬實境"; "Positive Parenting Solutions"="正向教養解決方案";
  "Prefabricated home"="預製屋"; "Priority Pass"="機場貴賓室通行"; "Procurement"="採購";
  "Professional services"="專業服務"; "Project management software"="專案管理軟體";
  "Quality Foods"="優質食品"; "QuickBooks"="QuickBooks會計軟體"; "Razer"="Razer電競品牌";
  "Restaurant management"="餐廳管理"; "Retirement Insurance Benefits"="退休保險福利";
  "RV Travel"="露營車旅遊"; "Sap basis"="SAP企業系統基礎"; "Seed accelerator"="種子加速器";
  "Skyscanner"="Skyscanner機票比價"; "socializing"="社交活動"; "SQL"="SQL資料庫語言";
  "Sustainable architecture"="永續建築"; "Taichung"="台中"; "Taichung; Changhua; Miaoli"="台中；彰化；苗栗";
  "Taichung; Changhua; Miaoli; Nantou"="台中；彰化；苗栗；南投"; "Taichung; Changhua; Nantou"="台中；彰化；南投";
  "Taoyuan City; Hsinchu; Miaoli; Hsinchu City"="桃園；新竹縣；苗栗；新竹市";
  "Taoyuan City; Taichung; Changhua; Hsinchu; Miaoli; Nantou"="桃園；台中；彰化；新竹；苗栗；南投";
  "Tax law"="稅法"; "Tax preparation"="報稅"; "The New Age Parents"="新世代父母";
  "Tourism in Japan"="日本旅遊"; "Travel Deals"="旅遊優惠"; "Travel the World"="環遊世界";
  "Trivago"="Trivago旅遊比價"; "UberEATS"="Uber Eats外送平台"; "Venture capital financing"="創業投資融資";
  "Visa Cash"="Visa現金卡"; "Weekend Getaway"="週末短途旅遊"; "Weekend Trips"="週末旅行";
  "Window shutter"="百葉窗"; "WordPress"="WordPress網站平台"; "Workwear"="工作服";
  "World Gym"="World Gym健身房"
}

# 判斷是否含中文
function HasChinese($s) { return $s -match '[一-鿿]' }

# 處理括號拆分：回傳 @{ TagName=; Category= } 或 $null
function SplitParen($tag) {
    if ($tag -match '^(.+?)\s*[（(](.+?)[)）]\s*$') {
        return @{ TagName=$matches[1].TrimEnd(); Category=$matches[2] }
    }
    return $null
}

$src = "C:\Users\Authma\Desktop\Claude\META興趣標籤.xlsx"
$dst = "C:\Users\Authma\Desktop\Claude\META興趣標籤_副本.xlsx"
Copy-Item $src $dst -Force
Write-Host "複製原始檔 → $dst"

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$wb = $excel.Workbooks.Open($dst)
$s1 = $wb.Sheets.Item(1)
$s3 = $wb.Sheets.Item(3)
$lastRow = $s3.UsedRange.Rows.Count

$s3.Cells.Item(1,2).Value2 = "英文標籤"

$stats = @{ Split=0; EngAddChn=0; ChnAddEng=0; NoTrans=0 }

for ($r = 2; $r -le $lastRow; $r++) {
    $tag = $s3.Cells.Item($r,2).Text
    if ([string]::IsNullOrWhiteSpace($tag)) { continue }

    $paren = SplitParen $tag

    if ($paren) {
        $name = $paren.TagName
        $cat  = $paren.Category
        if (HasChinese $name) {
            # 標籤名是中文 → 查英文翻譯，加 ()
            $eng = $chnToEng[$name]
            if ($eng) {
                $s3.Cells.Item($r,2).Value2 = "($eng)"
            } else {
                $s3.Cells.Item($r,2).Value2 = $name
                $stats.NoTrans++
            }
            $s3.Cells.Item($r,3).Value2 = "$name（$cat）"
        } else {
            # 標籤名是英文 → 直接拆分，不加 ()
            $s3.Cells.Item($r,2).Value2 = $name
            $s3.Cells.Item($r,3).Value2 = $cat
        }
        $stats.Split++
    } elseif (-not (HasChinese $tag)) {
        # 純英文無括號 → 補中文，加 ()
        $chn = $engToChn[$tag]
        if ($chn) {
            $s3.Cells.Item($r,2).Value2 = $tag
            $s3.Cells.Item($r,3).Value2 = "($chn)"
            $stats.EngAddChn++
        } else {
            $stats.NoTrans++
        }
    } else {
        # 有中文無括號 → 補英文，加 ()
        $eng = $chnToEng[$tag]
        if ($eng) {
            $s3.Cells.Item($r,2).Value2 = "($eng)"
            $s3.Cells.Item($r,3).Value2 = $tag
            $stats.ChnAddEng++
        } else {
            $stats.NoTrans++
            Write-Host "  [未翻譯] $tag"
        }
    }
}

# 套用格式
$s3.Columns.Item(1).ColumnWidth = $s1.Columns.Item(1).ColumnWidth
$s3.Columns.Item(2).ColumnWidth = $s1.Columns.Item(2).ColumnWidth
$s3.Columns.Item(3).ColumnWidth = $s1.Columns.Item(3).ColumnWidth
$s3.UsedRange.Font.Name = "新細明體"
$s3.UsedRange.Font.Size = 12
$s3.UsedRange.WrapText = $false
$s3.Rows.Item(1).Font.Bold = $true
$s3.Range("A2:C$lastRow").Font.Bold = $false
$s3.Range("2:$lastRow").RowHeight = 16.5

$wb.Save(); $wb.Close(); $excel.Quit()

Write-Host ""
Write-Host "=== 完成 ==="
Write-Host "括號拆分：$($stats.Split)"
Write-Host "英文補中文：$($stats.EngAddChn)"
Write-Host "中文補英文：$($stats.ChnAddEng)"
Write-Host "未找到翻譯：$($stats.NoTrans)"
