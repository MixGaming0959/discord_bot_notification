-- MySQL dump 10.13  Distrib 8.0.19, for Win64 (x86_64)
--
-- Host: localhost    Database: youtube_noti
-- ------------------------------------------------------
-- Server version	9.2.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `discord_mapping`
--

DROP TABLE IF EXISTS `discord_mapping`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `discord_mapping` (
  `ID` varchar(36) NOT NULL,
  `Discord_ID` varchar(36) NOT NULL,
  `Ref_ID` varchar(36) NOT NULL,
  `Type_Ref` varchar(20) NOT NULL,
  `is_NotifyOnLiveStart` tinyint DEFAULT (1),
  `Is_PreAlertEnabled` tinyint DEFAULT (0),
  PRIMARY KEY (`ID`),
  KEY `Discord_Mapping_DiscordServer_FK` (`Discord_ID`),
  CONSTRAINT `Discord_Mapping_DiscordServer_FK` FOREIGN KEY (`Discord_ID`) REFERENCES `discordserver` (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `discordserver`
--

DROP TABLE IF EXISTS `discordserver`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `discordserver` (
  `ID` varchar(36) NOT NULL,
  `GuildID` text NOT NULL,
  `ChannelID` text NOT NULL,
  `is_active` tinyint NOT NULL DEFAULT (1),
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `generation`
--

DROP TABLE IF EXISTS `generation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `generation` (
  `Id` varchar(36) NOT NULL,
  `Name` text,
  `Image` text,
  `GroupsID` varchar(36) DEFAULT NULL,
  `Another_Name` text,
  PRIMARY KEY (`Id`),
  KEY `Generation_groups_FK` (`GroupsID`),
  CONSTRAINT `Generation_groups_FK` FOREIGN KEY (`GroupsID`) REFERENCES `groups` (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `groups`
--

DROP TABLE IF EXISTS `groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `groups` (
  `Id` varchar(36) NOT NULL,
  `Name` text NOT NULL,
  `Another_Name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `livetable`
--

DROP TABLE IF EXISTS `livetable`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `livetable` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Title` text,
  `URL` text,
  `StartAt` datetime DEFAULT NULL,
  `Colaborator` text,
  `VtuberID` varchar(36) DEFAULT NULL,
  `Image` text,
  `IsMember` tinyint DEFAULT (0),
  `LiveStatus` varchar(20) DEFAULT NULL,
  `IsNoti` tinyint DEFAULT (0),
  PRIMARY KEY (`ID`),
  KEY `LiveTable_Vtuber_FK` (`VtuberID`),
  CONSTRAINT `LiveTable_Vtuber_FK` FOREIGN KEY (`VtuberID`) REFERENCES `vtuber` (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vtuber`
--

DROP TABLE IF EXISTS `vtuber`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vtuber` (
  `ID` varchar(36) NOT NULL,
  `Name` text,
  `GenID` varchar(36) DEFAULT NULL,
  `GroupsID` varchar(36) DEFAULT NULL,
  `YoutubeTag` text NOT NULL,
  `Image` text,
  `ChannelID` text NOT NULL,
  `IsEnable` tinyint DEFAULT (1),
  `subscribe_noti` tinyint DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `Vtuber_Gen_FK_1` (`GenID`),
  KEY `Vtuber_Groups_FK_2` (`GroupsID`),
  CONSTRAINT `Vtuber_Gen_FK_1` FOREIGN KEY (`GenID`) REFERENCES `generation` (`Id`),
  CONSTRAINT `Vtuber_Groups_FK_2` FOREIGN KEY (`GroupsID`) REFERENCES `groups` (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'youtube_noti'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-05-10 12:02:19
