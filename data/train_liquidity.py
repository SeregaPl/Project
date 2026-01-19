# -*- coding: utf-8 -*-
from __future__ import print_function
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, when
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import MultilayerPerceptronClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import sys

# Разрешаем Python выводить UTF-8 в консоль
reload(sys)
sys.setdefaultencoding('utf-8')

# 1. Инициализация Spark
spark = SparkSession.builder \
    .appName("CarLiquidityNN") \
    .enableHiveSupport() \
    .getOrCreate()

print(">>> Loading data from Hive...")
# Читаем данные и сразу чиним рейтинг
df = spark.sql("""
    SELECT brand, year_prod, probeg, 
           CAST(REPLACE(rating, ',', '.') AS FLOAT) as rating, 
           price 
    FROM auto_db.cars
""")

# Удаляем строки с пропусками (null)
df = df.na.drop()

# 2. FEATURE ENGINEERING
windowSpec = Window.partitionBy("brand")
df = df.withColumn("avg_brand_price", avg("price").over(windowSpec))

# Размечаем классы ликвидности:
df = df.withColumn("label",
                   when(col("price") > col("avg_brand_price") * 1.1, 0.0)
                   .when(col("price") < col("avg_brand_price") * 0.9, 2.0)
                   .otherwise(1.0))

print(">>> Class distribution (0=Slow, 1=Normal, 2=Fast):")
df.groupBy("label").count().show()

# 3. Подготовка признаков
indexer = StringIndexer(inputCol="brand", outputCol="brand_index")
df_indexed = indexer.fit(df).transform(df)

assembler = VectorAssembler(
    inputCols=["brand_index", "year_prod", "probeg", "rating", "price"],
    outputCol="features"
)
data = assembler.transform(df_indexed)

train_data, test_data = data.randomSplit([0.8, 0.2], seed=1234)

# 4. Архитектура Нейросети
# Слои: Вход(5) -> Скрытый(10) -> Скрытый(8) -> Выход(3)
layers = [5, 10, 8, 3]

trainer = MultilayerPerceptronClassifier(
    maxIter=100,
    layers=layers,
    blockSize=128,
    seed=1234
)

print(">>> Training Neural Network...")
model = trainer.fit(train_data)

# 5. Проверка точности
result = model.transform(test_data)
predictionAndLabels = result.select("prediction", "label")
evaluator = MulticlassClassificationEvaluator(metricName="accuracy")

accuracy = evaluator.evaluate(predictionAndLabels)
print(">>> Model Accuracy: {}".format(accuracy))

print(">>> Prediction examples:")
result.select("brand", "price", "label", "prediction").show(5)

model.save("/tmp/liquidity_model_nn")
print(">>> Model saved successfully!")