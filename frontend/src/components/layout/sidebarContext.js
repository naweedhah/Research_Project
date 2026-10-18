import { createContext, useContext } from 'react';

export const SidebarContext = createContext({
  sidebarOpen: false,
  setSidebarOpen: () => {},
});

export function useSidebar() {
  return useContext(SidebarContext);
}
