# 1.4.07 hedef sistemi (GEC-07, 11.11.2026)

Yardımcı ajanın bayt kodu araştırması. **Doğrulama notu:** kodlanan iddialar yeniden okundu: GoalsManager/_load@64-70 (`orders` 0 ise atla) ✔, goalComparison (`order` farkı) ✔; sunucu tarafında reward_mission yalnızca `goals`a bakıyordu ✔, istemci config önbellek anahtarı ✔. Kayıttaki bilinmeyen kimliğin yok sayılması ajanın okumasıdır (✔ onun işaretiyle), yeniden okunmadı (◐).

# GEC-07 hedef sistemi araştırması (1.4.07 istemcisi)

İşaretler: ✔ bayt kodundan okundu, ◐ çıkarım, ? doğrulanamadı.

## 1. Hedefler config'ten nasıl okunuyor
- Kaynak config'in `goals` dizisi. `Base/loadGameConfigSuccess@588-601` → `GoalsManager.instance.initMissions(config.goals)` ✔. Başka çağıran yok (`initGoalManager` hiçbir yerden çağrılmıyor) ✔.
- `GoalsManager/initMissions` → `initDictionary` (tür adı → sınıf eşlemesi) → `_load` → `checkAllGoals` ✔.
- `GoalsManager/_load@50-208`: her kayıt için `orders == 0` ise atlanır (id 0 böyle elenir) ✔; `params` JSON.decode edilir, boşsa `{}` ✔; `createGoal(types, kayıt, params)` ile sınıf kurulur; tür sözlükte yoksa "Undefined goal type" izi basılıp hedef atılır (hata vermez) ✔; sonunda `sortGoals`.
- `AbstractGoal/<kurucu>@36-322`: `id`, `orders`, `min_level` parseInt; `title/description/instructions`, `image` (boş ya da "" değilse), `characters`; `reward` → tek `RewardResource('g', int)` ✔ (argüman sırası ◐).
- `orders`: yalnızca sıralama anahtarı. `sortGoals` karşılaştırıcısı `a.order - b.order` ✔ (`goalComparison@16-23`). Goals.json'da 205 hedefin hepsi `orders=1`, yani eşit; AS3 sort kararlı değil, gerçek sıra ◐.
- `min_level`: yalnızca `_minLevel`'a yazılıp `get minLevel` ile okunuyor; çağıran yok. `isGoalAvailable@2` hep `true` döner ✔. Yani seviye süzgeci istemcide YOK; min_level etkisiz.
- Eşzamanlı sayı: `MAX_ACTIVE_GOALS = 15` (`GoalsManager/<sınıf>@26-31`) ✔. `checkAllGoals@105-276`: sıralı listede gezer; ödülü alınmamış her hedefi `activate()` eder; tamamlanmamış olanları sayar ve `vActiveGoals`'a koyar; sayaç 15'e ya da liste sonuna varınca durur ✔. Sonraki hedefler, öncekiler tamamlanıp ödüllenince `checkAllGoals` ile açılır (sırayla açılma) ✔. Görev penceresi 5 satır gösterir, kaydırılır (`MissionPopup/refreshMissions@91-101`) ✔.

## 2. Tamamlanan / ödül alınan kayıt
- `privateState.completedMissions` ve `privateState.rewardedMissions`: tam sayı kimlik dizileri ✔ (`Base/loadPlayerInfoSuccess@659-785`: `for each` ile değerler `Main.completedMissions[id]=true` / `Main.rewardedMissions[id]=true` sözlüğüne konur).
- Eşleme config'le değil kimlikle: `AbstractGoal/isCompleted` ve `get rewarded` bu sözlüklere bakar ✔.
- Config'te olmayan kimlik: `GoalsManager/initPlayerData@85-116` `_goalsById[id]` boşsa atlar ✔; `checkAllGoals` yalnızca `goalList` üstünde gezer ✔. Sonuç: yok sayılır, hata yok. Kalıntı kayıtta kalır, sunucu `save`'e dokunmadıkça silinmez.
- Tamamlanmış ama ödülü alınmamış (completed var, rewarded yok) hedef yüklemede `activate → checkComplete` ile hemen ödüllenir ve `reward_mission` gider ✔.

## 3. Komutlar ve ödül
- Tamamlanma: `AbstractGoal/checkComplete@36-198` → `completedMissions[id]=true`, `rewardMission(id)`, `complete_mission` args `[id, 0]` ✔.
- Ödül: `AbstractGoal/rewardMission@75-109` → `rewardedMissions[id]=true`, `reward_mission` args `[townID.id, id]` ✔ (belge `docs/inceleme/1407-komutlar.md` ile uyumlu).
- Miktar istemcinin kendi config `reward` değerinden (`onReward@161`: `Player.rewards[0].amount` altın olarak yerelde eklenir, ◐ sıra) ✔; sunucu `reward_mission` (`oyun/komutlar.py:1186`) aynı değeri `config["goals"]`'tan okur. Tür yalnız altın (`'g'`) ✔.
- Cash ile atlama düğmesi `Config.CAN_PAY_FOR_GOALS` kapalıysa gizli (`MissionPopup/openInfoPopup@483`) ✔.

## 4. types / params
- Tür → sınıf: `GoalsManager/initDictionary@16-937` ✔. Desteklenenler: built_id, built_subcatfunc, trained_id, subcatfunc_count, contained_id/contained_subcatfunc, building_contains_units, collected_id/collected_subcatfunc/collected_resource_id, captured_subcatfunc, destroyed_id, rename_empire, population, select_time_*, zoom, move_*, recruit_market_friend, popup_opened_*, player_stats_modified, daily_bonus, attack_player, market_trade, store_subcatfuncs, complete_social_*, assaults_won, complete_quest, pop_unit_subcatfunc, own_big_tiles, repair_building, assist_neighbour_buildings, train_ids_in_id, units_in_refuge, end_assaults_same_level, place_stored_item, sacrifice_unit, convert_unit, heal_units_with_healing_spring, kill_tower_with_scorpion, killed_enemy, select_unit_kill_enemy, use_selection_tool, help_friend_id, dragons_nest_*, double_click, soulmixer_mix_unit, buy_unit_pack.
- İlerleme sayacı yalnızca bellekte: `_currentStep` (`GoalConstructBuilding/onBuild@56-63`, `GoalCollectResource/onCollect`, `GoalCollectBuilding/onCollect`) ✔. Kayıtta yok; oturum kapanınca sıfırlanır. Hedef bitince sinyal kaldırılır, `checkComplete` çalışır.
- `params`: `ids` (öğe kimlikleri), `ammount` (adet; yazım böyle), `upgrade_from` (-1 = yeni kurma) ✔; collected_subcatfunc `{"id":alt_kategori,"ammount":n}`.
- Bayram için uygun: `built_id` (belli yapı kur, ör. `{"ids":[..],"ammount":1,"upgrade_from":-1}`), `collected_id`/`collected_subcatfunc` (toplama), `trained_id`. Uygunsuz: kayıttan türeyen durumu bekleyenler (çok oyunculu/arkadaş, saldırı) çünkü sayaç oturum içi.

## 5. image / characters
- Kurucuda `_imgName`, `_character`; `MissionPopup/openInfoPopup@429-465` → `ImageManager.getLocalitzationImage(ad)` ✔. Ad config `images` sözlüğünde olmalı, yoksa "DOES NOT EXIST IN THE IMAGES JSON" ve boş resim. Yol: `apfx + 'images_new/' + (değer ? değer+'/' : '') + ad` ✔. `hedefleri_ekle` (oyun/config.py:98) eksik adları `images`'a `""` ile ekliyor.
- Mevcut resimler (goals.json): `image`: goal_001..goal_103.jpg (çoğu tek), `goal_008_.jpg`, `goal_256.jpg`, `goal_260.jpg`, `goal_262.jpg`; `goal_059.jpg` 8 hedefte ortak; 106 hedefte "none". `characters`: nino_00.png ... nino_24.png (25 resim), 1 hedefte "none". Dosyalar depoda yok, oyun sunucusundan gelir. Bayram hedefi için örnek: `goal_059.jpg` + herhangi bir `nino_XX.png` ya da yapıya uygun mevcut `goal_0XX.jpg`.

## 6. Oturum içi değişiklik
- Hedefler yalnızca config yüklenirken bir kez okunuyor (`initMissions` tek çağrı yeri) ✔. Oturum ortasında config değişse istemci görmez; eklenen hedef bir sonraki girişte, kaldırılan sonraki girişte etkili. Oturum açıkken bayram biterse hedef istemcide kalır; tamamlanırsa `reward_mission` gelir.

## 7. Öneri
- id: 1008'in (en büyük mevcut) ve eski numara tablosunun (`config/gorev_gocu.json`, 1-1008) üstünde, örn. her bayrama blok: Ramazan 5001-5009, Kurban 5011-5019... (kimlik kısıtı yok, `id>5` dışında; ✔). Yıllık tekrar için ya aynı kimlik + bitişte temizlik ya da yıla göre blok.
- orders: sıfır olamaz (elenir). Tüm mevcutlar 1; bayram hedefi başa gelsin diye -1 (parseInt ≠ 0, sıralamada öne) ◐. `min_level`: 1 (etkisiz). 15 açık hedef sınırı var; bayram hedefi sayıyı doldurmasın, 1-3 hedef yeter.
- ödül: yalnız `reward` (tam sayı altın). `types` `built_id`/`collected_id`/`trained_id`; `params` JSON dizesi; `title/description` doğrudan Türkçe (ceviri hattına güvenme); `instructions` "".
- Sunucu: `get_client_game_config` kopyasına bayramdaysa hedefleri ekle (takvim.json'daki `gun/once/sure` mantığı hazır). Önbellek anahtarına (config.py:188) etkin bayram hedef kimlikleri girmeli, yoksa bayram bitince eski liste servis edilir. `reward_mission` (komutlar.py:1193) yalnız `__game_config["goals"]`'a baktığı için bayram hedefini bulamaz ve 0 altın yazar; bayram hedeflerini de aramalı (bayram bitince açık oturumda tamamlanan için de).
- Temizlik: bayram bitince hedef config'ten çıkınca kayıttaki kalıntı zararsız (yok sayılır, ✔). Ama aynı kimlik gelecek yıl yeniden kullanılacaksa, kayıt yüklemede (oyun/kayit.py `_yukleme_duzeltmeleri`) bayram bloğundaki kimlikleri `completedMissions` ve `rewardedMissions`'tan, bayram aktif değilken, silmek gerekir; yoksa hedef "ödenmiş" sayılıp görünmez.
- Riskler: (1) ilerleme bellekte, oturum içi kurmaya bağlı: bayram öncesi kurulmuş yapı sayılmaz (built_id) ◐; (2) tür adı yanlışsa hedef sessizce atılır; (3) resim adı `images`'ta yoksa boş görünür; (4) `orders` -1'in gerçek sıralamasını çalıştırarak doğrulamadım (?); (5) completed var rewarded yok kalırsa her girişte yeniden ödüllenir (komut tekrarında `reward_mission` çift ödülü `rewardedMissions` kontrolüyle engelliyor).
