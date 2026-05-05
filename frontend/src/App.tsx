import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { RoleProvider } from "./lib/roleContext";
import { Dashboard } from "./pages/Dashboard";
import { Library } from "./pages/Library";
import { NewRequest } from "./pages/NewRequest";
import { RequestDetail } from "./pages/RequestDetail";
import { ReviewQueue } from "./pages/ReviewQueue";

function titles(pathname: string): string {
  if (pathname === "/") return "Dashboard";
  if (pathname.startsWith("/requests/new")) return "New IEP request";
  if (pathname.startsWith("/requests/")) return "Request detail";
  if (pathname.startsWith("/reviews")) return "Review queue";
  if (pathname.startsWith("/library")) return "Library";
  return "Medical Affairs";
}

function Layout() {
  const loc = useLocation();
  return (
    <div className="min-h-screen flex w-full bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={titles(loc.pathname)} />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <RoleProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="requests/new" element={<NewRequest />} />
          <Route path="requests/:id" element={<RequestDetail />} />
          <Route path="reviews" element={<ReviewQueue />} />
          <Route path="library" element={<Library />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </RoleProvider>
  );
}
