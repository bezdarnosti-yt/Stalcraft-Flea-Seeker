#pragma once
#include <iostream>
#include <map>

const std::string PRODUCTION_API = "https://eapi.stalcraft.net";

const std::string ITEMS_LISTING_URL = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru/listing.json";

const std::string ICON_BASE_URL = "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database/main/ru";

const std::string ICON_CACHE_DIR = "icons";

const int UPGRADE_ANY = -1;

const std::map<std::string, std::string> QUALITY_MAP {
    {"DEFAULT", "Обычный"},
    {"RANK_NEWBIE", "Новичок"},
    {"RANK_STALKER", "Сталкер"},
    {"RANK_VETERAN", "Ветеран"},
    {"RANK_MASTER", "Мастер"},
    {"RANK_LEGEND", "Легенда"},  
};

const std::map<std::string, std::string> QUALITY_HEX {
    {"DEFAULT", "#939393"},
    {"RANK_NEWBIE", "#4ad94b"},
    {"RANK_STALKER", "#5555ff"},
    {"RANK_VETERAN", "#940394"},
    {"RANK_MASTER", "#d14849"},
    {"RANK_LEGEND", "#ffaa00"},  
};
