# Extract interest tags from CSV
Add-Type -AssemblyName Microsoft.VisualBasic

$csvPath = "C:\Users\Authma\Desktop\Claude\Notion受眾\受眾包all\ExportBlock-6baf9576-a3ac-45b6-80d3-fc9f305c0513-Part-1\TA 233b1307b65f80da8e48e3942cdce925_all.csv"

$parser = New-Object Microsoft.VisualBasic.FileIO.TextFieldParser($csvPath, [System.Text.Encoding]::UTF8)
$parser.TextFieldType = [Microsoft.VisualBasic.FileIO.FieldType]::Delimited
$parser.SetDelimiters(",")
$parser.HasFieldsEnclosedInQuotes = $true
$parser.ReadFields() | Out-Null  # skip header

$normalizeMap = [System.Collections.Generic.Dictionary[string,string]]::new()

while (-not $parser.EndOfData) {
    $fields = $parser.ReadFields()
    if ($fields.Count -le 3) { continue }
    $raw = $fields[3]
    if (-not $raw -or $raw.Trim() -eq "") { continue }

    foreach ($line in ($raw -split "`n")) {
        $l = $line.Trim()

        # Skip location lines (section 1)
        if ($l -match '^\s*1[\.、]') { continue }

        # Skip demographic/behavior lines
        if ($l -match '^[•\*\|]') { continue }
        if ($l -match '行為[：:]|家長[：:]|任職[於在]|居住[在於]') { continue }
        if ($l -match '^性別|^年齡|^語言') { continue }

        # Remove section number prefix (2., 3., etc. with optional label)
        $l = $l -replace '^\s*\d+[\.、]\s*(?:興趣|interest|行為|地點|地區)?\s*[-－:：]?\s*', ''

        if ($l.Trim() -eq '') { continue }

        # Split by Chinese enumeration comma or 或
        foreach ($tag in ($l -split '[、或]')) {
            $t = $tag.Trim()

            # Remove leading +/- signs
            $t = $t -replace '^\s*[\+\-＋－]+\s*', ''
            # Collapse multiple spaces
            $t = $t -replace '\s{2,}', ' '
            $t = $t.Trim()

            # Skip too short
            if ($t.Length -lt 2) { continue }

            # Skip if contains location category markers
            if ($t -match '（地標）|（景點）|（國家）|（城市）|（地區）|（縣市）|（行政區）') { continue }

            # Skip distance/range markers
            if ($t -match '[公千百]里|公尺|半徑') { continue }

            # Skip anything with 行業類別
            if ($t -match '行業類別') { continue }

            # Skip if starts with digits only (years, codes)
            if ($t -match '^\d{4}') { continue }

            # Skip age ranges like 27-60
            if ($t -match '^\d{1,3}[-–]\d{1,3}$') { continue }

            # Skip slash-separated items (usually location hierarchies like 台灣/台北)
            if ($t -match '^[^（）()\[\]【】]+/[^（）()\[\]【】]+$') { continue }

            # Skip items that are notes/comments
            if ($t -match '類似廣告受眾|粉絲專頁|互動過|名單|網站訪客') { continue }
            if ($t -match '加了之後|很穩定|調整|測試|備注|備註|說明') { continue }

            # Skip items starting with brackets (usually notes)
            if ($t -match '^[\(\*\[（【]') { continue }

            # Skip obvious location names (common patterns)
            if ($t -match '^台灣$|^台北$|^台中$|^台南$|^高雄$|^新北$|^桃園$') { continue }
            if ($t -match '^中國$|^香港$|^澳門$|^新加坡$|^馬來西亞$|^日本$|^韓國$|^美國$') { continue }
            if ($t -match '縣$|市$|區$|鄉$|鎮$' -and $t.Length -le 5) { continue }

            # Skip if it's just punctuation or symbols
            if ($t -match '^[\s\p{P}\p{S}]+$') { continue }

            # Final length check
            if ($t.Length -lt 2) { continue }

            $key = ($t.ToLower() -replace '\s+', ' ').Trim()
            if (-not $normalizeMap.ContainsKey($key)) {
                $normalizeMap[$key] = $t
            }
        }
    }
}
$parser.Close()

$allTags = $normalizeMap.Values | Sort-Object

Write-Host "Total unique tags: $($allTags.Count)"

# Save to review file
[System.IO.File]::WriteAllLines("C:\Users\Authma\Desktop\Claude\tags_review.txt", $allTags, [System.Text.Encoding]::UTF8)
Write-Host "Saved to tags_review.txt"
