-- 1. Настройка
SET hive.exec.mode.local.auto=true;
SET mapreduce.framework.name=local;
SET hive.cli.print.header=true;
CREATE DATABASE IF NOT EXISTS auto_db;
USE auto_db;

-- 2. Таблица
DROP TABLE IF EXISTS cars;
CREATE EXTERNAL TABLE cars (
    brand STRING, title STRING, year_prod INT, probeg INT, price INT,
    seller_name STRING, rating STRING, reviews_count STRING, link STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ';'
STORED AS TEXTFILE LOCATION '/data/cars'
TBLPROPERTIES ('serialization.encoding'='UTF-8');

-- 3. Аналитика
DROP TABLE IF EXISTS car_analytics;
CREATE TABLE car_analytics AS
SELECT *,
    CASE WHEN reviews_int >= 10 THEN 'Market' ELSE 'Person' END as seller_type,
    CASE
        WHEN probeg < avg_probeg_year * 0.7 THEN 'Low'
        WHEN probeg > avg_probeg_year * 1.3 THEN 'Large'
        ELSE 'Normal'
    END as mileage_status,
    CASE
        WHEN price < avg_price_year * 0.30 THEN 'SUSPICIOUS'
        WHEN price < avg_price_year * 0.85 AND probeg < avg_probeg_year * 0.7 THEN 'DIAMOND (Best Price & Mileage)'
        WHEN price < avg_price_year * 0.85 AND probeg <= avg_probeg_year * 1.3 THEN 'HOT (Best Price)'
        WHEN price < avg_price_year * 0.85 AND probeg > avg_probeg_year * 1.3 THEN 'REASONABLE (Cheap but Worn)'
        ELSE 'OTHER'
    END as predicted_liquidity
FROM (
    SELECT brand, title, year_prod, probeg, price, link,
        CAST(REPLACE(rating, ',', '.') AS FLOAT) as rating,
        CAST(REGEXP_REPLACE(reviews_count, '[^0-9]', '') AS INT) as reviews_int,
        AVG(price) OVER(PARTITION BY brand, year_prod) as avg_price_year,
        AVG(probeg) OVER(PARTITION BY year_prod) as avg_probeg_year
    FROM cars WHERE price > 30000
    -- Здесь мы убрали фильтр по цене, чтобы вошли все 1.5 млн
) t;

-- 4. ВЫВОД В ТЕРМИНАЛ
SELECT brand, title, year_prod, price, CAST(avg_price_year AS INT) as market_avg,
    probeg, mileage_status, seller_type, predicted_liquidity
FROM (
    SELECT *, ROW_NUMBER() OVER(PARTITION BY brand ORDER BY price ASC) as rank
    FROM car_analytics
    WHERE predicted_liquidity IN ('DIAMOND (Best Price & Mileage)', 'HOT (Best Price)')
      AND rating >= 4.0
) ranked_cars
WHERE rank <= 1
ORDER BY brand ASC, price ASC;
