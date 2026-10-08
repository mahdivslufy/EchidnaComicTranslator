# EchidnaComicTranslator 🛸📖
**موتور خودکار و صفر تا صد ترجمه، پاک‌سازی و تایپ‌ستینگ کمیک و مانگا با هوش مصنوعی**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Autonomous Scanlation](https://img.shields.io/badge/Scanlation-Zero--Ghosting-purple.svg)]()

موتور `EchidnaComicTranslator` یک پایپ‌لاین ماژولار و پرسرعت برای بومی‌سازی و اسکن‌لیشن انواع کمیک‌های غربی، مانگا و مانهوا به زبان فارسی است که ضعف‌های بزرگ ابزارهای قبلی (کندی مفرط، کج شدن متون، پاک نشدن نوشته‌های خارج بالون و آرتیفکت‌های تصویری) را با رویکرد بینایی ماشین ترکیبی و محاسبات هندسی ممان برطرف کرده است.

---

## 🌟 ویژگی‌های برجسته (Key Features)

1. **تشخیص یکپارچه حباب‌ها و متن‌های آزاد (All-in-One Vision Extraction):**
   * تشخیص هم‌زمان بالون‌های گفت‌وگو (`speech`)، حباب‌های فریاد مضرس (`scream`)، باکس‌های راوی مستطیلی (`narration`) و افکت‌های صوتی پس‌زمینه (`SFX`).
   * عدم نادیده گرفتن متون محیطی و افکت‌های صوتی.

2. **پاک‌سازی بدون شبح و حفظ خطوط مرزی (Ghost-Free Adaptive Inpainting):**
   * تفکیک هوشمند جوهر متن از مرزهای خارجی بالون با تحلیل مولفه‌های متصل (`Connected Components`).
   * بازسازی پس‌زمینه با الگوریتم Inpainting بدون به جا گذاشتن لکه‌های خاکستری یا محوشدگی‌های زشت.

3. **مرکزسنجی ریاضی و بالانس هندسی (Mathematical Centroid Typesetting):**
   * حل قطعی مشکل کج‌شدن متن در حباب‌های بیضی و دم‌دار: فرسایش مورفولوژیک دم حباب (`Morphological Erosion`) و محاسبه دقیق مرکز ثقل بیضی از طریق ممان‌های تصویر ($M_{10}/M_{00}, M_{01}/M_{00}$).
   * محاسبه داینامیک بهترین سایز فونت و خط‌شکنی متقارن متناسب با شکل بالون.

4. **ترجمه با حفظ لحن اورجینال و شخصیت‌پردازی (Character-Faithful Translation):**
   * حفظ اصالت لحن کارهای دارک و کمدی بزرگسالانه (مثل ریک و مورتی، تپق‌های عصبی مورتی، تیکه‌ها و الفاظ تند ریک بدون سانسور).

5. **پشتیبانی کامل و نیتیو از رسم‌الخط راست‌به‌چپ (True RTL & Bidi):**
   * اتصال مستقیم به `arabic_reshaper` و موتور BiDi جهت جلوگیری از چسبیدن یا برعکس شدن حروف فارسی با فونت استاندارد وزیر (`Vazir-Bold`).

6. **پشتیبانی از آرشیوهای کمیک (Direct CBZ / CBR / Images):**
   * استخراج خودکار صفحات از فایل `.cbz`، ترجمه موازی و بسته‌بندی مجدد در قالب فایل نهایی آماده تحویل.

---

## 🚀 نصب و راه‌اندازی (Quick Start)

### پیش‌نیازها:
* پایتون نسخه ۳.۱۱ یا بالاتر
* دسترسی به پراکسی یا API محلی (مثل `9Router` روی پورت `20128`)

```bash
git clone https://github.com/mahdivslufy/EchidnaComicTranslator.git
cd EchidnaComicTranslator
pip install -r requirements.txt
```

---

## 💻 نحوه استفاده (Usage)

### ۱. ترجمه یک فایل کمیک کامل (`CBZ`):
```bash
python main.py --cbz "input_comic.cbz" --out-cbz "output_persian.cbz"
```

### ۲. ترجمه با محدود کردن تعداد صفحات (مثلاً تست ۵ صفحه اول):
```bash
python main.py --cbz "input_comic.cbz" --out-cbz "output_sample.cbz" --limit 5
```

### ۳. ترجمه تک‌صفحه (تصویر تکی):
```bash
python main.py --image "page_001.jpg" --out "page_001_persian.jpg"
```

---

## 🛠️ ساختار ماژولار پروژه

```
EchidnaComicTranslator/
├── main.py              # اسکریپت اصلی موتور و CLI
├── requirements.txt     # کتابخانه‌های لازم (OpenCV, Pillow, BiDi, etc.)
├── .gitignore           # نادیده گرفتن کش و فایل‌های سنگین
└── README.md            # مستندات و راهنمای پروژه
```

---

## 📜 مجوز (License)
این پروژه تحت مجوز MIT منتشر شده است.
