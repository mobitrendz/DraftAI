import { useState } from "react";
import { X, AlertTriangle, Lock } from "lucide-react";
import { UserPublic } from "../../client/types.gen";
import { loginAccessTokenApiV1LoginAccessTokenPost } from "../../client/sdk.gen";

interface DeleteUserConfirmModalProps {
  userToDelete: UserPublic;
  currentUserEmail: string;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const DeleteUserConfirmModal = ({
  userToDelete,
  currentUserEmail,
  isDeleting,
  onClose,
  onConfirm,
}: DeleteUserConfirmModalProps) => {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleVerifyAndConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsVerifying(true);

    try {
      // Verify current user's password by attempting to get a token
      const response = await loginAccessTokenApiV1LoginAccessTokenPost({
        body: {
          username: currentUserEmail,
          password: password,
        },
      });

      if (response.data?.access_token) {
        onConfirm();
      } else {
        setError("Incorrect password. Please try again.");
      }
    } catch (err) {
      setError("Invalid credentials. Password verification failed.");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="max-w-md w-full bg-[var(--card-bg)] border border-red-500/20 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
        <div className="px-8 py-6 border-b border-red-500/10 bg-red-500/5 flex justify-between items-center">
          <div className="flex items-center gap-3 text-red-500">
            <AlertTriangle className="w-6 h-6" />
            <h3 className="font-bold text-lg">Confirm Deletion</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-red-500/10 rounded-xl transition-all"
          >
            <X className="w-5 h-5 text-[var(--text-dim)]" />
          </button>
        </div>

        <div className="p-8 space-y-6">
          <div className="space-y-2">
            <p className="text-[var(--text)]">
              You are about to permanently delete{" "}
              <span className="font-bold text-red-500">
                {userToDelete.email}
              </span>
              .
            </p>
            <p className="text-sm text-[var(--text-dim)]">
              This action cannot be undone. Please enter your password to
              confirm this sensitive operation.
            </p>
          </div>

          <form onSubmit={handleVerifyAndConfirm} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-[var(--text-h)] flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-[var(--text-dim)]" />
                Your Password
              </label>
              <input
                type="password"
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-red-500/30 transition-all font-medium"
                placeholder="Enter your current password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoFocus
              />
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs font-bold text-red-500">
                {error}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-6 py-3.5 bg-[var(--bg)] border border-[var(--border)] rounded-2xl font-bold hover:bg-[var(--sidebar-bg)] transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isVerifying || isDeleting}
                className="flex-1 px-6 py-3.5 bg-red-500 text-white rounded-2xl font-bold hover:shadow-lg shadow-red-500/25 active:scale-95 transition-all disabled:opacity-50"
              >
                {isVerifying || isDeleting ? "Processing..." : "Confirm Delete"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default DeleteUserConfirmModal;
