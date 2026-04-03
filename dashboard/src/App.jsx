import React, { useEffect, useMemo, useState } from 'react';
import StatsCard from './components/StatsCard';
import ScansTable from './components/ScansTable';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080').replace(
  /\/$/,
  '',
);

const styles = {
  app: {
    minHeight: '100vh',
    color: '#f7f4ea',
    fontFamily: '"Trebuchet MS", "Segoe UI", sans-serif',
    padding: '32px 20px 48px',
    background:
      'radial-gradient(circle at top left, rgba(246, 173, 85, 0.12), transparent 28%), linear-gradient(180deg, #07111f 0%, #0d1728 50%, #08101c 100%)',
  },
  shell: {
    maxWidth: '1100px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    gap: '16px',
    marginBottom: '28px',
    flexWrap: 'wrap',
  },
  title: {
    fontSize: '32px',
    fontWeight: 800,
    letterSpacing: '0.02em',
    color: '#f9c74f',
    marginBottom: '6px',
  },
  subtitle: {
    color: '#a9b3c4',
    fontSize: '14px',
    maxWidth: '680px',
  },
  status: {
    border: '1px solid rgba(249, 199, 79, 0.28)',
    background: 'rgba(10, 21, 38, 0.8)',
    color: '#f7f4ea',
    borderRadius: '999px',
    padding: '10px 14px',
    fontSize: '12px',
  },
  banner: {
    marginBottom: '20px',
    padding: '14px 16px',
    borderRadius: '14px',
    border: '1px solid rgba(237, 137, 54, 0.35)',
    background: 'rgba(54, 26, 8, 0.55)',
    color: '#ffd8a8',
    fontSize: '14px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
    marginBottom: '28px',
  },
};

const emptyStats = {
  total: 0,
  high: 0,
  medium: 0,
  low: 0,
  recentScans: [],
};

export default function App() {
  const [stats, setStats] = useState(emptyStats);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [backendStatus, setBackendStatus] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadStats() {
      try {
        setLoading(true);
        setError('');

        const [statsResponse, statusResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/stats`, {
            signal: controller.signal,
          }),
          fetch(`${API_BASE_URL}/config-status`, {
            signal: controller.signal,
          }),
        ]);

        if (!statsResponse.ok) {
          throw new Error(`Request failed with status ${statsResponse.status}`);
        }

        const payload = await statsResponse.json();
        setStats({
          total: payload.total ?? 0,
          high: payload.high ?? 0,
          medium: payload.medium ?? 0,
          low: payload.low ?? 0,
          recentScans: payload.recentScans ?? [],
        });

        if (statusResponse.ok) {
          setBackendStatus(await statusResponse.json());
        }
      } catch (fetchError) {
        if (fetchError.name === 'AbortError') {
          return;
        }

        setStats(emptyStats);
        setBackendStatus(null);
        setError(
          `Unable to reach the backend at ${API_BASE_URL}. Start the API to see live scan data.`,
        );
      } finally {
        setLoading(false);
      }
    }

    loadStats();
    return () => controller.abort();
  }, []);

  const statusText = useMemo(() => {
    if (loading) {
      return 'Fetching latest scan activity';
    }

    return error ? 'Offline fallback mode' : `Connected to ${API_BASE_URL}`;
  }, [error, loading]);

  const cloudWarning =
    backendStatus && !backendStatus.liveScanningReady
      ? 'Live cloud scanning is not ready yet. Add Firebase service account credentials and a GCP project ID for Vertex AI.'
      : '';

  return (
    <div style={styles.app}>
      <div style={styles.shell}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>CyberShield Dashboard</div>
            <div style={styles.subtitle}>
              Monitor phishing scan activity, risk distribution, and recent findings from one
              place.
            </div>
          </div>

          <div style={styles.status}>{statusText}</div>
        </div>

        {error && <div style={styles.banner}>{error}</div>}
        {!error && cloudWarning && <div style={styles.banner}>{cloudWarning}</div>}

        <div style={styles.grid}>
          <StatsCard label="Total Scans" value={stats.total} color="#4dabf7" />
          <StatsCard label="High Risk" value={stats.high} color="#ff6b6b" />
          <StatsCard label="Medium Risk" value={stats.medium} color="#f6ad55" />
          <StatsCard label="Safe" value={stats.low} color="#51cf66" />
        </div>

        <ScansTable scans={stats.recentScans} loading={loading} />
      </div>
    </div>
  );
}
