import { useState, useEffect } from "react";
import {
  getCurrentUserApiV1LoginCurrentUserGet,
  updateUserApiV1UsersIdPatch,
  deleteUserApiV1UsersIdDelete,
  loginAccessTokenApiV1LoginAccessTokenPost,
  updatePasswordApiV1UsersPasswordPatch,
} from "../client/sdk.gen";
import { type UserPublic } from "../client/types.gen";
import { useAuth, Role } from "../contexts/AuthContext";
import {
  User,
  Mail,
  Shield,
  Lock,
  Trash2,
  CheckCircle2,
  AlertCircle,
  UserCircle,
  Key,
  Activity,
} from "lucide-react";

const Profile = () => {
  const { logout, role: currentUserRole } = useAuth();
  const [currentUser, setCurrentUser] = useState<UserPublic | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // User Profile Edit State
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editFullName, setEditFullName] = useState("");
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Password Change State
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Account Deletion State
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletionPassword, setDeletionPassword] = useState("");
  const [isVerifyingPassword, setIsVerifyingPassword] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      setIsLoading(true);
      const response = await getCurrentUserApiV1LoginCurrentUserGet();
      if (response.data) {
        setCurrentUser(response.data);
        setEditFullName(response.data.full_name || "");
      }
    } catch (error) {
      console.error("Failed to fetch user:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;

    try {
      setIsUpdatingProfile(true);
      const response = await updateUserApiV1UsersIdPatch({
        path: { id: currentUser.id },
        body: { full_name: editFullName },
      });
      if (response.data) {
        setCurrentUser(response.data);
        setIsEditingProfile(false);
      }
    } catch (error) {
      console.error("Failed to update profile:", error);
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    try {
      setIsUpdatingPassword(true);
      await updatePasswordApiV1UsersPasswordPatch({
        body: {
          current_password: currentPassword,
          new_password: newPassword,
        },
      });
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        setIsChangingPassword(false);
        setPasswordSuccess(false);
      }, 2000);
    } catch (error: any) {
      console.error("Failed to update password:", error);
      setPasswordError(
        error.detail ||
          "Failed to update password. Please check your current password.",
      );
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!currentUser) return;

    try {
      setIsDeletingAccount(true);
      await deleteUserApiV1UsersIdDelete({ path: { id: currentUser.id } });
      logout();
    } catch (error) {
      console.error("Failed to delete account:", error);
      alert("An error occurred while deleting your account. Please try again.");
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleConfirmPasswordForDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;
    setDeleteError(null);

    try {
      setIsVerifyingPassword(true);
      // Verify password by attempting to login
      const response = await loginAccessTokenApiV1LoginAccessTokenPost({
        body: {
          username: currentUser.email,
          password: deletionPassword,
        },
      });

      if (response.data?.access_token) {
        // Password verified, proceed to final confirmation
        if (
          window.confirm(
            "FINAL CONFIRMATION: This will permanently erase your entire account. Continue?",
          )
        ) {
          handleDeleteAccount();
        }
      } else {
        setDeleteError("Invalid password. Please try again.");
      }
    } catch (error) {
      setDeleteError("Invalid password. Please try again.");
    } finally {
      setIsVerifyingPassword(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header>
        <h1 className="text-3xl font-bold text-foreground">Account Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your personal information and security preferences
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Personal Info */}
        <div className="lg:col-span-2 space-y-8">
          <section className="bg-card rounded-3xl border border-border shadow-sm overflow-hidden">
            <div className="px-8 py-6 border-b border-border flex justify-between items-center bg-muted/30">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 text-primary rounded-xl">
                  <UserCircle className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-foreground">
                  Personal Profile
                </h2>
              </div>
              {!isEditingProfile && (
                <button
                  onClick={() => setIsEditingProfile(true)}
                  className="px-4 py-2 bg-primary text-primary-foreground text-sm font-bold rounded-xl shadow-sm shadow-primary/20 hover:shadow-lg transition-all"
                >
                  Edit Profile
                </button>
              )}
            </div>

            <div className="p-8">
              {isEditingProfile ? (
                <form onSubmit={handleUpdateProfile} className="space-y-6">
                  <div className="space-y-2">
                    <label
                      htmlFor="full_name"
                      className="text-sm font-bold text-foreground flex items-center gap-2"
                    >
                      <User className="w-3.5 h-3.5 text-muted-foreground" />
                      Full Name
                    </label>
                    <input
                      id="full_name"
                      type="text"
                      className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                      value={editFullName}
                      onChange={(e) => setEditFullName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="flex gap-4">
                    <button
                      type="submit"
                      disabled={isUpdatingProfile}
                      className="px-8 py-3 bg-primary text-primary-foreground rounded-xl font-bold shadow-sm shadow-primary/20 hover:shadow-lg transition-all disabled:opacity-50"
                    >
                      {isUpdatingProfile ? "Saving..." : "Save Changes"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsEditingProfile(false)}
                      className="px-8 py-3 bg-background border border-border text-foreground rounded-xl font-bold hover:bg-accent transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="w-4 h-4" />
                      <span className="text-xs font-black uppercase tracking-widest">
                        Email Address
                      </span>
                    </div>
                    <p className="text-lg text-foreground font-medium">
                      {currentUser?.email}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <User className="w-4 h-4" />
                      <span className="text-xs font-black uppercase tracking-widest">
                        Full Name
                      </span>
                    </div>
                    <p className="text-lg text-foreground font-medium">
                      {currentUser?.full_name || "Not set"}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Shield className="w-4 h-4" />
                      <span className="text-xs font-black uppercase tracking-widest">
                        Account Role
                      </span>
                    </div>
                    <div
                      className={`mt-1 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${
                        currentUser?.role === "super"
                          ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                          : currentUser?.role === "admin"
                            ? "bg-indigo-500/10 text-indigo-500 border border-indigo-500/20"
                            : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
                      }`}
                    >
                      {currentUser?.role}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Activity className="w-4 h-4" />
                      <span className="text-xs font-black uppercase tracking-widest">
                        System Status
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
                      <span className="text-sm font-bold text-green-500">
                        Active Session
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="bg-card rounded-3xl border border-border shadow-sm overflow-hidden">
            <div className="px-8 py-6 border-b border-border flex justify-between items-center bg-muted/30">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 text-primary rounded-xl">
                  <Key className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-foreground">
                  Security Credentials
                </h2>
              </div>
            </div>

            <div className="p-8">
              {isChangingPassword ? (
                <form onSubmit={handleUpdatePassword} className="space-y-6">
                  <div className="space-y-2">
                    <label
                      htmlFor="current_password"
                      style={{ display: "block" }}
                      className="text-sm font-bold text-foreground"
                    >
                      Current Password
                    </label>
                    <input
                      id="current_password"
                      type="password"
                      className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label
                        htmlFor="new_password"
                        style={{ display: "block" }}
                        className="text-sm font-bold text-foreground"
                      >
                        New Password
                      </label>
                      <input
                        id="new_password"
                        type="password"
                        className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <label
                        htmlFor="confirm_password"
                        style={{ display: "block" }}
                        className="text-sm font-bold text-foreground"
                      >
                        Confirm New Password
                      </label>
                      <input
                        id="confirm_password"
                        type="password"
                        className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  {passwordError && (
                    <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-500 text-sm font-bold">
                      <AlertCircle className="w-5 h-5" />
                      {passwordError}
                    </div>
                  )}
                  {passwordSuccess && (
                    <div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-2xl text-green-500 text-sm font-bold">
                      <CheckCircle2 className="w-5 h-5" />
                      Password successfully updated!
                    </div>
                  )}

                  <div className="flex gap-4">
                    <button
                      type="submit"
                      disabled={isUpdatingPassword}
                      className="px-8 py-3 bg-primary text-primary-foreground rounded-xl font-bold shadow-sm shadow-primary/20 hover:shadow-lg transition-all disabled:opacity-50"
                    >
                      {isUpdatingPassword ? "Updating..." : "Update Password"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsChangingPassword(false)}
                      className="px-8 py-3 bg-background border border-border text-foreground rounded-xl font-bold hover:bg-accent transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                  <div className="max-w-md">
                    <p className="font-bold text-foreground">
                      Account Password
                    </p>
                    <p className="text-muted-foreground text-sm mt-1">
                      Protect your account by ensuring your password is complex
                      and updated regularly.
                    </p>
                  </div>
                  <button
                    onClick={() => setIsChangingPassword(true)}
                    className="px-8 py-3.5 bg-primary text-primary-foreground rounded-2xl font-bold shadow-sm shadow-primary/20 hover:shadow-lg transition-all flex items-center gap-2"
                  >
                    <Lock className="w-4 h-4" />
                    Change Password
                  </button>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Right Column: Sidebar Actions/Info */}
        <div className="space-y-8">
          <section
            className={`${
              currentUserRole === Role.SUPER
                ? "bg-slate-500/5 border-slate-500/10"
                : "bg-red-500/5 border-red-500/10"
            } rounded-3xl border shadow-sm overflow-hidden`}
          >
            <div className="p-8 space-y-6">
              <div
                className={`flex items-center gap-3 ${
                  currentUserRole === Role.SUPER
                    ? "text-slate-500"
                    : "text-red-500"
                }`}
              >
                {currentUserRole === Role.SUPER ? (
                  <Shield className="w-6 h-6" />
                ) : (
                  <Trash2 className="w-6 h-6" />
                )}
                <h2 className="text-xl font-bold">
                  {currentUserRole === Role.SUPER
                    ? "Account Protection"
                    : "Danger Zone"}
                </h2>
              </div>

              <p className="text-sm text-muted-foreground leading-relaxed">
                {currentUserRole === Role.SUPER
                  ? "As a Super User, your account is protected from self-deletion to maintain system stability and prevent accidental loss of administrative access. Please contact support or another administrator for account removal."
                  : "Deleting your account is a permanent action. All your content drafts, settings, and profile information will be removed from our systems."}
              </p>

              {currentUserRole === Role.SUPER ? (
                <button
                  disabled
                  className="w-full py-4 bg-slate-500/20 text-slate-500 rounded-2xl font-bold cursor-not-allowed transition-all"
                >
                  Delete My Account (Disabled)
                </button>
              ) : !showDeleteConfirm ? (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="w-full py-4 bg-red-500 text-white rounded-2xl font-bold hover:bg-red-600 hover:shadow-xl hover:shadow-red-500/20 active:scale-[0.98] transition-all"
                >
                  Delete My Account
                </button>
              ) : (
                <form
                  onSubmit={handleConfirmPasswordForDelete}
                  className="space-y-4"
                >
                  <div className="space-y-2">
                    <label
                      htmlFor="deletion_password"
                      className="text-xs font-black uppercase tracking-widest text-red-500"
                    >
                      Verify Password
                    </label>
                    <input
                      id="deletion_password"
                      type="password"
                      className="w-full bg-background border border-red-500/30 text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-red-500/50 transition-all font-medium"
                      placeholder="Current Password"
                      value={deletionPassword}
                      onChange={(e) => setDeletionPassword(e.target.value)}
                      required
                    />
                  </div>
                  {deleteError && (
                    <div className="p-3 bg-red-500/10 rounded-xl text-[10px] font-bold text-red-500 border border-red-500/20">
                      {deleteError}
                    </div>
                  )}
                  <div className="flex flex-col gap-2">
                    <button
                      type="submit"
                      disabled={isVerifyingPassword || isDeletingAccount}
                      className="w-full py-3.5 bg-red-600 text-white rounded-2xl font-bold hover:shadow-lg transition-all disabled:opacity-50"
                    >
                      {isVerifyingPassword || isDeletingAccount
                        ? "Processing..."
                        : "Confirm Deletion"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowDeleteConfirm(false);
                        setDeletionPassword("");
                        setDeleteError(null);
                      }}
                      className="w-full py-3 bg-transparent text-muted-foreground hover:text-foreground font-bold transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Profile;
