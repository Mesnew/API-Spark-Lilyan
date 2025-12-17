package siren

import siren.feedDB._

object dbcli extends App {
  val mysqlHost = sys.env.getOrElse("MYSQL_HOST", "db")
  val mysqlPort = sys.env.getOrElse("MYSQL_PORT", "3306")
  val dbURL = s"jdbc:mysql://$mysqlHost:$mysqlPort/"
  createSirenDB(dbURL: String)
  grantPrivileges(dbURL: String)
  createUniteLegaleTable(dbURL: String)
  insertUniteLegaleFile(dbURL: String)
}