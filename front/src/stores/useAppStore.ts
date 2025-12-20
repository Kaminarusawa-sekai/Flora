import { defineStore } from 'pinia';

interface AppState {
  isChatCollapsed: boolean;
  isResourcePanelCollapsed: boolean;
  isSidebarCollapsed: boolean;
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    isChatCollapsed: false,
    isResourcePanelCollapsed: false,
    isSidebarCollapsed: false,
  }),

  actions: {
    toggleChat() {
      this.isChatCollapsed = !this.isChatCollapsed;
    },
    toggleResourcePanel() {
      this.isResourcePanelCollapsed = !this.isResourcePanelCollapsed;
    },
    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed;
    },
  },
});
