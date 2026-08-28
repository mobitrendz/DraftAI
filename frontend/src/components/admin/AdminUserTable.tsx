import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  UserMinus,
  Mail,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Shield,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { UserPublic } from "../../client/types.gen";
import { readUsersApiV1UsersGet } from "../../client/sdk.gen";
import { Role, useAuth } from "../../contexts/AuthContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";

interface AdminUserTableProps {
  currentUser: UserPublic | null;
  onToggleStatus: (user: UserPublic) => Promise<void>;
  onDeleteUser: (user: UserPublic) => Promise<void>;
}

const AdminUserTable = ({
  currentUser,
  onToggleStatus,
  onDeleteUser,
}: AdminUserTableProps) => {
  const { role: currentUserRole } = useAuth();
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<
    "full_name" | "created_at" | "role" | "is_active"
  >("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const { data: usersData, isLoading } = useQuery({
    queryKey: ["users", currentPage, pageSize],
    queryFn: async () => {
      const response = await readUsersApiV1UsersGet({
        query: { page: currentPage, size: pageSize },
      });
      if (response.error) throw response.error;
      return response.data;
    },
  });

  const users = (usersData as any)?.data || (usersData as any)?.items || [];
  const totalUsers =
    (usersData as any)?.count || (usersData as any)?.total || 0;

  const canManageUser = (targetUser: UserPublic) => {
    if (currentUserRole === Role.SUPER) return true;
    if (currentUserRole === Role.ADMIN) {
      const targetRole = targetUser.role?.toUpperCase();
      if (targetUser.id === currentUser?.id) return true;
      if (targetRole === Role.SUPER || targetRole === Role.ADMIN) return false;
      return true;
    }
    return false;
  };

  const filteredUsers = users
    .filter((user: UserPublic) => {
      const matchesSearch =
        user.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesRole = roleFilter === "all" || user.role === roleFilter;

      if (user.id === currentUser?.id) return false;

      if (currentUserRole === Role.ADMIN) {
        const targetRole = user.role?.toUpperCase();
        if (targetRole === Role.SUPER) return false;
      }

      return matchesSearch && matchesRole;
    })
    .sort((a: UserPublic, b: UserPublic) => {
      const direction = sortDirection === "asc" ? 1 : -1;

      if (sortField === "full_name") {
        const nameA = a.full_name || "";
        const nameB = b.full_name || "";
        return nameA.localeCompare(nameB) * direction;
      }

      if (sortField === "created_at") {
        const dateA = new Date(a.created_at || 0).getTime();
        const dateB = new Date(b.created_at || 0).getTime();
        return (dateA - dateB) * direction;
      }

      if (sortField === "role") {
        const roleA = a.role || "";
        const roleB = b.role || "";
        return roleA.localeCompare(roleB) * direction;
      }

      if (sortField === "is_active") {
        const statusA = a.is_active ? 1 : 0;
        const statusB = b.is_active ? 1 : 0;
        return (statusA - statusB) * direction;
      }

      return a.id.localeCompare(b.id);
    });

  const handleSort = (
    field: "full_name" | "created_at" | "role" | "is_active",
  ) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const SortIcon = ({
    field,
  }: {
    field: "full_name" | "created_at" | "role" | "is_active";
  }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 ml-2" />;
    return sortDirection === "asc" ? (
      <ArrowUp className="w-3 h-3 ml-2 text-primary" />
    ) : (
      <ArrowDown className="w-3 h-3 ml-2 text-primary" />
    );
  };

  return (
    <div className="bg-card rounded-3xl border border-border shadow-2xl overflow-hidden">
      <div className="p-8 border-b border-border space-y-6 bg-muted/30">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <h2 className="text-2xl font-black text-foreground tracking-tight">
              User Directory
            </h2>
            <p className="text-muted-foreground font-medium text-sm mt-1">
              Manage platform access and security roles
            </p>
          </div>
          <div className="flex gap-3">
            <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-4 py-1.5 rounded-full text-xs font-black uppercase">
              {filteredUsers.filter((u: UserPublic) => u.is_active).length}{" "}
              Active
            </Badge>
            <Badge className="bg-indigo-500/10 text-indigo-500 border-indigo-500/20 px-4 py-1.5 rounded-full text-xs font-black uppercase">
              {filteredUsers.length} Visible
            </Badge>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name or email..."
              className="pl-12 h-12 bg-background border-border text-foreground rounded-2xl focus:ring-primary transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            data-testid="role-filter"
            className="bg-background border border-border rounded-2xl px-6 h-12 text-muted-foreground text-sm font-bold focus:outline-none focus:ring-2 focus:ring-primary transition-all appearance-none cursor-pointer"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
          >
            <option value="all">All Roles</option>
            {currentUserRole === Role.SUPER && (
              <option value="super">Super Admins</option>
            )}
            <option value="admin">Admins</option>
            <option value="user">Users</option>
          </select>
        </div>
      </div>

      <div className="p-2">
        <Table>
          <TableHeader>
            <TableRow className="border-none hover:bg-transparent">
              <TableHead
                className="px-6 py-5 text-muted-foreground font-black uppercase tracking-widest text-[10px] cursor-pointer hover:text-primary transition-colors"
                onClick={() => handleSort("full_name")}
              >
                <div className="flex items-center">
                  User Details
                  <SortIcon field="full_name" />
                </div>
              </TableHead>
              <TableHead
                className="px-6 py-5 text-muted-foreground font-black uppercase tracking-widest text-[10px] cursor-pointer hover:text-primary transition-colors"
                onClick={() => handleSort("role")}
              >
                <div className="flex items-center">
                  Security Role
                  <SortIcon field="role" />
                </div>
              </TableHead>
              <TableHead
                className="px-6 py-5 text-muted-foreground font-black uppercase tracking-widest text-[10px] cursor-pointer hover:text-primary transition-colors"
                onClick={() => handleSort("is_active")}
              >
                <div className="flex items-center">
                  System Status
                  <SortIcon field="is_active" />
                </div>
              </TableHead>
              <TableHead
                className="px-6 py-5 text-muted-foreground font-black uppercase tracking-widest text-[10px] cursor-pointer hover:text-primary transition-colors"
                onClick={() => handleSort("created_at")}
              >
                <div className="flex items-center">
                  Registration
                  <SortIcon field="created_at" />
                </div>
              </TableHead>
              <TableHead className="px-6 py-5 text-muted-foreground font-black uppercase tracking-widest text-[10px] text-right">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow className="hover:bg-transparent border-none">
                <TableCell colSpan={5} className="py-24 text-center">
                  <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                    <p className="text-muted-foreground font-bold animate-pulse">
                      Synchronizing User Data...
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredUsers.length === 0 ? (
              <TableRow className="hover:bg-transparent border-none">
                <TableCell
                  colSpan={5}
                  className="py-24 text-center text-muted-foreground"
                >
                  <p className="font-black text-xl tracking-tight">
                    No users found
                  </p>
                  <p className="text-sm font-medium mt-1">
                    Try adjusting your search or filters
                  </p>
                </TableCell>
              </TableRow>
            ) : (
              filteredUsers.map((user: UserPublic) => (
                <TableRow
                  key={user.id}
                  className="border-border hover:bg-accent/50 transition-all group"
                >
                  <TableCell className="px-6 py-5">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-black text-lg border border-primary/10 group-hover:scale-110 transition-transform">
                        {user.full_name?.charAt(0) ||
                          user.email.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-black text-foreground tracking-tight">
                          {user.full_name || "Anonymous User"}
                        </span>
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-bold">
                          <Mail className="w-3 h-3" />
                          <span>{user.email}</span>
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-5">
                    <div
                      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider ${
                        user.role?.toLowerCase() === "super"
                          ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                          : user.role?.toLowerCase() === "admin"
                            ? "bg-indigo-500/10 text-indigo-500 border border-indigo-500/20"
                            : "bg-slate-700/20 text-slate-400 border border-slate-700/30"
                      }`}
                    >
                      <Shield className="w-3.5 h-3.5" />
                      {user.role}
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-5">
                    {canManageUser(user) && user.id !== currentUser?.id ? (
                      <select
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider bg-background border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary transition-all cursor-pointer ${
                          user.is_active ? "text-emerald-500" : "text-rose-500"
                        }`}
                        value={user.is_active ? "active" : "inactive"}
                        onChange={(e) => {
                          const newValue = e.target.value === "active";
                          if (newValue !== user.is_active) {
                            onToggleStatus(user);
                          }
                        }}
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                      </select>
                    ) : (
                      <div
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider ${
                          user.is_active
                            ? "text-emerald-500 bg-emerald-500/10 border border-emerald-500/20"
                            : "text-rose-500 bg-rose-500/10 border border-rose-500/20"
                        }`}
                      >
                        <div
                          className={`w-2.5 h-2.5 rounded-full mr-2 ${
                            user.is_active
                              ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                              : "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]"
                          }`}
                        />
                        <span className="font-black uppercase tracking-tight text-[11px]">
                          {user.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-5">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground font-black">
                      <Calendar className="w-3.5 h-3.5" />
                      {user.created_at
                        ? new Date(user.created_at).toLocaleDateString(
                            "en-US",
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            },
                          )
                        : "N/A"}
                    </div>
                  </TableCell>
                  <TableCell className="px-6 py-5 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDeleteUser(user)}
                      disabled={
                        !canManageUser(user) || user.id === currentUser?.id
                      }
                      className="text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 rounded-xl transition-all"
                    >
                      <UserMinus className="w-5 h-5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalUsers > pageSize && (
        <div className="px-8 py-6 bg-muted/20 border-t border-border flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-xs text-muted-foreground font-bold uppercase tracking-tight">
            Showing{" "}
            <span className="text-foreground font-black">
              {(currentPage - 1) * pageSize + 1}
            </span>{" "}
            to{" "}
            <span className="text-foreground font-black">
              {Math.min(currentPage * pageSize, totalUsers)}
            </span>{" "}
            of <span className="text-foreground font-black">{totalUsers}</span>{" "}
            Records
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="bg-card border-border text-muted-foreground hover:text-foreground rounded-xl h-10 w-10 p-0"
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setCurrentPage((prev) =>
                  Math.min(Math.ceil(totalUsers / pageSize), prev + 1),
                )
              }
              disabled={currentPage === Math.ceil(totalUsers / pageSize)}
              className="bg-card border-border text-muted-foreground hover:text-foreground rounded-xl h-10 w-10 p-0"
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUserTable;
