/**
 * @file sql_postgre.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-11-23
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <iostream>
#include <pqxx/pqxx>

void postgreConnectionTest() {

  try {
    // Establish a connection to the PostgreSQL database
    pqxx::connection conn(
      "dbname=gs user=gsadmin password=5002 hostaddr=127.0.0.1 port=5432"
      );
    pqxx::work txn(conn); // Create a transaction
    pqxx::result result = txn.exec("SELECT user_id, user_name FROM userinfo");

    // Process the query result
    for (const auto &row : result)
    {
      std::cout << "User ID: " << row["user_id"].as<int>() << ", User Name: " << row["user_name"].as<std::string>() << std::endl;
    }

    txn.commit();
  } catch (const std::exception &e) {
    std::cerr << "Error: " << e.what() << std::endl;
    throw 1;
  } catch (...) {
    std::cerr << "Unknown error from out of std" << std::endl;
    throw 2;
  }
  
}