import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AgentGuard } from "./pages/AgentGuard";
import { Artifacts } from "./pages/Artifacts";
import { CaseDetail } from "./pages/CaseDetail";
import { Cases } from "./pages/Cases";
import { Dashboard } from "./pages/Dashboard";
import { Decisions } from "./pages/Decisions";
import { LocalProof } from "./pages/LocalProof";
import { Search } from "./pages/Search";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="cases" element={<Cases />} />
        <Route path="cases/:caseId" element={<CaseDetail />} />
        <Route path="artifacts" element={<Artifacts />} />
        <Route path="search" element={<Search />} />
        <Route path="localproof" element={<LocalProof />} />
        <Route path="agentguard" element={<AgentGuard />} />
        <Route path="decisions" element={<Decisions />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
