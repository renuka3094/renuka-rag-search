import { HashRouter, Route, Routes } from "react-router-dom";

import LayoutShell from "./components/LayoutShell";
import AdminPage from "./pages/AdminPage";
import ChatPage from "./pages/ChatPage";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<LayoutShell />}>
          <Route index element={<ChatPage />} />
          <Route path="c/:conversationId" element={<ChatPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
