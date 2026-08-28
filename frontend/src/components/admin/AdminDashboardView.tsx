import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { UserPlus, ShieldAlert } from "lucide-react";
import AdminUserTable from "./AdminUserTable";
import CreateAdminForm from "./CreateAdminForm";
import DeleteUserConfirmModal from "./DeleteUserConfirmModal";
import AdminActivityDashboard from "./activity/AdminActivityDashboard";
import { UserPublic } from "../../client/types.gen";
import {
  updateUserApiV1UsersIdPatch,
  deleteUserApiV1UsersIdDelete,
  createUserApiV1UsersPost,
} from "../../client/sdk.gen";
import { Role, useAuth } from "../../contexts/AuthContext";

interface AdminDashboardViewProps {
  currentUser: UserPublic | null;
  initialTab?: "activity" | "users";
}

const AdminDashboardView = ({
  currentUser,
  initialTab,
}: AdminDashboardViewProps) => {
  const queryClient = useQueryClient();
  const { role: currentUserRole, user: authUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isCreatingAdmin, setIsCreatingAdmin] = useState(false);
  const [userToDelete, setUserToDelete] = useState<UserPublic | null>(null);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");
  const [newAdminFullName, setNewAdminFullName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tableKey, setTableKey] = useState(0);
  const [activeTab, setActiveTab] = useState<"activity" | "users">(
    initialTab || "activity",
  );

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    } else if (currentUserRole && !location.state?.fromTabClick) {
      setActiveTab("activity");
    }
  }, [initialTab, currentUserRole, location.state]);

  const handleToggleStatus = async (user: UserPublic) => {
    try {
      await updateUserApiV1UsersIdPatch({
        path: { id: user.id },
        body: { is_active: !user.is_active } as any,
      });
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setTableKey((prev) => prev + 1);
    } catch (err) {
      console.error("Failed to toggle status:", err);
    }
  };

  const confirmDeleteUser = async () => {
    if (!userToDelete) return;
    try {
      setIsSubmitting(true);
      await deleteUserApiV1UsersIdDelete({ path: { id: userToDelete.id } });
      setUserToDelete(null);
      setTableKey((prev) => prev + 1);
    } catch (err) {
      console.error("Failed to delete user:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async (user: UserPublic) => {
    setUserToDelete(user);
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setIsSubmitting(true);
      const targetRole = currentUserRole === Role.SUPER ? "admin" : "user";
      await createUserApiV1UsersPost({
        body: {
          email: newAdminEmail,
          password: newAdminPassword,
          full_name: newAdminFullName,
          role: targetRole as any,
          is_active: true,
        },
      });
      setIsCreatingAdmin(false);
      setNewAdminEmail("");
      setNewAdminPassword("");
      setNewAdminFullName("");
      setTableKey((prev) => prev + 1);
    } catch (err: any) {
      setError(err.body?.detail || "Failed to create user.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            {currentUserRole === Role.SUPER
              ? "Super User Control Center"
              : "Identity & Access"}
          </h2>
          <div className="flex items-center gap-4 mt-2">
            <button
              onClick={() => {
                setActiveTab("activity");
                navigate("/", { state: { fromTabClick: true } });
              }}
              className={`text-sm font-bold pb-1 transition-all border-b-2 ${
                activeTab === "activity"
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground"
              }`}
            >
              Activity
            </button>
            <button
              onClick={() => {
                setActiveTab("users");
                navigate("/users", { state: { fromTabClick: true } });
              }}
              className={`text-sm font-bold pb-1 transition-all border-b-2 ${
                activeTab === "users"
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground"
              }`}
            >
              Users
            </button>
          </div>
        </div>
        <button
          onClick={() => setIsCreatingAdmin(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-xl font-bold shadow-sm shadow-primary/20 hover:shadow-lg transition-all active:scale-95"
        >
          <UserPlus className="w-5 h-5" />
          {currentUserRole === Role.SUPER
            ? "Provision Admin"
            : "Provision User"}
        </button>
      </div>

      {isCreatingAdmin && (
        <CreateAdminForm
          email={newAdminEmail}
          fullName={newAdminFullName}
          isSubmitting={isSubmitting}
          isSuper={currentUserRole === Role.SUPER}
          error={error}
          onClose={() => setIsCreatingAdmin(false)}
          onSubmit={handleCreateAdmin}
          onEmailChange={setNewAdminEmail}
          onPasswordChange={setNewAdminPassword}
          onFullNameChange={setNewAdminFullName}
        />
      )}

      {userToDelete && (
        <DeleteUserConfirmModal
          userToDelete={userToDelete}
          currentUserEmail={authUser?.email || ""}
          isDeleting={isSubmitting}
          onClose={() => setUserToDelete(null)}
          onConfirm={confirmDeleteUser}
        />
      )}

      {activeTab === "activity" ? (
        <AdminActivityDashboard />
      ) : (
        <AdminUserTable
          key={tableKey}
          currentUser={currentUser}
          onToggleStatus={handleToggleStatus}
          onDeleteUser={handleDeleteUser}
        />
      )}

      <div className="p-6 bg-amber-500/5 border border-amber-500/10 rounded-2xl flex gap-4">
        <ShieldAlert className="w-6 h-6 text-amber-500 shrink-0" />
        <div>
          <h4 className="text-sm font-bold text-amber-500 uppercase tracking-wider">
            Security Notice
          </h4>
          <p className="text-xs text-foreground mt-1">
            Administrative actions are logged. Changes to user status or role
            take effect upon their next session.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardView;
