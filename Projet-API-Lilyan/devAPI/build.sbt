ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "2.12.17"
import sbtassembly.AssemblyPlugin.autoImport._

assembly / mainClass := Some("siren.dbcli")

libraryDependencies ++= Seq(
  "mysql" % "mysql-connector-java" % "8.0.33",
  "org.apache.spark" %% "spark-core" % "3.4.4", "org.apache.spark" %% "spark-sql" % "3.4.4",
  "org.apache.spark" %% "spark-connect" % "3.4.4"
)

lazy val root = (project in file(".")).settings(name := "devAPI")