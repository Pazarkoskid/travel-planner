import { t } from "../i18n";
import { FormEvent, ReactNode, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../services/api";
import { ErrorBox, Field } from "../components/ui";

function AuthShell({ side, children }: { side: ReactNode; children: ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth-side">{side}</aside>
      <div className="auth-form">{children}</div>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      nav((loc.state as { from?: string })?.from || "/");
    } catch {
      setError(t("Корисничкото име или лозинката не се точни."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      side={
        <>
          <h2>{t("Вашите планови, резервации и печати се на едно место.")}</h2>
          <div className="small">
            <p>{t("Демо профили за тестирање:")}</p>
            <p>turist / Turist12345!<br />host / Host12345!<br />admin / Admin12345!</p>
          </div>
        </>
      }
    >
      <form className="stack" onSubmit={submit}>
        <h1>{t("Најава")}</h1>
        {error && <ErrorBox message={error} />}
        <Field label={t("Корисничко име")}>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </Field>
        <Field label={t("Лозинка")}>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? t("Се најавувате") : t("Најави се")}</button>
        <p className="small">{t("Немате профил?")} <Link to="/register">{t("Регистрирајте се")}</Link></p>
      </form>
    </AuthShell>
  );
}

export function Register() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "", role: "TOURIST" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register/", { method: "POST", json: form });
      await login(form.username, form.password);
      nav("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("Регистрацијата не успеа."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      side={
        <>
          <h2>{t("Туристите планираат. Локалните бизниси примаат барања.")}</h2>
          <p className="small">{t("Изберете „Сопственик или оператор“ ако нудите сместување, бродска тура, ресторан или такси. Бизнисот го одобрува администратор.")}</p>
        </>
      }
    >
      <form className="stack" onSubmit={submit}>
        <h1>{t("Регистрација")}</h1>
        {error && <ErrorBox message={error} />}
        <Field label={t("Корисничко име")}><input value={form.username} onChange={set("username")} autoComplete="username" required /></Field>
        <Field label={t("Е-пошта")}><input type="email" value={form.email} onChange={set("email")} autoComplete="email" required /></Field>
        <Field label={t("Лозинка")} hint={t("Најмалку 8 знаци, не само бројки.")}>
          <input type="password" value={form.password} onChange={set("password")} autoComplete="new-password" required />
        </Field>
        <Field label={t("Тип на профил")}>
          <select value={form.role} onChange={set("role")}>
            <option value="TOURIST">{t("Турист")}</option>
            <option value="BUSINESS">{t("Сопственик или оператор")}</option>
          </select>
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? t("Се креира профилот") : t("Креирај профил")}</button>
      </form>
    </AuthShell>
  );
}
