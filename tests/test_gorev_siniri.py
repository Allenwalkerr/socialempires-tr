"""Görev sınırı (KMT-08, KAR-25): 6 saatte 3 görev, Odin heykeliyle 4.

Beklenen değerlerin kaynağı: 1.4.07 bayt kodu. Quest.DELAY_ALLOWED = 21600, Quest.MAX_QUESTS_ON_TIME = 4 (sınıf sabitleri);
Quest$/getNumQuestsAvailable@0-212: Main.lastQuestsTimes'ı azalan sıralar, şimdiden başlayıp her zamanı bir öncekiyle
karşılaştırır, fark DELAY_ALLOWED'dan küçük oldukça sayar; Odin heykeli varsa MAX - sayı, yoksa MAX - sayı - 1 döner.
Base/processAttacks@2085: Main.lastQuestsTimes = map.lastQuestTimes (get_player_info'dan; istemci listeye yazmaz).
Quest$/start@58: start_quest [görev, kasaba].
"""

from unittest import mock

from ortak import KomutTesti

T0 = 1_793_300_000


def istemcinin_kalan_hakki(zamanlar, simdi, odin=False):
    """Quest$/getNumQuestsAvailable'ın Python karşılığı (yukarıdaki bayt kodu)."""
    sayilan, onceki = [], simdi
    for t in sorted(zamanlar, reverse=True):
        if onceki - t < 21600:
            sayilan.append(t)
            onceki = t
        else:
            break
    return 4 - len(sayilan) - (0 if odin else 1)


class GorevSiniri(KomutTesti):
    def baslat(self, simdi, kasaba=0):
        with mock.patch.object(self.komutlar, "timestamp_now", lambda: simdi):
            self.komut("start_quest", 7, kasaba)

    def test_alti_saatte_uc_gorev(self):
        h = self.kayit["maps"][0]
        for i in range(3):
            self.assertGreater(istemcinin_kalan_hakki(h.get("lastQuestTimes", []), T0 + i * 60), 0, i)
            self.baslat(T0 + i * 60)
        self.assertEqual(h["lastQuestTimes"], [T0, T0 + 60, T0 + 120])
        self.assertEqual(istemcinin_kalan_hakki(h["lastQuestTimes"], T0 + 180), 0)  # 4. görev açılmaz
        self.assertEqual(istemcinin_kalan_hakki(h["lastQuestTimes"], T0 + 180, odin=True), 1)  # Odin heykeliyle 4
        self.assertEqual(istemcinin_kalan_hakki(h["lastQuestTimes"], T0 + 120 + 21600), 3)  # 6 saat sonra yeniden

    def test_liste_son_dort_baslangici_tutar_ve_kasabaya_yazilir(self):
        self.kayit["maps"].append(dict(self.kayit["maps"][0], id=1, lastQuestTimes=[]))
        for i in range(6):
            self.baslat(T0 + i, kasaba=1)
        self.assertEqual(self.kayit["maps"][1]["lastQuestTimes"], [T0 + 2, T0 + 3, T0 + 4, T0 + 5])
        self.assertNotIn(T0, self.kayit["maps"][0].get("lastQuestTimes", []))

    def test_bozuk_liste_duzelir(self):
        self.kayit["maps"][0]["lastQuestTimes"] = ["x", None, T0]
        self.baslat(T0 + 1)
        self.assertEqual(self.kayit["maps"][0]["lastQuestTimes"], [T0, T0 + 1])
