package siren

import org.apache.spark.sql.SparkSession
import siren.SirenLogger.info

object analyticcli extends App {
  val mysqlHost = sys.env.getOrElse("MYSQL_HOST", "db")
  val mysqlPort = sys.env.getOrElse("MYSQL_PORT", "3306")
  val mysqlUser = sys.env.getOrElse("MYSQL_USER", "sirenuser")
  val mysqlPassword = sys.env.getOrElse("MYSQL_PASSWORD", "12345678")
  val jdbcUrl = s"jdbc:mysql://$mysqlHost:$mysqlPort/siren"

  val spark = SparkSession.builder()
    .appName("spark-connect-server")
    .master("local[*]")
    .config("spark.connect.grpc.binding.port", "15002")
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

  info("Spark session started on port 15002.")
  info("Views: global_temp.activity, global_temp.zone")

  sys.addShutdownHook {
    spark.stop()
  }

  Thread.currentThread().join()
}