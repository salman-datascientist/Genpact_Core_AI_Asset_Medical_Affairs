import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type UserRole = "analyst" | "medical_director";

const RoleContext = createContext<{
  role: UserRole;
  setRole: (r: UserRole) => void;
} | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>("analyst");
  const value = useMemo(() => ({ role, setRole }), [role]);
  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error("useRole must be used within RoleProvider");
  return ctx;
}
