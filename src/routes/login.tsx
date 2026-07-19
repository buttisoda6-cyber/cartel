import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Store, Lock, User, ArrowRight, ShieldCheck, KeyRound } from "lucide-react";
import { apiClient } from "@/lib/api/client";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // If already logged in, skip straight to the right dashboard.
  useEffect(() => {
    if (sessionStorage.getItem("merchant_auth") === "true") {
      const role = sessionStorage.getItem("merchant_role");
      navigate({ to: role === "admin" ? "/admin" : "/", replace: true });
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (mode === "signup") {
      if (password.length < 6) {
        setError("Password must be at least 6 characters long.");
        return;
      }
      // Local-only signup record. This does NOT call your backend yet —
      // wire this to /api/auth/signup when that endpoint exists so new
      // merchants are actually persisted server-side.
      localStorage.setItem("signup_username", username);
      localStorage.setItem("signup_password", password);
      setSuccess("Account created! Please log in with your new credentials.");
      setMode("login");
      setUsername("");
      setPassword("");
      return;
    }

    // ---- LOGIN ----
    let isAuthenticated = false;
    let role: "admin" | "users" = "users";

    if (username === "admin" && password === "cartel@123") {
      isAuthenticated = true;
      role = "admin";
    } else if (username !== "" && password !== "") {
      isAuthenticated = true;
      role = "users";
    }

    if (!isAuthenticated) {
      setError("Invalid username or password.");
      return;
    }

    // Persist only for current tab/session.
    sessionStorage.setItem("merchant_auth", "true");
    sessionStorage.setItem("merchant_role", role);
    sessionStorage.setItem("merchant_username", username);

    try {
      const res = await apiClient.post<{ session_id: number }>("/api/activity/login", {
        username,
        device_info: navigator.userAgent,
      });
      sessionStorage.setItem("merchant_session_id", String(res.session_id));
    } catch (err) {
      console.error("Failed to log activity to database:", err);
    }

    navigate({ to: role === "admin" ? "/admin" : "/", replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-4 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-success/20 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md bg-card border border-border rounded-3xl shadow-2xl p-8 relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-16 h-16 bg-primary text-primary-foreground rounded-2xl flex items-center justify-center mb-4 shadow-[0_8px_30px_rgba(22,163,74,0.3)]">
            <Store className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">CART-EL Portal</h1>
          <p className="text-sm text-muted-foreground mt-2">
            {mode === "signup" ? "Set up your Merchant account" : "Secure Merchant Login"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-semibold ml-1">Username</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-background border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder={mode === "signup" ? "Choose a username" : "Enter your username"}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-semibold ml-1">Password</label>
            <div className="relative">
              {mode === "signup" ? (
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              ) : (
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              )}
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-background border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder={mode === "signup" ? "Create a secure password" : "Enter your password"}
                required
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-alert font-medium bg-alert/10 px-3 py-2 rounded-lg text-center animate-in shake">
              {error}
            </div>
          )}

          {success && (
            <div className="text-sm text-success font-medium bg-success/10 px-3 py-2 rounded-lg text-center animate-in">
              {success}
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-primary text-primary-foreground font-semibold py-3.5 rounded-xl shadow-[0_8px_20px_rgba(22,163,74,0.25)] hover:shadow-[0_12px_25px_rgba(22,163,74,0.35)] hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 group mt-2"
          >
            {mode === "signup" ? "Create Account" : "Access Dashboard"} <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          {mode === "login" ? (
            <>
              Don't have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("signup");
                  setError("");
                  setSuccess("");
                }}
                className="text-primary font-semibold hover:underline"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError("");
                  setSuccess("");
                }}
                className="text-primary font-semibold hover:underline"
              >
                Log in
              </button>
            </>
          )}
        </div>

        <div className="mt-8 flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="w-4 h-4 text-success" />
          Secured by CART-EL
        </div>
      </div>
    </div>
  );
}