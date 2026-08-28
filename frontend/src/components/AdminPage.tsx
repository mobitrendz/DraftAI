import { useAuth, Role } from "../contexts/AuthContext";
import DashboardLayout from "./layout/DashboardLayout";
import AdminDashboardView from "./admin/AdminDashboardView";

interface AdminPageProps {
  initialTab?: "activity" | "users";
  onLogout?: () => void;
}

const AdminPage = ({ initialTab, onLogout }: AdminPageProps) => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    } else {
      logout();
    }
  };

  return (
    <DashboardLayout currentUser={user} onLogout={handleLogout}>
      <AdminDashboardView currentUser={user} initialTab={initialTab} />
    </DashboardLayout>
  );
};

export default AdminPage;
