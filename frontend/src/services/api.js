import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendChatMessage = async (prompt, mandateNonce = null) => {
  const response = await apiClient.post('/chat', {
    prompt,
    mandate_nonce: mandateNonce,
  });
  return response.data;
};

export const updateMandate = async (maxSpendInr, durationMinutes = 60) => {
  const response = await apiClient.post('/mandate', {
    max_spend_inr: parseFloat(maxSpendInr),
    duration_minutes: parseInt(durationMinutes, 10),
  });
  return response.data;
};

export const refreshMandate = async (maxSpendInr = 2000, durationMinutes = 60) => {
  const response = await apiClient.post('/mandate/refresh', {
    max_spend_inr: parseFloat(maxSpendInr),
    duration_minutes: parseInt(durationMinutes, 10),
  });
  return response.data;
};

export const revokeMandate = async (nonce = null) => {
  const response = await apiClient.post('/mandate/revoke', {
    nonce: nonce,
  });
  return response.data;
};

export const getMandate = async () => {
  const response = await apiClient.get('/mandate');
  return response.data;
};

export const getCatalog = async () => {
  const response = await apiClient.get('/catalog');
  return response.data;
};

export const getAuditLogs = async () => {
  const response = await apiClient.get('/audit-logs');
  return response.data;
};

export const subscribeAuditStream = (onLogReceived) => {
  const eventSource = new EventSource(`${API_BASE_URL}/audit-stream`);

  eventSource.addEventListener('audit_event', (event) => {
    try {
      const data = JSON.parse(event.data);
      onLogReceived(data);
    } catch (err) {
      console.error('Failed to parse SSE audit log event', err);
    }
  });

  eventSource.onerror = (err) => {
    console.error('EventSource SSE connection error:', err);
  };

  return () => {
    eventSource.close();
  };
};

export default apiClient;
