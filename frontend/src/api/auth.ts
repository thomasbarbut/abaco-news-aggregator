import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { User } from '@/types';

export const authKeys = {
  me: ['auth', 'me'] as const,
};

// ── Current user ─────────────────────────────────────────────────────────
export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

// ── Get login URL ─────────────────────────────────────────────────────────
export function useGetLoginUrl() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.get<{ auth_url: string; state: string }>('/auth/login');
      return data;
    },
  });
}

// ── Refresh token ─────────────────────────────────────────────────────────
export function useRefresh() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<{
        access_token: string;
        token_type: string;
        expires_in: number;
      }>('/auth/refresh');
      return data;
    },
  });
}

// ── Logout ────────────────────────────────────────────────────────────────
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      // Clear server-side session if endpoint exists
      try {
        await apiClient.post('/auth/logout');
      } catch {
        // Best-effort
      }
    },
    onSettled: () => {
      queryClient.clear();
    },
  });
}
