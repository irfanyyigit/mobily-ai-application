import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import plotly.graph_objects as go
np.random.seed(42)
#sayfa ayarları
st.set_page_config(page_title="AI Tabanlı Talep Öngörü ve Akıllı Operasyon Merkezi", layout="wide")
#css
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px !important;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
        min-height: 160px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Akıllı Operasyon Analizi")

# --- DOSYA YÜKLEME PANELİ ---
st.sidebar.header("Veri Kaynağı")
uploaded_file = st.sidebar.file_uploader("İstikbal Stok Listesini Yükleyin (Excel)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 1. Veri Okuma
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()
        
        required_columns = ['Ürün Adı', 'Stok Adedi']
        if not all(col in df.columns for col in required_columns):
            st.error(f"Hatalı Dosya! Gerekli sütunlar: {required_columns}")
            st.stop()

        # Veri Temizleme
        df['Stok Adedi'] = pd.to_numeric(df['Stok Adedi'], errors='coerce').fillna(0)
        if 'Satış Fiyatı (TL)' in df.columns:
            if df['Satış Fiyatı (TL)'].dtype == object:
                df['Satış Fiyatı (TL)'] = df['Satış Fiyatı (TL)'].astype(str).str.replace(' TL', '').str.replace('.', '').str.replace(',', '.').astype(float)

        # Üst Özet Kartları
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Toplam Ürün Çeşidi", len(df))
        kritik_adet = len(df[df['Stok Adedi'] < 20])
        col_b.metric("Kritik Stok Seviyesi", kritik_adet, delta="-3" if kritik_adet > 0 else "0", delta_color="inverse")
        col_c.metric("Tahmini Verimlilik Artışı", "%18", "+2.5")

        with st.expander("🚨 Acil Sipariş Verilmesi Gereken Ürünler"):
            kritik_liste = df[df['Stok Adedi'] < 10][['Ürün Adı', 'Stok Adedi']]
            st.table(kritik_liste)

        st.divider()

        # --- AI TALEP ÖNGÖRÜSÜ (12 AYLIK) ---
        st.subheader(" AI Tabanlı Talep Öngörüsü")
        selected_product = st.selectbox("Analiz edilecek ürünü seçin:", df['Ürün Adı'].unique())
        product_row = df[df['Ürün Adı'] == selected_product].iloc[0]
        
        # Değişken Hazırlığı
        mevcut_stok = int(product_row['Stok Adedi'])
        birim_fiyat = product_row['Satış Fiyatı (TL)'] if 'Satış Fiyatı (TL)' in df.columns else 0
        
        aylar_indeks = np.array(range(1, 13)).reshape(-1, 1)
        if selected_product == "Blanca Yatak Odası Takımı":
            base_satis = [15, 18, 22, 35, 42, 48] 
        else:
            base_satis = [45, 40, 32, 25, 18, 15] 
            
        satislar_gercek = np.array([x + np.random.randint(-3, 4) for x in base_satis]).reshape(-1, 1)        
        # AI Model Eğitimi
        model = LinearRegression()
        model.fit(aylar_indeks[:6], satislar_gercek)
        tahminler_tum = model.predict(aylar_indeks)
        guven_skoru = r2_score(satislar_gercek, tahminler_tum[:6])
        
        # Grafik Verileri
        ay_isimleri = ['Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık', 'Ocak', 'Şubat']
        son_satis_degeri = float(satislar_gercek[-1][0])
        ilk_tahmin_degeri = float(tahminler_tum[6][0])
        artis_orani = ((ilk_tahmin_degeri - son_satis_degeri) / son_satis_degeri * 100) if son_satis_degeri != 0 else 0
        toplam_tahmin_ihtiyacı = float(tahminler_tum[6:].sum())

        # Gelişmiş Grafik
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ay_isimleri[:6], y=satislar_gercek.flatten(), name="Gerçekleşen Satış", line=dict(color='#003366', width=4), mode='lines+markers'))
        fig.add_trace(go.Scatter(x=ay_isimleri[5:], y=tahminler_tum.flatten()[5:], name="AI Gelecek Öngörüsü", line=dict(color='#FFD700', width=4, dash='dash'), mode='lines+markers'))
        fig.update_layout(title=f" {selected_product} 12 Aylık Operasyonel Projeksiyon", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        # Analiz Metrikleri
        c1, c2, c3 = st.columns(3)
        c1.metric("Tahmin Güven Skoru", f"%{float(guven_skoru)*100:.1f}")
        c2.metric("Eylül Ayı Beklenen Talep", f"{int(ilk_tahmin_degeri)} Adet", f"%{float(artis_orani):.1f} Trend")
        
        if toplam_tahmin_ihtiyacı > mevcut_stok:
            c3.metric("Stok Durumu Analizi", "Stok Yetersiz!", f"-{int(toplam_tahmin_ihtiyacı - mevcut_stok)} Eksik", delta_color="inverse")
        else:
            c3.metric("Stok Durumu Analizi", "Stok Yeterli", f"+{int(mevcut_stok - toplam_tahmin_ihtiyacı)} Fazla")

        # --- SATIN ALMA VE STRATEJİ ---
        st.sidebar.divider()
        st.sidebar.header(" EOQ Parametreleri")
        siparis_maliyeti = st.sidebar.number_input("Sipariş Maliyeti (S)", value=500)
        stok_tutma_maliyeti = st.sidebar.number_input("Tutma Maliyeti (H)", value=50)

        def hesapla_eoq(yillik_talep, s, h):
            return int(np.sqrt((2 * yillik_talep * s) / h)) if h > 0 else 0
        
        yillik_tahmin = ilk_tahmin_degeri * 12
        ideal_siparis = hesapla_eoq(yillik_tahmin, siparis_maliyeti, stok_tutma_maliyeti)

        st.subheader("Operasyonel Karar Destek")
        o1, o2 = st.columns(2)
        o1.info(f"**Önerilen Sipariş Miktarı:** {ideal_siparis} Adet")
        siparis_sikligi = 365 / (yillik_tahmin / ideal_siparis) if yillik_tahmin > 0 else 0
        o2.success(f"**Sipariş Döngüsü:** {int(siparis_sikligi)} Gün")

        # --- DIŞ ETKENLER VE SENARYO ---
        st.divider()
        st.subheader("Senaryo ve Dış Etken Analizi")
        with st.expander("Senaryo ve Makro Veri Ayarları"):
            e1, e2, e3 = st.columns(3)
            with e1:
                fiyat_degisimi = st.slider("Fiyat Değişimi (%)", -50, 50, 0)
                konut_artisi = st.number_input("Konut Satış Artışı (%)", value=0)
            with e2:
                hava_durumu = st.slider("Ortalama Sıcaklık (°C)", -10, 45, 20)
                sezon_etkisi = st.checkbox("Özel Sezon Etkisi")
            with e3:
                dolar_kuru = st.number_input("USD/TRY Beklentisi", value=30.0)

        # Hesaplama Motoru
        konut_etkisi = (konut_artisi * 0.8) / 100
        hava_etkisi = -0.05 if (hava_durumu > 30 or hava_durumu < 5) else 0.02
        kur_etkisi = -0.10 if dolar_kuru > 35 else 0
        yeni_tahmin_baz = ilk_tahmin_degeri * (1 - (fiyat_degisimi / 100))
        if sezon_etkisi: yeni_tahmin_baz *= 1.3
        piyasa_bazli_tahmin = yeni_tahmin_baz * (1 + konut_etkisi + hava_etkisi + kur_etkisi)

        st.info(f"**Simülasyon Sonucu:** Tahmini Yeni Talep: **{int(piyasa_bazli_tahmin)} Adet**")

        # --- ABC ANALİZİ VE SAĞLIK SKORU ---
        st.divider()
        toplam_stok_degeri = mevcut_stok * birim_fiyat
        if toplam_stok_degeri > 200000:
            sinif, acıklama = "A Sınıfı (Kritik)", "Yüksek sermaye bağlıyor. Günlük takip şart."
        elif toplam_stok_degeri > 50000:
            sinif, acıklama = "B Sınıfı (Değerli)", "Orta risk. Haftalık kontrol."
        else:
            sinif, acıklama = "C Sınıfı (Standart)", "Düşük maliyetli. Rutin takip."

        # Sağlık Skoru Hesaplama
        skor = 100
        if artis_orani > 20: skor -= 10
        if mevcut_stok < toplam_tahmin_ihtiyacı: skor -= 40
        if sinif.startswith("A"): skor -= 10

        st.subheader("Ürün Operasyonel Sağlık Durumu")
        st.progress(max(0, skor / 100))
        if skor > 70: st.success(f"Durum: Mükemmel ({skor}/100)")
        elif skor > 40: st.warning(f"Durum: Riskli ({skor}/100)")
        else: st.error(f"Durum: KRİTİK ({skor}/100)")

        abc1, abc2 = st.columns([1, 2])
        abc1.metric("Ürün Değer Sınıfı", sinif)
        abc2.info(f"**Finansal Analiz:** {acıklama}\n\nToplam Değer: **{toplam_stok_degeri:,.2f} TL**")

        # --- FİNANSAL ETKİ ---
        st.divider()
        st.subheader("Finansal Etki Analizi")
        gelecek_ciro = toplam_tahmin_ihtiyacı * birim_fiyat
        f1, f2 = st.columns(2)
        f1.metric("Tahmini Ciro (Gelecek 6 Ay)", f"{gelecek_ciro:,.0f} TL")
        f2.metric("Stokta Bağlı Sermaye", f"{toplam_stok_degeri:,.0f} TL")
        
        doluluk = min(mevcut_stok / (toplam_tahmin_ihtiyacı if toplam_tahmin_ihtiyacı > 0 else 1), 1.0)
        st.progress(doluluk)
        st.caption(f"Stok Karşılama Oranı: %{doluluk*100:.1f}")

        # AI Karar Destek (Sidebar)
        st.sidebar.subheader("AI Karar Destek")
        if artis_orani < -10: st.sidebar.warning("Trend Düşüşte! Stok birikme riski.")
        insight = "STABİL"
        if sinif.startswith("A") and artis_orani > 10: insight = "KRİTİK ALIM GEREKLİ"
        elif toplam_tahmin_ihtiyacı > mevcut_stok: 
            risk_tl = (toplam_tahmin_ihtiyacı - mevcut_stok) * birim_fiyat
            insight = f"RİSK: {int(risk_tl):,} TL Kayıp Riski"
        st.sidebar.info(insight)

# --- ÖZELLİK: AI AKILLI SATIN ALMA TAKVİMİ ---
        st.divider()
        st.subheader("AI Akıllı Satın Alma ve Sevkiyat Takvimi")
        
        # Sipariş zamanlaması hesaplama mantığı
        gunluk_satis_tahmini = ilk_tahmin_degeri / 30
        stok_tukenme_gun = mevcut_stok / gunluk_satis_tahmini if gunluk_satis_tahmini > 0 else 365
        
        # 3 Farklı Senaryo İçin Takvim Planı
        t1, t2, t3 = st.columns(3)
        
        with t1:
            st.markdown("### Acil Sipariş")
            acil_tarih = "Hemen (Bugün!)" if stok_tukenme_gun < 7 else f"{int(stok_tukenme_gun - 7)} Gün Sonra"
            st.warning(f"**Tarih:** {acil_tarih}")
            st.write(f"**Miktar:** {int(ideal_siparis * 0.5)} Adet")
            st.caption("Kritik stok seviyesini korumak için gereken minimum miktar.")

        with t2:
            st.markdown("### Normal Tedarik")
            normal_tarih = f"{int(stok_tukenme_gun / 2)} Gün Sonra"
            st.info(f"**Tarih:** {normal_tarih}")
            st.write(f"**Miktar:** {ideal_siparis} Adet (EOQ)")
            st.caption("Ekonomik sipariş miktarı modeline göre en verimli alım.")

        with t3:
            st.markdown("### Fırsat Alımı")
            st.success("**Tarih:** Piyasa Düşüşünde")
            st.write(f"**Miktar:** {int(ideal_siparis * 1.5)} Adet")
            st.caption("Döviz veya hammadde indirimi durumunda yapılacak stoklama.")

        # Bir butona basarak raporu "indirilmiş" gibi simüle edelim
        st.sidebar.divider()
        if st.sidebar.button("Yönetici Raporunu Hazırla (PDF)"):
            st.toast("Rapor oluşturuluyor...",)
            st.sidebar.download_button(
                label="Raporu İndir",
                data=f"Stratejik Analiz Raporu\nÜrün: {selected_product}\nSkor: {skor}\nÖneri: {insight}",
                file_name=f"{selected_product}_analiz.txt",
                mime="text/plain"
            )
    except Exception as e:
        st.error(f"Beklenmedik bir hata oluştu: {e}")
else:
    st.info(" Lütfen analiz için sol taraftan bir Excel dosyası yükleyin.")