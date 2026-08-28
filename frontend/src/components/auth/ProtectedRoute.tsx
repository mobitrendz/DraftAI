import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, Role } from "../../contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: Role;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
}) => {
  const { isAuthenticated, role, isLoading, hasPermission } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--accent)]"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !hasPermission(requiredRole)) {
    // Custom "Access Denied" view or redirect
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] p-4">
        <div className="max-w-md w-full bg-[var(--card-bg)] border border-[var(--border)] rounded-2xl p-8 text-center shadow-xl">
          <div className="w-20 h-20 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-10 w-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m0 0v2m0-2h2m-2 0H10m11 3.29V17a2 2 0 00-2-2h-1.29l-3.3-3.3a2 2 0 00-2.83 0l-3.3 3.3H5a2 2 0 00-2 2v3.29a2 2 0 00.59 1.41l3.3 3.3a2 2 0 002.83 0l3.3-3.3h1.29a2 2 0 002-2v-3.29a2 2 0 00-.59-1.41l-3.3-3.3a2 2 0 00-2.83 0l-3.3 3.3H5"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-h)] mb-2">
            Access Denied
          </h1>
          <p className="text-[var(--text-dim)] mb-8">
            You don't have the required permissions to access this page.
            Required role:{" "}
            <span className="font-bold text-[var(--accent)]">
              {requiredRole}
            </span>
          </p>
          <button
            onClick={() => window.history.back()}
            className="w-full py-3 bg-[var(--accent)] text-white font-bold rounded-xl hover:opacity-90 transition-all shadow-lg shadow-[var(--accent)]/25"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
