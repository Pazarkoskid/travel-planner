"""Вклучува Row Level Security на сите табели во public шемата (Supabase).

Supabase ги изложува табелите од `public` преку Data API (PostgREST) за улогите anon/authenticated.
Django не го користи тој API, па RLS без политики значи: REST пристапот не гледа ништо,
а Django (сопственик на табелите) работи нормално, бидејќи сопственикот го заобиколува RLS.

    python manage.py secure_db
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Вклучи RLS на сите табели во public (заштита од Supabase Data API)."

    def handle(self, *args, **opts):
        if connection.vendor != "postgresql":
            self.stdout.write("Не е PostgreSQL — прескокнато.")
            return
        with connection.cursor() as cur:
            cur.execute("""SELECT tablename FROM pg_tables
                           WHERE schemaname = 'public' AND tableowner = current_user AND NOT rowsecurity""")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                cur.execute(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY')
        self.stdout.write(self.style.SUCCESS(f"RLS вклучен на {len(tables)} табели."))
