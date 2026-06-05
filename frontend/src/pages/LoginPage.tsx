import { type FormEvent, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FormShell }  from '../fujin/components/FormShell';
import { useAuth }    from '../context/AuthContext';
import { ApiError }   from '../api/client';

const OUTER: React.CSSProperties = {
  minHeight:      '100vh',
  display:        'flex',
  alignItems:     'center',
  justifyContent: 'center',
  background:     'var(--fujin-bg-base)',
};

const CARD: React.CSSProperties = {
  width: 340,
};

const HEADER: React.CSSProperties = {
  padding:      '20px 0 16px',
  borderBottom: '1px solid var(--fujin-border-subtle)',
  marginBottom: 0,
  textAlign:    'center',
};

const WORDMARK: React.CSSProperties = {
  fontFamily:    'monospace',
  fontSize:      20,
  fontWeight:    700,
  letterSpacing: 4,
  color:         'var(--fujin-text-primary)',
};

const SUBTITLE: React.CSSProperties = {
  fontFamily: 'inherit',
  fontSize:   12,
  color:      'var(--fujin-text-muted)',
  margin:     '6px 0 0',
};

const LABEL: React.CSSProperties = {
  display:      'block',
  fontSize:     12,
  fontWeight:   600,
  color:        'var(--fujin-text-secondary)',
  marginBottom: 4,
};

const INPUT: React.CSSProperties = {
  display:    'block',
  width:      '100%',
  fontFamily: 'inherit',
  fontSize:   13,
  color:      'var(--fujin-text-primary)',
  background: 'var(--fujin-bg-elevated)',
  border:     '1px solid var(--fujin-border-subtle)',
  padding:    '6px 10px',
  outline:    'none',
  boxSizing:  'border-box',
};

const NOTICE: React.CSSProperties = {
  padding:      '8px 12px',
  marginBottom: 12,
  fontSize:     12,
  color:        'var(--fujin-status-success)',
  background:   'var(--fujin-bg-elevated)',
  border:       '1px solid var(--fujin-status-success)',
  borderRadius: 2,
  textAlign:    'center',
};

export default function LoginPage() {
  const { login }  = useAuth();
  const navigate   = useNavigate();
  const location   = useLocation();
  const notice     = (location.state as { notice?: string } | null)?.notice ?? '';
  const [fields,   setFields]  = useState({ username: '', password: '' });
  const [error,    setError]   = useState('');
  const [loading,  setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(fields.username, fields.password);
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  const set = (k: keyof typeof fields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setFields((p) => ({ ...p, [k]: e.target.value }));

  return (
    <div style={OUTER}>
      <div style={CARD}>
        <div style={HEADER}>
          <div style={WORDMARK}>BIND</div>
          <p style={SUBTITLE}>Book Indexing Network Daemon</p>
        </div>
        {notice && <div style={NOTICE}>{notice}</div>}
        <FormShell onSubmit={handleSubmit} submitLabel="Sign In" loading={loading} error={error}>
          <div>
            <label style={LABEL}>Username</label>
            <input
              type="text"
              style={INPUT}
              value={fields.username}
              onChange={set('username')}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label style={LABEL}>Password</label>
            <input
              type="password"
              style={INPUT}
              value={fields.password}
              onChange={set('password')}
              autoComplete="current-password"
              required
            />
          </div>
        </FormShell>
      </div>
    </div>
  );
}
