# --- НАСТРОЙКИ ---
$csvFiles = @("Cars.csv")
$hdfsDataPath = "/data/cars"
$hiveScriptName = "init_hive.sql"
$finalCsvName = "car_analytics.csv"

# Установка кодировки
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Exec-Docker($Container, $Command) {
    docker exec -e "HADOOP_OPTS=-Dfile.encoding=UTF-8" $Container sh -c "$Command"
}

# 1. ФУНКЦИЯ ОЖИДАНИЯ
function Wait-For-Service($Name, $TestCommand, $MaxRetries = 30) {
    Write-Host "Waiting for ${Name}..." -ForegroundColor Cyan
    for ($i = 1; $i -le $MaxRetries; $i++) {
        $result = Invoke-Expression $TestCommand 2>$null
        if ($result -match "Safe mode is OFF" -or $result -match "default") {
            Write-Host "${Name} is ready!" -ForegroundColor Green ; return $true
        }
        Write-Host "Attempt ${i}/${MaxRetries}: Waiting..."
        Start-Sleep -Seconds 10
    }
    throw "${Name} failed to start."
}

# Ждем сервисы
Wait-For-Service "HDFS" "docker exec namenode hdfs dfsadmin -safemode get"
Wait-For-Service "Hive" "docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -n root --silent=true -e 'SHOW DATABASES;'"

# 2. ЗАГРУЗКА В HDFS
Write-Host "Uploading data to HDFS..." -ForegroundColor Cyan
Exec-Docker "namenode" "hdfs dfs -mkdir -p $hdfsDataPath"
foreach ($file in $csvFiles) {
    docker cp $file namenode:/tmp/$file
    Exec-Docker "namenode" "hdfs dfs -put -f /tmp/$file $hdfsDataPath/"
}

# 3. ИНИЦИАЛИЗАЦИЯ ТАБЛИЦ
Write-Host "Running Hive init script..." -ForegroundColor Cyan
docker cp $hiveScriptName hive-server:/tmp/$hiveScriptName
Exec-Docker "hive-server" "beeline -u jdbc:hive2://localhost:10000 -n root --silent=true -f /tmp/$hiveScriptName"

# 4. ЭКСПОРТ (КАК В PUSK.ps1, НО БЫСТРЕЕ)
Write-Host "Exporting to ${finalCsvName} using csv2 format..." -ForegroundColor Cyan

# Формируем запрос
$hiveQuery = "SELECT brand, title, year_prod, price, CAST(avg_price_year AS INT), probeg, mileage_status, seller_type, predicted_liquidity, link FROM auto_db.car_analytics"

# ИСПОЛЬЗУЕМ outputformat=csv2 (как в PUSK.ps1)
# Это автоматически экранирует запятые в названиях машин, чтобы строки не ломались.
# Мы вручную создаем заголовок, а потом дописываем данные, фильтруя логи grep-ом.
Exec-Docker "hive-server" "echo 'brand,title,year_prod,price,market_avg,probeg,mileage_status,seller_type,predicted_liquidity,link' > /tmp/output.csv && beeline -u jdbc:hive2://localhost:10000 -n root --silent=true --outputformat=csv2 --showHeader=false -e '$hiveQuery' | grep -v 'jdbc:hive2' >> /tmp/output.csv"

# Копируем файл (это быстрее, чем pipe в PowerShell для 1.5 млн строк)
docker cp hive-server:/tmp/output.csv "./$finalCsvName"

Write-Host "Done! File saved as $finalCsvName" -ForegroundColor Green