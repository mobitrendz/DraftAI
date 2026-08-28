import { useQuery } from "@tanstack/react-query";
import { ShieldAlert, AlertCircle, Loader2, Activity } from "lucide-react";
import { useAuth, Role } from "../../../contexts/AuthContext";
import { readAllActivitiesApiV1ActivitiesGet } from "../../../client/sdk.gen";
import { extractApiError } from "../../../lib/error-handler";

const AdminActivityDashboard = () => {
  const { token, hasPermission } = useAuth();
  const isAdmin = hasPermission(Role.ADMIN);

  const {
    data: activities,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["admin-activities"],
    queryFn: async () => {
      const response = await readAllActivitiesApiV1ActivitiesGet();
      if (response.error) throw response.error;
      return response.data;
    },
    enabled: isAdmin && !!token,
  });

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center p-12 bg-rose-500/5 border border-rose-500/10 rounded-[32px]">
        <div className="w-20 h-20 bg-rose-500/10 rounded-full flex items-center justify-center mb-6">
          <ShieldAlert className="w-10 h-10 text-rose-500" />
        </div>
        <h1 className="text-3xl font-black text-rose-500 tracking-tight">
          Access Restricted
        </h1>
        <p className="text-muted-foreground mt-4 max-w-sm text-lg font-medium">
          Activity logs are restricted to administrative personnel only.
        </p>
      </div>
    );
  }

  const items = activities?.items ?? [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-black text-foreground tracking-tight">
            Platform Activity
          </h1>
          <p className="text-lg text-muted-foreground font-medium mt-1">
            Recent API activity across all users
          </p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 text-primary font-bold text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading...
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-center gap-3 text-rose-500 text-sm font-bold">
          <AlertCircle className="w-5 h-5 shrink-0" />
          {extractApiError(error)}
        </div>
      )}

      <div className="rounded-2xl border border-border bg-card overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <h2 className="font-bold text-foreground">
            {activities?.total ?? 0} total events
          </h2>
        </div>

        {isLoading && !activities ? (
          <div className="p-12 text-center text-muted-foreground">Loading activity...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            No recent activity recorded.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {items.map((item) => (
              <div
                key={item.id}
                className="px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2"
              >
                <div>
                  <p className="font-medium text-foreground">
                    {item.method} {item.path}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    User {item.user_id?.slice(0, 8) ?? "unknown"} ·{" "}
                    {item.ip_address ?? "—"}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  <span
                    className={
                      item.status_code && item.status_code < 400
                        ? "text-green-600"
                        : "text-red-500"
                    }
                  >
                    {item.status_code}
                  </span>
                  {" · "}
                  {item.created_at
                    ? new Date(item.created_at).toLocaleString()
                    : "—"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminActivityDashboard;
