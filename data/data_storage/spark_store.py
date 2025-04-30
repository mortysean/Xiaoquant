from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, FloatType

class SparkStore:
    def __init__(self):
        """Initializes SparkSession for data storage."""
        self.spark = SparkSession.builder \
            .appName("MarketDataStorage") \
            .master("spark://127.0.0.1:7077") \
            .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
            .getOrCreate()
        
        print("✅ Spark Store initialized successfully.")

    def insert_market_data(self, data):
        """Inserts standardized market data into Spark DataFrame."""
        try:
            # Define Spark schema
            schema = StructType([
                StructField("timestamp", StringType(), True),
                StructField("symbol", StringType(), True),
                StructField("exchange", StringType(), True),
                StructField("open", FloatType(), True),
                StructField("high", FloatType(), True),
                StructField("low", FloatType(), True),
                StructField("close", FloatType(), True),
                StructField("volume", FloatType(), True),
            ])

            # Convert dictionary to DataFrame
            df = self.spark.createDataFrame([data], schema=schema)

            # Save as Parquet file (or other formats)
            df.write.mode("append").parquet("/tmp/spark_market_data")

            print(f"✅ Data inserted into Spark: {data}")

        except Exception as e:
            print(f"❌ Error inserting data into Spark: {e}")
