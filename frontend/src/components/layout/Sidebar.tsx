import {
  LayoutDashboard,
  User,
  Users,
  LogOut,
  ChevronLeft,
  ChevronRight,
  PenLine,
  Settings,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { Role, useAuth } from "../../contexts/AuthContext";
import { ThemeToggle, ThemeToggleCompact } from "../ThemeToggle";

interface SidebarProps {
  userRole?: string;
  userName?: string;
  onLogout: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

const Sidebar = ({
  userRole,
  userName,
  onLogout,
  isOpen,
  onClose,
}: SidebarProps) => {
  const location = useLocation();
  const { hasPermission } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navItems = [
    {
      name: "Home",
      icon: LayoutDashboard,
      path: "/",
      roles: [Role.USER, Role.ADMIN, Role.SUPER],
    },
    {
      name: "Settings",
      icon: Settings,
      path: "/settings",
      roles: [Role.USER, Role.ADMIN, Role.SUPER],
    },
    {
      name: "Identity & Access",
      icon: Users,
      path: "/users",
      roles: [Role.ADMIN, Role.SUPER],
    },
    {
      name: "My Profile",
      icon: User,
      path: "/profile",
      roles: [Role.USER, Role.ADMIN, Role.SUPER],
    },
  ];

  const filteredItems = navItems.filter((item) =>
    item.roles.some((role) => hasPermission(role)),
  );

  const sidebarClasses = `
    fixed inset-y-0 left-0 z-50 lg:relative lg:translate-x-0 transform transition-all duration-300 ease-in-out
    bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] flex flex-col
    ${isOpen ? "translate-x-0" : "-translate-x-full"}
    ${isCollapsed ? "lg:w-20" : "lg:w-[var(--sidebar-width)]"}
    w-[280px]
  `;

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside className={sidebarClasses}>
        <div className="h-[var(--header-height)] flex items-center px-6 border-b border-[var(--sidebar-border)]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shrink-0">
              <PenLine className="text-primary-foreground w-5 h-5" />
            </div>
            {(!isCollapsed || isOpen) && (
              <span className="font-bold text-lg text-foreground whitespace-nowrap">
                Draft<span className="text-primary">AI</span>
              </span>
            )}
          </div>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          {filteredItems.map((item) => {
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => {
                  if (onClose) onClose();
                }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <item.icon
                  className={`w-5 h-5 shrink-0 ${isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-accent-foreground"}`}
                />
                {(!isCollapsed || isOpen) && (
                  <span className="font-medium">{item.name}</span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-[var(--sidebar-border)] space-y-1">
          <div className="px-3 py-2">
            {isCollapsed && !isOpen ? <ThemeToggleCompact /> : <ThemeToggle />}
          </div>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-all"
          >
            {isCollapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <ChevronLeft className="w-5 h-5" />
            )}
            {!isCollapsed && (
              <span className="font-medium text-sm">Collapse Sidebar</span>
            )}
          </button>

          <button
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[var(--text-dim)] hover:bg-red-500/10 hover:text-red-500 transition-all"
          >
            <LogOut className="w-5 h-5 shrink-0" />
            {(!isCollapsed || isOpen) && (
              <span className="font-medium text-sm">Sign Out</span>
            )}
          </button>

          {(!isCollapsed || isOpen) && (
            <div className="mt-4 px-3 py-3 bg-accent/50 rounded-2xl flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
                {userName?.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-foreground truncate">
                  {userName}
                </span>
                <span className="text-[10px] text-primary uppercase font-black tracking-wider">
                  {userRole}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
