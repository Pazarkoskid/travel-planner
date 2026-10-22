# AI Travel Planner Macedonia

Дипломски прототип според **Спецификација v1.1** (вклучително поглавје 23 — доверливи рецензии, фото-посети и беџови).

Платформа што создава персонализиран повеќедневен план низ Северна Македонија, го оптимизира редоследот на посети, го прикажува на карта и ги поврзува туристите со локално сместување, бродски тури, ресторани и такси.

**Клучен принцип:** AI никогаш не измислува места, цени, работно време или достапност. Моделот избира само меѓу записи од проверениот каталог (по ID), а серверот ги валидира сите резултати.

---

## Брз старт

### Опција А — Docker (PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1/
- Django admin: http://localhost:8000/admin/

Миграциите и демо податоците се полнат автоматски.

### Опција Б — локално (SQLite, без Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py fetch_images   # фотографии од Wikimedia Commons (потребен интернет)
python manage.py runserver

# Frontend (во друг терминал)
cd frontend
npm install
npm run dev
```

### Фотографии

`python manage.py fetch_images` за секое место и град ја наоѓа главната слободна (CC/PD) фотографија од англиската Wikipedia и ги зачувува URL-то, авторот и лиценцата. Авторите се прикажуваат на страницата „Извори на фотографии“ (`/credits`) и под фотографијата на секое место. Без интернет или без слика, интерфејсот прикажува уреден градиент. Слика може рачно да се смени во Django admin (полиња `image_url` и `image_credit`).

### Временска прогноза (OpenWeather)

1. Регистрирајте се на https://home.openweathermap.org/users/sign_up и отворете **API keys**. Клучот се активира за 10 мин до 2 часа.
2. Во главната папка `travel-planner-macedonia` копирајте `.env.example` во `.env` и пополнете:
   `OPENWEATHER_API_KEY=вашиот_клуч`
3. Рестартирајте го backend-от (`python manage.py runserver`). `.env` се чита автоматски.

Прогнозата се прикажува: на страницата на секое место (под картата), во планот (секој ден и под картата),
кај бродските тури (кај секое поаѓање) и на огласите (десно). Без клуч, администраторот гледа порака како да ја вклучи.

### Уредување на податоци

- **Администратор** (Админ → Каталог на места): цена, работно време, опис, статус, знаменитост, фотографија. При внес на цена или работно време автоматски се поставува датум на проверка.
- **Бизнис** (Бизнис-табла → „Уреди оглас, цени и работно време“): профил и телефон; сместување (опис, удобности, правила, цени и достапност по датум); ресторан (работно време по ден, мени со цени); бродска тура (опис, постојки со време, што е вклучено, поаѓања и откажување); такси (тарифи, возила, 0–24).
- Нов бизнис е „Чека одобрување“ и не е јавен додека администраторот не го одобри.

### UI/UX слики (лаптоп, таблет, телефон)

Скриптата `tools/screenshots.py` ги фотографира сите 25 екрани на три уреди и прави мокапи со рамки.

```powershell
pip install playwright pillow
python -m playwright install chromium
# backend и frontend треба да работат (runserver + npm run dev), со seed_demo податоци
python tools/screenshots.py --out ui-sliki
```

Резултат: `ui-sliki/laptop`, `ui-sliki/tablet`, `ui-sliki/phone` (екрани), `ui-sliki/mockups` (сите три уреди на една слика) и `ui-sliki/pregled-*.png` (преглед по уред). `--sample-weather` прикажува пример-прогноза ако нема клуч, `--only 01-pocetna,14-plan` прави само одредени екрани.

### Демо корисници (само за развој)

| Улога | Корисник | Лозинка |
|---|---|---|
| Турист | `turist` | `Turist12345!` |
| Сопственик/оператор | `host` | `Host12345!` |
| Администратор | `admin` | `Admin12345!` |

Туристот веќе има 3 одобрени фото-посети во Охрид (Св. Наум, Канео, Самуилова тврдина) → **3 од 10 = 30%** истраженост, и една завршена резервација за која може да остави проверена рецензија.

---

## Deploy: Supabase (база + фотографии) и Render (backend + frontend)

`render.yaml` во root е Render Blueprint: креира `travel-planner-api` (Django, gunicorn) и
`travel-planner-web` (React static site). Базата и качените фотографии се на Supabase.

**1. Supabase**
1. Нов проект, регион *Central EU (Frankfurt)*. Запиши ја лозинката на базата.
2. **Connect → Session pooler** → копирај го connection string-от
   (`postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-…pooler.supabase.com:5432/postgres`) и стави ја лозинката.
   Render нема IPv6, па *Direct connection* не работи; користи го pooler-от.
   Ако лозинката има `@ # / :` → URL-кодирај ги (`@` = `%40`) или смени лозинка без нив.
3. **Storage → New bucket** `media`, означи *Public bucket*.
4. **Storage → S3 Configuration**: копирај *Endpoint* и *Region*, па **New access key** → Access key ID и Secret.

**2. GitHub** — push на проектот (Render влече од GitHub).

**3. Render** → **New → Blueprint** → избери го repo-то → пополни ги вредностите:

| Сервис | Променлива | Вредност |
|---|---|---|
| api | `DATABASE_URL` | Session pooler string од чекор 1.2 |
| api | `SUPABASE_S3_ENDPOINT`, `SUPABASE_S3_REGION`, `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY` | од чекор 1.4 |
| api | `SEED_ADMIN_PASSWORD` | лозинка за `admin` (демо лозинката не важи на јавниот сајт) |
| api | `CORS_ALLOWED_ORIGINS` | `https://travel-planner-web.onrender.com` |
| api | `OPENWEATHER_API_KEY` | клучот (може и празно) |
| web | `VITE_API_URL` | `https://travel-planner-api.onrender.com` |

Ако Render даде друга адреса (името е зафатено), поправи ги `CORS_ALLOWED_ORIGINS` и `VITE_API_URL`
и направи **Manual Deploy** (за frontend е задолжително: адресата се вградува при build).

Build-от на backend сам прави: `collectstatic` → `migrate` → `secure_db` (RLS на сите табели, за Supabase
Data API да не ги открива податоците) → `seed_demo --if-empty` (само првиот пат) → `fetch_images`.

Ограничувања на бесплатните планови: Render free „заспива“ по 15 мин. (прво барање ~1 мин.);
Supabase free проект се паузира по 7 дена без активност.

## PWA (мобилна апликација)

- `frontend/public/sw.js`: service worker. Страниците и статиката се кешираат, а GET барањата до API
  работат по принципот „прво мрежа, офлајн последен одговор“. Затоа планот, местата и резервациите
  се гледаат и без интернет. Резервации и фото-посети (POST) секогаш бараат мрежа.
- `manifest.webmanifest`: икони, кратенки (Ново патување, Места, Мој пасош) и standalone приказ.
- На мобилен се појавува покана „Инсталирај“ (Android/Chrome); на iPhone упатство за „Додај на почетен екран“.
- Service worker-от се регистрира само во production build (`npm run build`), не во `npm run dev`.

## Јазици (македонски / англиски)

- Frontend: `t("македонски текст")` од `src/i18n.ts`; англискиот речник е во `src/i18n.en.ts`.
  Изборот (MK/EN во горната лента) се памти во прелистувачот. Без избор се зема јазикот на прелистувачот.
- Backend: frontend-от праќа `Accept-Language`, а `core/i18n.py` ги преведува генерираните текстови
  (причини во планот, предупредувања, белешки за пристапност, беџови, известувања, градови).
  OpenWeather ја враќа прогнозата на избраниот јазик.
- Имињата и описите на местата и огласите остануваат како што се внесени (македонски).

## Пристапни маршрути

- Секое место има `wheelchair` (YES / LIMITED / NO / UNKNOWN) и белешка (скали, калдрма, наклон).
  Почетните вредности за демо-местата се **проценки** (`destinations/accessibility_data.py`) и мора
  да се проверат. Админот ги менува во Админ → Каталог.
- Патување со „Намалена подвижност“ или „Инвалидска количка“: непристапните места се изоставаат
  (освен ако се означени како задолжителни, со предупредување), пристапните добиваат предност,
  времето за посета е ×1.25 / ×1.3, има едно место помалку дневно, а за делумно пристапните се
  прикажува предупредување со белешката.
- Филтер „Само пристапни“ во листата места (`/places/?accessible=1`).

## PDF извоз

- `GET /api/v1/trips/<id>/export/?format=pdf`: план по денови со времиња, причини, движење, трошоци,
  пристапност и предупредувања, на јазикот од `Accept-Language`. Фонтот е Onest (OFL, `core/assets/`),
  поради кирилицата.
- Ако е поставен `FRONTEND_URL`, PDF-от има QR-код до планот во апликацијата.

## Беџови и колекција

- Каталог: `backend/gamification/catalog.py` (40 градови/предели + достигнувања, правила за доделување).
- Слики: `frontend/public/badges/*.webp`, генерирани со `python tools/badges.py --src <папка со locations/>`.
- Миграцијата `gamification/0003_badge_catalog` го внесува каталогот; `python manage.py recompute_badges`
  го синхронизира и ги доделува заслужените беџови (безбедно при секој deploy).
- Правила: прва посета во град, посета на одредени места, N места од категорија, N фото-посети.
  Беџ без место во проверениот каталог е „Наскоро“ и не може да се освои.
- Страница: `/badges` (колекција, освоени во боја, неосвоени во сиво).

## Тестови

```bash
cd backend && pytest          # 46 тестови (+1 за PostgreSQL конкурентност)
cd frontend && npm test
```

Покриваат: двојно резервирање, капацитет на тури, ослободување капацитет, idempotency, дозволи меѓу бизниси, транзиции на статуси, рецензии само по COMPLETED и една по резервација, модерација, AI само со валидни IDs (и отфрлање непознати), fallback кога LLM е недостапен, оптимизатор не полош од baseline, фото-проверка по радиус, дупликати, напредок по уникатни места (10 фотографии од Канео = 1 место), беџ „Охрид 100%“, приватност на галерија и профил.

Тестот за вистинска конкурентност (две нишки за последното место) се извршува само на PostgreSQL:

```bash
POSTGRES_DB=travel POSTGRES_USER=travel POSTGRES_PASSWORD=... POSTGRES_HOST=localhost pytest
```

---

## Архитектура

| Слој | Технологија |
|---|---|
| Frontend | React 18 + TypeScript + Vite, React Router, Leaflet + OpenStreetMap |
| Backend | Django 5 + Django REST Framework, JWT (SimpleJWT) |
| База | PostgreSQL (Docker) / SQLite (локално) |
| AI | Опционален LLM (Anthropic) зад сервисен слој + детерминистички fallback |
| Оптимизација | Google OR-Tools (отворен TSP) + 2-opt fallback |
| Рутирање | Haversine проценка или OSRM (со timeout и fallback) |

### Django апликации

| Апликација | Модули од спецификацијата |
|---|---|
| `accounts` | User/UserProfile (улоги TOURIST/BUSINESS/ADMIN, јавен профил) |
| `destinations` | City, Place (извор, датум на проверка, листа знаменитости) |
| `businesses` | Business, BusinessUser, Accommodation, AccommodationUnit, AccommodationAvailability, RestaurantProfile, BoatTour, BoatDeparture, TaxiService |
| `reservations` | Reservation, ReservationItem, историја на статуси, атомски резервации |
| `reviews` | Review, BusinessReply, ReviewReport |
| `trips` | Trip, ItineraryDay, ItineraryItem, AIPlanRun, AI pipeline, OR-Tools |
| `gamification` | PhotoCheckIn, PlacePhoto, Badge, UserBadge, CityAchievement, PlaceReport |
| `notifications` | Notification |
| `core` | AuditLog, геофункции, рутирање, дозволи, аналитика, `seed_demo` |

Спецификацијата предвидува посебни апликации за ресторани/тури/такси — тука се споени во `businesses` за помалку дупликат-код; моделите се исти.

### AI pipeline (`backend/trips/planner.py`)

1. Валидација на влезот (датум, денови 1–10, гости, буџет, интереси).
2. Кандидати само од `Place.status = VERIFIED` во градот; рангирање по интереси, знаменитости, растојание и измени („поевтино“, „повеќе природа“…).
3. Цени/работно време се користат само ако се зачувани — инаку предупредување „потребна е потврда“.
4. Избор: LLM враќа JSON `{days: [{place_ids}]}` **или** детерминистички greedy-кластер избор.
5. Серверска валидација: непознати IDs се отфрлаат и се запишуваат во `AIPlanRun.rejected_ids`.
6. OR-Tools го подредува секој ден; оптимизираниот ред се прифаќа само ако не е полош од baseline.
7. Временски блокови, ручек кај најблискиот ресторан, предупредувања и метрики.

LLM се вклучува со `LLM_PROVIDER=anthropic` и `ANTHROPIC_API_KEY` во `.env`. Без клуч сè работи детерминистички.

### Резервации

- Капацитетот се зафаќа при барањето (PENDING) со **условен UPDATE** (`… WHERE available_units >= 1`) во трансакција — две паралелни барања не можат да го надминат капацитетот.
- REJECTED/CANCELLED го ослободуваат капацитетот.
- Цената се зачувува како snapshot (`total_price` + `ReservationItem` по ноќ).
- `idempotency_key` спречува двојно барање при повторен клик.
- COMPLETED е дозволено само по крајот на услугата; само тогаш е можна рецензија.

### Фото-посети и беџови

- GPS од уредот (при прикачување) е примарен доказ; во радиус од `checkin_radius_m` → автоматски APPROVED.
- Само EXIF → PENDING за рачна проверка (не се верува слепо). Без GPS → PENDING. Многу далеку → REJECTED.
- Дупликати (SHA-256) се одбиваат.
- Беџ по место еднаш (unique во базата); нивоа: Истражувач, Локален авантурист (5 места), Градски истражувач (50%), Мајстор на градот (100%), Истражувач на Македонија (100% во ≥3 града).
- Процентот = уникатни одобрени **задолжителни знаменитости** / сите задолжителни знаменитости. Листата ја одржува администраторот (`Place.is_required_landmark` во Django admin).

---

## API (префикс `/api/v1/`)

| Метод | Endpoint | Намена |
|---|---|---|
| POST | `auth/register/`, `auth/login/`, `auth/refresh/` | Регистрација и JWT |
| GET/PATCH | `auth/me/` | Сопствен профил |
| GET | `cities/`, `cities/{id}/places/` | Дестинации и места |
| GET | `places/?city=&category=&near=lat,lng&radius_km=` | Пребарување и близина |
| CRUD | `trips/` | Патувања (само сопствени) |
| POST | `trips/{id}/generate/`, `trips/{id}/revise/` | AI план / измена |
| GET | `trips/{id}/itinerary/`, `trips/{id}/evaluate/`, `trips/{id}/export/?format=csv` | План, метрики, извоз |
| GET | `accommodations/?city=&check_in=&check_out=&guests=&amenities=&max_total=` | Пребарување со вкупна цена |
| GET | `accommodations/{id}/availability/` | Достапност по ноќ |
| POST | `accommodation-bookings/`, `boat-reservations/`, `restaurant-reservations/`, `taxi-requests/` | Барања |
| GET | `boat-tours/`, `boat-departures/{id}/availability/`, `restaurants/`, `taxi-services/`, `businesses/` | Услуги |
| GET | `reservations/mine/` | Мои резервации |
| POST | `reservations/{id}/cancel/`, `reservations/{id}/accept/` | Откажување / прифаќање предлог |
| POST | `reservations/{id}/review/` | Рецензија (само COMPLETED) |
| GET | `businesses/{id}/reviews/` | Рецензии |
| POST | `reviews/{id}/reply/`, `reviews/{id}/report/` | Одговор / пријава |
| GET | `business/dashboard/`, `business/reservations/` | Бизнис-табла |
| PATCH | `business/reservations/{id}/` | `confirm`, `reject`, `propose`, `quote`, `start`, `complete`, `cancel` |
| POST | `business/units/{id}/availability/`, `business/boat-tours/{id}/departures/` | Управување со понуда |
| POST | `places/{id}/checkins/` | Фото-посета (multipart: `image`, `lat`, `lng`, `caption`, `is_public`) |
| GET | `places/{id}/gallery/`, `badges/`, `me/gamification/`, `users/{username}/` | Галерија, беџови, профили |
| GET | `weather/?city=` / `?place=` / `?lat=&lng=` | Прогноза (OpenWeather, кеш 30 мин) |
| GET | `boat-tours/{id}/`, `taxi-services/{business_id}/`, `restaurants/{business_id}/`, `accommodations/{id}/` | Детали за оглас |
| GET/POST | `business/my/` | Мои бизниси / нов бизнис |
| PATCH | `business/my/{id}/`, `business/my/{id}/restaurant/`, `business/my/{id}/taxi/`, `business/accommodations/{id}/`, `business/boat-tours/{id}/` | Уредување од бизнис |
| POST | `business/my/{id}/accommodations/`, `business/my/{id}/boat-tours/`, `business/departures/{id}/cancel/` | Нов оглас / тура, откажување поаѓање |
| GET/POST/PATCH | `admin/places/` | Каталог (админ): цени, работно време, статус |
| PATCH/DELETE | `photos/{id}/` · POST `photos/{id}/report/` | Приватност / пријава |
| GET/POST | `admin/analytics/`, `admin/checkins/`, `admin/place-reports/`, `admin/review-reports/`, `admin/businesses/…` | Модерација и аналитика |

Грешките имаат доследен формат: `{"error": {"code", "message", "details"}}`.

---

## Безбедност

- Дозволите се проверуваат на серверот (сопственост на патување, бизнис, резервација); туѓи ресурси враќаат 404.
- Rate limiting за најава, AI генерирање и прикачување фотографии.
- Тајни само во `.env`/environment; ништо во frontend или Git.
- Надворешни повици (LLM, OSRM) со timeout и fallback.
- Прикачени слики: валидација на формат и големина (8 MB), SHA-256 за дупликати.
- Не се чуваат платежни податоци.

## Познати ограничувања на прототипот

- Координатите во `data/seed_places.csv` се приближни; цените и работното време не се внесени (види `data/data_sources.md`).
- Бизнисите во seed-от се измислени демо записи означени „(демо)“.
- Растојанијата без OSRM се проценка од воздушна линија.
- PostGIS не е задолжителен: близината се пресметува со bounding box + Haversine (може да се замени со `ST_DWithin`).
- JWT се чува во localStorage — за продукција се препорачува httpOnly cookie.
- PDF извоз на план не е имплементиран (CSV е).
- Плаќања не се дел од MVP.

## Следни чекори (од спецификацијата)

PWA/мобилна апликација, албански и англиски интерфејс, плаќања, синхронизација со надворешни календари, временска прогноза, PDF извоз, пристапни маршрути.
