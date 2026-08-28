import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  loginAccessTokenApiV1LoginAccessTokenPost,
  registerUserApiV1LoginSignupPost,
} from "../client";
import { useAuth } from "../contexts/AuthContext";
import { extractApiError } from "../lib/error-handler";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { AlertCircle, Loader2 } from "lucide-react";

const Login: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || "/";
  const isExpired =
    new URLSearchParams(location.search).get("expired") === "true";

  const loginMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await loginAccessTokenApiV1LoginAccessTokenPost({
        body: { username, password },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      if (data?.access_token) {
        login(data.access_token);
        navigate(from, { replace: true });
      }
    },
  });

  const signupMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await registerUserApiV1LoginSignupPost({
        body: { email: username, password },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      alert("Signup successful! Please sign in.");
      setIsSignUp(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSignUp) {
      signupMutation.mutate();
    } else {
      loginMutation.mutate();
    }
  };

  const error = loginMutation.error || signupMutation.error;
  const isLoading = loginMutation.isPending || signupMutation.isPending;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <Card className="max-w-md w-full border-border bg-card shadow-2xl rounded-3xl">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-3xl font-black text-foreground tracking-tight">
            {isSignUp ? "Join MobiTrendz" : "Welcome Back"}
          </CardTitle>
          <CardDescription className="text-muted-foreground text-lg">
            {isSignUp
              ? "Create your account to get started"
              : "Sign in to access your dashboard"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {isExpired && !error && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center gap-3 text-amber-600 text-sm font-bold animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="w-5 h-5 shrink-0" />
                Token Expired, please login again.
              </div>
            )}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-500 text-sm font-bold animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="w-5 h-5 shrink-0" />
                {extractApiError(error).toLowerCase().includes("inactive user")
                  ? "Your account is currently inactive. Please contact your system administrator."
                  : extractApiError(error)}
              </div>
            )}
            <div className="space-y-2">
              <Label
                htmlFor="email"
                className="text-foreground/80 ml-1 font-bold"
              >
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="bg-background border-border text-foreground h-12 focus:ring-primary"
              />
            </div>
            <div className="space-y-2">
              <Label
                htmlFor="password"
                className="text-foreground/80 ml-1 font-bold"
              >
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-background border-border text-foreground h-12 focus:ring-primary"
              />
            </div>
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-lg transition-all rounded-xl mt-6 shadow-lg shadow-primary/20"
            >
              {isLoading ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : isSignUp ? (
                "Create Account"
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <div className="relative w-full">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground font-bold">
                Or continue with
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={() => setIsSignUp(!isSignUp)}
            className="w-full text-muted-foreground hover:text-foreground hover:bg-accent font-bold"
          >
            {isSignUp
              ? "Already have an account? Sign in"
              : "Don't have an account? Sign up"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Login;
