import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Timeline from "./pages/Timeline.jsx";
import Upload from "./pages/Upload.jsx";
import Insights from "./pages/Insights.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import RecordsPage from "./pages/RecordsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import SupportPage from "./pages/SupportPage.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/analytics" element={<Navigate to="/insights" replace />} />
        <Route path="/intelligence" element={<Navigate to="/insights" replace />} />
        <Route path="/timeline" element={<Layout><Timeline /></Layout>} />
        <Route path="/upload" element={<Layout><Upload /></Layout>} />
        <Route path="/records" element={<RecordsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/support" element={<SupportPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
