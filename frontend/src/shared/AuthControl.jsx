// Controllo login/account per la SPA (atlante). Stesso aspetto del widget
// vanilla del masthead SSR (classi .site-auth), cosi' l'header e' coerente fra i
// due sistemi di rendering. Non compare se Supabase non e' configurato.

import React, { useEffect, useRef, useState } from "react";
import { UserRound } from "lucide-react";
import {
  getUser,
  isAuthConfigured,
  onAuthChange,
  signInWithGoogle,
  signOut,
  syncProfile,
} from "./supabase.js";

export function AuthControl() {
  const [user, setUser] = useState(null);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!isAuthConfigured()) return undefined;
    let active = true;
    let unsub = () => {};
    getUser().then((u) => {
      if (!active) return;
      setUser(u);
      if (u) syncProfile(); // upsert profilo anche se il login avviene sull'atlante
    });
    onAuthChange((u) => {
      setUser(u);
      if (u) syncProfile();
    }).then((fn) => (active ? (unsub = fn) : fn()));
    return () => {
      active = false;
      unsub();
    };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [open]);

  if (!isAuthConfigured()) return null;

  if (!user) {
    return (
      <div className="site-auth">
        <button
          type="button"
          className="site-auth__login"
          aria-label="Accedi con Google"
          onClick={() => signInWithGoogle()}
        >
          <UserRound className="site-auth__login-icon" size={16} aria-hidden="true" />
          <span className="site-auth__login-label">Accedi</span>
        </button>
      </div>
    );
  }

  const label = user.email || "Account";
  return (
    <div className="site-auth" ref={wrapRef}>
      <div className="site-auth__menu">
        <button
          type="button"
          className="site-auth__btn"
          aria-haspopup="true"
          aria-expanded={open ? "true" : "false"}
          onClick={() => setOpen((o) => !o)}
        >
          <span className="site-auth__avatar" aria-hidden="true">
            {(label.trim().charAt(0) || "?").toUpperCase()}
          </span>
          <span className="site-auth__label">{label}</span>
        </button>
        {open && (
          <div className="site-auth__dropdown">
            <a className="site-auth__item" href="/atlante?fav=1">I miei preferiti</a>
            <a className="site-auth__item" href="/account">Il mio account</a>
            <button type="button" className="site-auth__item" onClick={() => signOut()}>
              Esci
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
