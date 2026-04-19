import React from "react";
import { NavLink } from "react-router-dom";

const Sidebar = () => {
  const navItems = [
    { name: "Dashboard", path: "/", icon: "dashboard" },
    { name: "AI Insights", path: "/insights", icon: "lightbulb" },
    { name: "Timeline", path: "/timeline", icon: "schedule" },
    { name: "Upload", path: "/upload", icon: "upload" },
    { name: "CRM Records", path: "/records", icon: "storage" },
    { name: "AI chatbot", path: "/chat", icon: "smart_toy" },
  ];

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col justify-between border-none bg-background py-8 shadow-[12px_0_32px_-4px_rgba(32,27,20,0.04)] dark:bg-[#1a1c1e]">
      <div>
        <div className="mb-10 px-8">
          <h1 className="font-headline text-xl font-black uppercase tracking-tighter text-primary dark:text-[#ede1d5]">
            AI CRM
          </h1>
          <p className="font-headline text-[10px] font-bold uppercase tracking-tight opacity-50">
            Revenue intelligence
          </p>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `px-6 py-3 flex items-center gap-3 transition-all duration-300 ${
                  isActive
                    ? "text-primary dark:text-white font-bold bg-[#ede1d5] dark:bg-primary rounded-r-full mr-4 border-l-4 border-secondary scale-[0.98]"
                    : "text-[#424b54]/70 dark:text-stone-400 font-medium hover:text-primary hover:bg-[#ede1d5]/30"
                }`
              }
            >
              <span className="material-symbols-outlined text-xl">{item.icon}</span>
              <span className="font-headline text-xs font-bold uppercase tracking-tight">{item.name}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex flex-col gap-1">
        <NavLink
          to="/settings"
          className="flex items-center gap-3 px-6 py-2 font-medium text-[#424b54]/70 transition-colors hover:bg-[#ede1d5]/30 hover:text-primary dark:text-stone-400"
        >
          <span className="material-symbols-outlined text-xl">settings</span>
          <span className="font-headline text-xs font-bold uppercase tracking-tight">Settings</span>
        </NavLink>
        <NavLink
          to="/support"
          className="flex items-center gap-3 px-6 py-2 font-medium text-[#424b54]/70 transition-colors hover:bg-[#ede1d5]/30 hover:text-primary dark:text-stone-400"
        >
          <span className="material-symbols-outlined text-xl">contact_support</span>
          <span className="font-headline text-xs font-bold uppercase tracking-tight">Support</span>
        </NavLink>
      </div>
    </aside>
  );
};

export default Sidebar;
