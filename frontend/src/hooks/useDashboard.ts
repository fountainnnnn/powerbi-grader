import { useState, useCallback } from 'react';
import { Dashboard } from '../types/api';
import { apiClient } from '../services/api';

export function useDashboard() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [currentDashboard, setCurrentDashboard] = useState<Dashboard | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboards = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.listDashboards();
      setDashboards(response.dashboards);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboards');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const uploadDashboard = useCallback(async (file: File) => {
    setError(null);
    try {
      const dashboard = await apiClient.uploadDashboard(file);
      setDashboards(prev => [dashboard, ...prev]);
      return dashboard;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to upload dashboard';
      setError(errorMsg);
      throw err;
    }
  }, []);

  const selectDashboard = useCallback((dashboard: Dashboard) => {
    setCurrentDashboard(dashboard);
    setError(null);
  }, []);

  const deleteDashboard = useCallback(async (dashboardId: string) => {
    setError(null);
    try {
      await apiClient.deleteDashboard(dashboardId);
      setDashboards(prev => prev.filter(d => d.id !== dashboardId));
      if (currentDashboard?.id === dashboardId) {
        setCurrentDashboard(null);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete dashboard';
      setError(errorMsg);
      throw err;
    }
  }, [currentDashboard?.id]);

  return {
    dashboards,
    currentDashboard,
    isLoading,
    error,
    loadDashboards,
    uploadDashboard,
    selectDashboard,
    deleteDashboard,
  };
}
