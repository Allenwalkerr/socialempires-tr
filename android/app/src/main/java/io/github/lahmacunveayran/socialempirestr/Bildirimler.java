package io.github.lahmacunveayran.socialempirestr;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Yerel bildirimler (ONR-03, KAR-21, KAR-23): üretim hazır, eğitim bitti, kalkan bitiyor, saldırıya uğradın.
 * İnternet gerekmez. Zamanları oyun/bildirim.py hesaplar; simge oyunun kendi simgesidir (templates/img/simge-192.png,
 * araclar/android_paketi.py onu mipmap/ic_launcher yapar).
 *
 * Zamanı belli olanlar uygulama arka plana geçerken AlarmManager'a kurulur (uygulama kapansa da gelir) ve uygulama
 * yeniden öne gelince iptal edilir. Saldırı, bot dünyası arka planda çalışırken olur; Python {@link #saldiri} çağırır.
 */
public final class Bildirimler {
    private static final String TAG = "SocialEmpires";
    private static final String KANAL = "oyun";
    /** oyun/bildirim.py EN_COK ile aynı: iptal ederken bu kadar kimliğe bakılır. */
    private static final int EN_COK = 20;
    private static final int SALDIRI_KIMLIGI = 1000;
    private static final String EK_KIMLIK = "kimlik";
    private static final String EK_METIN = "metin";

    static volatile Context uygulama;
    static volatile boolean onde;

    private Bildirimler() {
    }

    static void hazirla(Context baglam) {
        uygulama = baglam.getApplicationContext();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel kanal = new NotificationChannel(KANAL,
                    baglam.getString(R.string.bildirim_kanali), NotificationManager.IMPORTANCE_DEFAULT);
            baglam.getSystemService(NotificationManager.class).createNotificationChannel(kanal);
        }
    }

    /** Android 13 ve sonrasında kullanıcı bildirim iznini vermediyse hiçbir şey gösterilmez. */
    static boolean izinVar(Context baglam) {
        return Build.VERSION.SDK_INT < 33
                || baglam.checkSelfPermission("android.permission.POST_NOTIFICATIONS") == PackageManager.PERMISSION_GRANTED;
    }

    static void goster(Context baglam, int kimlik, String metin) {
        if (!izinVar(baglam)) {
            return;
        }
        Intent ac = new Intent(baglam, MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent dokununca = PendingIntent.getActivity(baglam, 0, ac,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(baglam, KANAL) : new Notification.Builder(baglam);
        b.setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(baglam.getString(R.string.uygulama_adi))
                .setContentText(metin)
                .setStyle(new Notification.BigTextStyle().bigText(metin))
                .setContentIntent(dokununca)
                .setAutoCancel(true);
        baglam.getSystemService(NotificationManager.class).notify(kimlik, b.build());
    }

    /** Python (android_giris, oyun.bildirim.saldiri): oyuncu bot akınına uğradı. Uygulama öndeyse gösterilmez. */
    public static void saldiri(String metin) {
        Context baglam = uygulama;
        if (baglam == null || onde) {
            return;
        }
        try {
            goster(baglam, SALDIRI_KIMLIGI, metin);
        } catch (RuntimeException hata) {
            Log.w(TAG, "Saldiri bildirimi gosterilemedi", hata);
        }
    }

    private static PendingIntent alarm(Context baglam, int kimlik, String metin, int bayrak) {
        Intent i = new Intent(baglam, Alici.class).putExtra(EK_KIMLIK, kimlik);
        if (metin != null) {
            i.putExtra(EK_METIN, metin);
        }
        return PendingIntent.getBroadcast(baglam, kimlik, i, bayrak | PendingIntent.FLAG_IMMUTABLE);
    }

    /** onStop: JSON [{kimlik, zaman (sn), metin}] (android_giris.bildirimler). Kesin zaman izni istemez; Android
     * pil için birkaç dakika geciktirebilir. */
    static void kur(Context baglam, String json) {
        if (onde) { // hesap sürerken oyuncu döndüyse kurulmaz (onStart zaten iptal etti)
            return;
        }
        iptal(baglam);
        AlarmManager am = baglam.getSystemService(AlarmManager.class);
        try {
            JSONArray liste = new JSONArray(json);
            for (int n = 0; n < liste.length() && n < EN_COK; n++) {
                JSONObject o = liste.getJSONObject(n);
                int kimlik = o.getInt("kimlik");
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, o.getLong("zaman") * 1000L,
                        alarm(baglam, kimlik, o.getString("metin"), PendingIntent.FLAG_UPDATE_CURRENT));
            }
            Log.i(TAG, "Bildirim kuruldu: " + Math.min(liste.length(), EN_COK));
        } catch (JSONException hata) {
            Log.w(TAG, "Bildirim listesi okunamadi", hata);
        }
    }

    /** onStart: oyuncu döndü; kurulu bildirimler ve ekrandakiler kalkar. */
    static void iptal(Context baglam) {
        AlarmManager am = baglam.getSystemService(AlarmManager.class);
        for (int kimlik = 1; kimlik <= EN_COK; kimlik++) {
            PendingIntent p = alarm(baglam, kimlik, null, PendingIntent.FLAG_NO_CREATE);
            if (p != null) {
                am.cancel(p);
                p.cancel();
            }
        }
        baglam.getSystemService(NotificationManager.class).cancelAll();
    }

    /** Zamanı gelen bildirim (AlarmManager). Uygulama kapalıyken de çalışır. */
    public static final class Alici extends BroadcastReceiver {
        @Override
        public void onReceive(Context baglam, Intent niyet) {
            String metin = niyet.getStringExtra(EK_METIN);
            if (metin != null && !onde) {
                hazirla(baglam);
                goster(baglam, niyet.getIntExtra(EK_KIMLIK, 1), metin);
            }
        }
    }
}
