"""Optional real Spark job. Run with spark-submit on an existing Spark installation."""
import json
from pyspark.sql import SparkSession, functions as F


def main():
    spark = SparkSession.builder.appName('PlatformCareSyntheticAggregate').getOrCreate()
    try:
        events = spark.createDataFrame([('music', 4), ('tv', 12), ('music', 8)], ['service', 'minutes'])
        if events.where(F.col('minutes').isNull() | (F.col('minutes') < 0)).limit(1).count():
            raise ValueError('Validation failed: minutes must be nonnegative')
        rows = events.groupBy('service').agg(F.sum('minutes').alias('total_minutes')).collect()
        result = {row['service']: row['total_minutes'] for row in rows}
        if result != {'music': 12, 'tv': 12}:
            raise ValueError('Spark output differs from the synthetic reference')
        print(json.dumps({'engine': 'spark', 'passed': True, 'totals': result, 'scope': 'three synthetic events'}))
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
