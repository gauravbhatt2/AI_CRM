import React from "react";
import Sidebar from "./Sidebar.jsx";
import TopBar from "./TopBar.jsx";

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-background text-on-surface">
      <Sidebar />
      <TopBar />
      <main className="ml-64 pt-20 px-12 pb-12 transition-all">
        <div className="max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
};

export default Layout;
