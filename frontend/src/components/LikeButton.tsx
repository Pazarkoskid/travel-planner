import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { api } from "../services/api";
import { t } from "../i18n";
import Icon from "./Icon";

export default function LikeButton({ id, count, liked }: { id: number; count: number; liked: boolean }) {
  const { user } = useAuth();
  const [state, setState] = useState({ count, liked });
  const [busy, setBusy] = useState(false);
  if (!user) {
    return (
      <Link to="/login" className="like" title={t("Најавете се за да лајкнете")}>
        <Icon name="heart" size={18} /><span>{count}</span>
      </Link>
    );
  }
  const toggle = async () => {
    if (busy) return;
    const prev = state;
    setState({ liked: !prev.liked, count: prev.count + (prev.liked ? -1 : 1) });
    setBusy(true);
    try {
      const r = await api<{ like_count: number; liked_by_me: boolean }>(`/photos/${id}/like/`, { method: prev.liked ? "DELETE" : "POST" });
      setState({ count: r.like_count, liked: r.liked_by_me });
    } catch {
      setState(prev);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" className={state.liked ? "like on" : "like"} onClick={toggle} aria-pressed={state.liked}
            aria-label={state.liked ? t("Отстрани лајк") : t("Лајкни")}>
      <Icon name="heart" size={18} /><span>{state.count}</span>
    </button>
  );
}
