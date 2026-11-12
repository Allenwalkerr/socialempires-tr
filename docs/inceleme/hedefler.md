# Hedefler (goals) incelemesi, 12.11.2026

Sahibinin istediği: "görevleri kapsamlı bir şekilde irdele". Kaynak: 1.4.07 bayt kodu, `config/goals.json` (206 hedef).

## İstemci hedefleri nasıl işler

- **Gösterim:** `GoalsManager/checkAllGoals` @50-276 hedefleri `order`'a (AbstractGoal/<kurucu> @49-60:
  `parseInt(orders)`) göre sıralar, ödülü alınmamış ilk `MAX_ACTIVE_GOALS` (15) hedefi gösterir.
  `isGoalAvailable` her zaman true; `min_level`'e bakılmaz. Seviye kapısı sunucuda (DNT-51,
  `oyun/hedef_seviye.py`: istemciye yalnızca oyuncunun seviyesine gelmiş hedefler gider).
- **Ok (yönlendirme):** hedef penceresinde ok düğmesi hedefin `tutorialized` olduğu ve kimliği 5'ten
  büyük olduğu durumda çıkar (`MissionPopup/onTutorializeClick` @45-73). `tutorialized` değerini her hedef sınıfı
  kendisi koyar; okun yokluğu bazı türlerde oyunun kendi tasarımıdır (aşağıdaki tablo, `startBasicTutorial`).
- **Uyarı:** ok, istenen bina haritada yoksa "Gereken bina sende yok" der (`loc:GOALS_GENERAL_BUILDING_NOT_FOUND`,
  ör. `GoalOpenSocialSubcat`, `GoalBuildingSubcatContainSubcat`). Pazarın üç hedefi (50 kur, 51 dost bul,
  53 aç) birlikte görünebilir; 51 ve 53 pazar kurulmadan bu uyarıyı verir. Bu istemcinin kendi davranışı.
- **Tamamlanma:** her sınıf bir sinyali dinler; tamamlanınca istemci `complete_mission` yollar, sunucu
  `completedMissions`'a yazar. Örnekler:
  - `population` (`GoalPopulation`): `PlayerStatus/updatePopulation`'ın yolladığı birlik nüfusu
    (iPopulationCount toplamı), nüfus sınırı değil (CEV-08).
  - `player_stats_modified` (`GoalAdjustStats`): `PlayerStatus/adjustStats`'ın `SIG_PLAYER_STATS_ADJUST`
    sinyali; nakit bu yoldan düşmeyen bir harcama sayılmaz (sahibinin "1 nakit harcadım sayılmadı" bildirimi
    araştırılıyor: hangi harcama olduğu sorulacak).

## Tür tablosu

| Tür | Hedef | İstemci sınıfı | Ok |
| --- | ---: | --- | --- |
| `built_id` | 69 | `GoalConstructBuilding` | var |
| `trained_id` | 16 | `GoalTrainedUnit` | var |
| `complete_quest` | 16 | `GoalCompleteQuest` | var |
| `built_subcatfunc` | 13 | `GoalConstructBuildingSubcat` | var |
| `contained_id` | 12 | `GoalBuildingContainUnit` | var |
| `complete_social_id` | 10 | `GoalOpenSocialBuilding` | var |
| `collected_id` | 8 | `GoalCollectBuilding` | var |
| `attack_player` | 8 | `GoalAssaultsStarted` | var |
| `collected_subcatfunc` | 5 | `GoalCollectBuildingSubcat` | var |
| `killed_enemy` | 5 | `GoalKillEnemy` | var |
| `contained_subcatfunc` | 4 | `GoalBuildingSubcatContainSubcat` | var |
| `market_trade` | 3 | `GoalMarketTrade` | var |
| `own_big_tiles` | 3 | `GoalOwnGrid` | var |
| `select_time_subcatfunc` | 2 | `GoalSelectTimeSubcat` | var |
| `popup_opened_collections` | 2 | `GoalOpenPopupCollections` | var |
| `assaults_won` | 2 | `GoalAssaultsWon` | var |
| `train_ids_in_id` | 2 | `GoalBuildingTrainsUnit` | var |
| `none` | 1 | `None` | yok |
| `subcatfunc_count` | 1 | `GoalTrainedUnitSubcat` | yok |
| `zoom` | 1 | `GoalZoomUsed` | yok |
| `dragons_nest_feed` | 1 | `GoalDragonsNestFeed` | var |
| `pop_unit_subcatfunc` | 1 | `GoalBuildingSubcatPopUnit` | var |
| `double_click` | 1 | `GoalDoubleClick` | var |
| `captured_subcatfunc` | 1 | `GoalCapturedSubcat` | var |
| `rename_empire` | 1 | `GoalEmpireRenamed` | var |
| `move_subcatfunc_building` | 1 | `GoalMoveBuildingSubcat` | var |
| `buy_unit_pack` | 1 | `GoalBuyUnitPack` | var |
| `soulmixer_mix_unit` | 1 | `GoalSoulMixerGet` | yok |
| `use_selection_tool` | 1 | `GoalSelectionTool` | var |
| `help_friend_id` | 1 | `GoalVisitedFriends` | var |
| `select_time_id` | 1 | `GoalSelectTime` | var |
| `recruit_market_friend` | 1 | `GoalFriendsInBuilding` | var |
| `player_stats_modified` | 1 | `GoalAdjustStats` | yok |
| `complete_social_subcat` | 1 | `GoalOpenSocialSubcat` | var |
| `population` | 1 | `GoalPopulation` | var |
| `store_subcatfuncs` | 1 | `GoalStoreItemSubcat` | var |
| `popup_opened_quests` | 1 | `GoalOpenPopupQuests` | var |
| `repair_building` | 1 | `GoalRepairBuilding` | var |
| `assist_neighbour_buildings` | 1 | `GoalFriendAssist` | var |
| `kill_tower_with_scorpion` | 1 | `GoalScorpionKilledTowerStar` | yok |
| `sacrifice_unit` | 1 | `GoalSacrificeUnit` | var |
| `convert_unit` | 1 | `GoalConvertUnit` | yok |
| `heal_units_with_healing_spring` | 1 | `GoalUnitHealed` | var |

## Çevrimdışı yapılabilirlik

- Görev adası hedeflerinin (complete_quest) adalarının hepsi `villages/quests`'te var.
- "Ziyaret et" (44) 100000030-32: oyunun kendi Arthur köyleri (`villages/Arthur30-32.json`).
- Dost isteyen hedefler (complete_social_id, complete_social_subcat, recruit_market_friend): botlarla (DNT-52).
- Saldırı hedefleri (attack_player, assaults_won): PvP ve görev adaları; seviye kapısı 8 ve 6 (DNT-51).
