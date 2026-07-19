import { Link, Outlet, useRouterState, useNavigate, Navigate } from "@tanstack/react-router";
import { BarChart2, Sparkles, MessageCircle, TrendingUp, Bell, Store, Heart, Leaf, ShoppingCart, Mic, X, Siren, Crown } from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import type { ComponentType } from "react";
import { AIChatPanel } from "./AIChatPanel";
import { apiClient } from "@/lib/api/client";

const nav: { to: string; label: string; icon: ComponentType<{ className?: string }> }[] = [
  { to: "/",              label: "Stock",         icon: BarChart2 },
  { to: "/action-center", label: "Action Center", icon: Siren },
  { to: "/offers",        label: "AI Offers",     icon: Sparkles },
  { to: "/broadcast",     label: "Broadcast",     icon: MessageCircle },
  { to: "/analytics",     label: "Analytics",     icon: TrendingUp },
];

export function Layout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [isAuth, setIsAuth] = useState<boolean | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setIsAuth(sessionStorage.getItem("merchant_auth") === "true");
    setRole(sessionStorage.getItem("merchant_role"));
    setUsername(sessionStorage.getItem("merchant_username") || "");
  }, [pathname]);

  // Track window/tab close to automatically logout user/admin in DB
  useEffect(() => {
    const handleBeforeUnload = () => {
      const sessionId = sessionStorage.getItem("merchant_session_id");
      const username = sessionStorage.getItem("merchant_username");
      if (sessionId && username) {
        const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
        const url = `${API_URL}/api/activity/logout`;
        const blob = new Blob(
          [JSON.stringify({ session_id: Number(sessionId), username })],
          { type: "application/json" }
        );
        navigator.sendBeacon(url, blob);
        // Clear session ID so reload detects it as a new session
        sessionStorage.removeItem("merchant_session_id");
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  // Re-initialize backend session on page reload/refresh
  useEffect(() => {
    const initReloadSession = async () => {
      const auth = sessionStorage.getItem("merchant_auth") === "true";
      const user = sessionStorage.getItem("merchant_username");
      const sessionId = sessionStorage.getItem("merchant_session_id");

      if (auth && user && !sessionId) {
        try {
          const res = await apiClient.post<{ session_id: number }>("/api/activity/login", {
            username: user,
            device_info: navigator.userAgent,
          });
          sessionStorage.setItem("merchant_session_id", String(res.session_id));
        } catch (err) {
          console.error("Failed to auto-login session on reload:", err);
        }
      }
    };

    initReloadSession();
  }, [pathname]);

  const avatarInitials = useMemo(() => {
    if (!username) return "?";
    return username
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }, [username]);

  const handleLogout = async () => {
    const sessionId = sessionStorage.getItem("merchant_session_id");
    if (sessionId) {
      try {
        await apiClient.post("/api/activity/logout", {
          session_id: Number(sessionId),
          username: username || sessionStorage.getItem("merchant_username") || "unknown",
        });
      } catch (err) {
        console.error("Failed to record logout:", err);
      }
    }
    sessionStorage.removeItem("merchant_auth");
    sessionStorage.removeItem("merchant_role");
    sessionStorage.removeItem("merchant_username");
    sessionStorage.removeItem("merchant_session_id");
    window.location.href = "/login";
  };

  if (pathname === "/login") {
    return <Outlet />;
  }

  if (isAuth === null) {
    return <div className="min-h-screen bg-background" />; // loading state
  }

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  // ---------------------------------------------------------------------
  // ADMIN: minimal shell — no sidebar, no bottom nav, no merchant links.
  // Only a slim header (logo + logout) and the Admin Space content.
  // ---------------------------------------------------------------------
  if (role === "admin") {
    if (!pathname.startsWith("/admin")) {
      return <Navigate to="/admin" replace />;
    }

    return (
      <div className="min-h-screen flex flex-col bg-background text-foreground">
        <header className="h-16 bg-card border-b flex items-center justify-between px-4 md:px-8 shadow-card sticky top-0 z-40">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
              <Crown className="w-5 h-5" />
            </div>
            <div className="font-bold text-base text-foreground leading-tight">Admin Dashboard</div>
          </div>
          <div
            title="Logout"
            onClick={handleLogout}
            className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-semibold cursor-pointer hover:opacity-90 hover:scale-105 transition-all shadow-card"
          >
            {avatarInitials}
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    );
  }

  // ---------------------------------------------------------------------
  // MERCHANT: full layout with sidebar (desktop) + bottom nav (mobile).
  // ---------------------------------------------------------------------
  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex fixed left-0 top-0 h-screen w-60 flex-col bg-sidebar text-sidebar-foreground z-50">
        <div className="px-6 py-6 flex items-center gap-2 border-b border-white/10">
          <div className="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-base leading-none">CART-EL</div>
            <div className="text-xs text-white/60 mt-1">Aadhirai Mart</div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => {
            const active = pathname === n.to;
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active ? "bg-white/15 font-medium" : "text-white/80 hover:bg-white/10"
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{n.label}</span>
                {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white/60" />}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 md:ml-60">
        <header className="h-16 bg-card border-b flex items-center justify-between px-4 md:px-8 shadow-card sticky top-0 z-40">
          <div className="flex items-center gap-2">
            <div className="md:hidden w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
              <Store className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-base text-foreground leading-tight">Aadhirai Mart</div>
              <div className="text-xs text-muted-foreground">Merchant Dashboard</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div
              title="Logout"
              onClick={handleLogout}
              className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-semibold cursor-pointer hover:opacity-90 hover:scale-105 transition-all shadow-card"
            >
              {avatarInitials}
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8 pb-24 md:pb-8 overflow-x-hidden">
          <Outlet />
        </main>

        {/* Bottom nav mobile */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-sidebar text-sidebar-foreground border-t border-white/10 flex justify-around z-50">
          {nav.map((n) => {
            const active = pathname === n.to;
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`flex-1 flex flex-col items-center gap-1 py-2.5 text-[9px] ${
                  active ? "text-white" : "text-white/60"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{n.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* AI Chat Floating Button */}
      <button
        onClick={() => setChatOpen(true)}
        className="fixed bottom-20 md:bottom-8 right-6 w-14 h-14 bg-primary text-primary-foreground rounded-full shadow-[0_8px_30px_rgb(0,0,0,0.12)] flex items-center justify-center hover:scale-105 hover:shadow-[0_8px_40px_rgb(0,0,0,0.2)] transition-all z-50 group"
      >
        <Sparkles className="w-6 h-6" />
        <span className="absolute right-full mr-3 bg-card text-foreground px-3 py-1.5 rounded-lg text-sm font-medium shadow-card opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
          AI Store Employee
        </span>
      </button>

      {/* AI Chat Panel */}
      <AIChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}