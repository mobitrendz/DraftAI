import { X, Shield, Lock, User, Mail } from "lucide-react";

interface CreateAdminFormProps {
  email: string;
  fullName: string;
  isSubmitting: boolean;
  isSuper: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  onEmailChange: (val: string) => void;
  onPasswordChange: (val: string) => void;
  onFullNameChange: (val: string) => void;
}

const CreateAdminForm = ({
  email,
  fullName,
  isSubmitting,
  isSuper,
  error,
  onClose,
  onSubmit,
  onEmailChange,
  onPasswordChange,
  onFullNameChange,
}: CreateAdminFormProps) => {
  return (
    <div className="bg-card rounded-3xl border border-border shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="px-8 py-6 border-b border-border bg-muted/50 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-xl">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-foreground">
              {isSuper ? "New Admin User" : "New System User"}
            </h3>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest">
              {isSuper ? "Elevated Access Account" : "Access Provisioning"}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-muted-foreground hover:text-foreground hover:bg-background rounded-xl transition-all"
        >
          <X className="w-6 h-6" />
        </button>
      </div>

      <form onSubmit={onSubmit} className="p-8 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label
              htmlFor="full-name"
              className="text-sm font-bold text-foreground flex items-center gap-2"
            >
              <User className="w-3.5 h-3.5 text-muted-foreground" />
              Full Name
            </label>
            <input
              id="full-name"
              type="text"
              className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
              placeholder="e.g. Sarah Connor"
              value={fullName}
              onChange={(e) => onFullNameChange(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="admin-email"
              className="text-sm font-bold text-foreground flex items-center gap-2"
            >
              <Mail className="w-3.5 h-3.5 text-muted-foreground" />
              Email Address
            </label>
            <input
              id="admin-email"
              type="email"
              className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="admin-password"
            className="text-sm font-bold text-foreground flex items-center gap-2"
          >
            <Lock className="w-3.5 h-3.5 text-muted-foreground" />
            Temporary Password
          </label>
          <input
            id="admin-password"
            type="password"
            className="w-full bg-background border border-border text-foreground rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
            placeholder="Min. 8 characters"
            onChange={(e) => onPasswordChange(e.target.value)}
            required
          />
        </div>

        {error && (
          <div className="text-sm text-red-500 font-bold p-4 bg-red-500/10 rounded-2xl border border-red-500/20">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-4 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-8 py-3.5 bg-background border border-border text-foreground rounded-2xl font-bold hover:bg-accent transition-all"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-10 py-3.5 bg-primary text-primary-foreground rounded-2xl font-bold shadow-sm shadow-primary/20 hover:shadow-lg active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {isSubmitting
              ? "Provisioning..."
              : isSuper
                ? "Create Admin Account"
                : "Create User Account"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateAdminForm;
