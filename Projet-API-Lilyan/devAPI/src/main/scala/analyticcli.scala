package siren

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.connect.service.SparkConnectService
import siren.SirenLogger.info

object analyticcli extends App {
  val mysqlHost = sys.env.getOrElse("MYSQL_HOST", "db")
  val mysqlPort = sys.env.getOrElse("MYSQL_PORT", "3306")
  val mysqlUser = sys.env.getOrElse("MYSQL_USER", "sirenuser")
  val mysqlPassword = sys.env.getOrElse("MYSQL_PASSWORD", "12345678")
  val jdbcUrl = s"jdbc:mysql://$mysqlHost:$mysqlPort/siren"

  // Configuration pour Spark Connect
  System.setProperty("spark.plugins", "org.apache.spark.sql.connect.SparkConnectPlugin")

  val spark = SparkSession.builder()
    .appName("spark-connect-server")
    .master("local[*]")
    .config("spark.plugins", "org.apache.spark.sql.connect.SparkConnectPlugin")
    .config("spark.connect.grpc.binding.port", "15002")
    .config("spark.connect.grpc.arrow.maxBatchSize", "4m")
    .getOrCreate()

  val activityCounts = spark.read
    .format("jdbc")
    .option("url", jdbcUrl)
    .option("dbtable",
      "(SELECT activite_principale_unite_legale, COUNT(siren) AS siren_count " +
        "FROM siren.unite_legale GROUP BY activite_principale_unite_legale) AS activity_counts")
    .option("user", mysqlUser)
    .option("password", mysqlPassword)
    .option("driver", "com.mysql.cj.jdbc.Driver")
    .load()

  activityCounts.createOrReplaceGlobalTempView("activity")

  info("Views created: global_temp.activity")
  info("Spark Connect server running on port 15002.")

  sys.addShutdownHook {
    spark.stop()
  }

  Thread.currentThread().join()
}