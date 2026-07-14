import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { useSession } from "./stores/session";
import Analytics from "./pages/Analytics";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Graph from "./pages/Graph";
import KnowledgeBase from "./pages/KnowledgeBase";
import Login from "./pages/Login";
import Settings from "./pages/Settings";

export default function App() {
  const token = useSession((s) => s.token);
  if (!token) return <Login />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/graph" element={<Graph />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
