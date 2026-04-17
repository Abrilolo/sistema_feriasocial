import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.db.session import engine

tables = ["students","users","qr_tokens","checkins","registrations","projects","temp_codes"]

cmds = []
for t in tables:
    cmds.append(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
    cmds.append(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
    for role in ["anon", "authenticated"]:
        cmds.append(f"DROP POLICY IF EXISTS deny_{role}_{t} ON {t}")
        cmds.append(f"CREATE POLICY deny_{role}_{t} ON {t} FOR ALL TO {role} USING (false)")

ok = 0
warn = 0
with engine.connect() as conn:
    for cmd in cmds:
        try:
            conn.execute(text(cmd))
            ok += 1
        except Exception as e:
            print(f"WARN: {cmd[:60]} -> {str(e)[:100]}")
            warn += 1
    conn.commit()

print(f"Completado: {ok} OK, {warn} advertencias")

with engine.connect() as conn:
    r = conn.execute(text(
        "SELECT c.relname AS tablename, c.relrowsecurity AS rowsecurity, c.relforcerowsecurity AS forcerolesecurity "
        "FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' "
        "AND c.relname IN ('students','users','qr_tokens','checkins','registrations','projects','temp_codes') "
        "ORDER BY c.relname"
    ))
    print(f"\n{'Tabla':<20} {'RLS':<6} {'Forzado'}")
    print("-" * 35)
    for row in r:
        rls_status = "SI" if row.rowsecurity else "NO"
        force_status = "SI" if row.forcerolesecurity else "NO"
        print(f"{row.tablename:<20} {rls_status:<6} {force_status}")

print("\nListo. El backend sigue funcionando (usa conexion directa que bypasea RLS).")
print("La API REST publica de Supabase ya NO puede leer tus tablas.")
