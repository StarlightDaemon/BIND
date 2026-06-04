import { type FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FormShell } from '../fujin/components/FormShell';
import { setup }     from '../api/endpoints';
import { ApiError }  from '../api/client';

const OUTER: React.CSSProperties = {
  minHeight:      '100vh',
  display:        'flex',
  alignItems:     'center',
  justifyContent: 'center',
  background:     'var(--fujin-bg-base)',
};

const CARD: React.CSSProperties = {
  width:   360,
  padding: 0,
};

const HEADER: React.CSSProperties = {
  textAlign:    'center',
  padding:      '24px 24px 16px',
  background:   'var(--fujin-bg-surface)',
  border:       '1px solid var(--fujin-border-subtle)',
  borderBottom: 'none',
};

const TITLE: React.CSSProperties = {
  fontFamily:    'inherit',
  fontSize:      18,
  fontWeight:    700,
  color:         'var(--fujin-text-primary)',
  margin:        '12px 0 4px',
};

const SUBTITLE: React.CSSProperties = {
  fontFamily: 'inherit',
  fontSize:   12,
  color:      'var(--fujin-text-muted)',
  margin:     0,
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

const HELPER: React.CSSProperties = {
  display:   'block',
  marginTop: 4,
  fontSize:  11,
  color:     'var(--fujin-text-muted)',
};

// BIND calendar/event SVG (retained from original setup.html)
function BindIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" fill="currentColor" style={{ color: 'var(--fujin-interactive-default)' }}>
      <path d="M26,30H6a2.0023,2.0023,0,0,1-2-2V12a2.0023,2.0023,0,0,1,2-2H26a2.0023,2.0023,0,0,1,2,2V28A2.0023,2.0023,0,0,1,26,30ZM6,12V28H26V12Z"/>
      <path d="M10,8H22a2.0023,2.0023,0,0,0,2-2V4a2.0023,2.0023,0,0,0-2-2H10A2.0023,2.0023,0,0,0,8,4V6A2.0023,2.0023,0,0,0,10,8ZM10,4H22V6H10Z"/>
      <path d="M16,16a3,3,0,1,0,3,3A3.0033,3.0033,0,0,0,16,16Zm0,4a1,1,0,1,1,1-1A1.0009,1.0009,0,0,1,16,20Z"/>
      <path d="M22,24H10v-2h.8535A4.9818,4.9818,0,0,1,16,23a4.9818,4.9818,0,0,1,5.1465-1H22Z"/>
    </svg>
  );
}

export default function SetupPage() {
  const navigate = useNavigate();
  const [fields,   setFields]  = useState({ username: '', password: '', confirm: '' });
  const [error,    setError]   = useState('');
  const [loading,  setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (fields.password !== fields.confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await setup.create(fields.username, fields.password, fields.confirm);
      navigate('/login');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Setup failed.');
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
          <BindIcon />
          <h1 style={TITLE}>Welcome to BIND</h1>
          <p style={SUBTITLE}>Create your admin account to get started</p>
        </div>
        <FormShell onSubmit={handleSubmit} submitLabel="Create Account" loading={loading} error={error}>
          <div>
            <label style={LABEL}>Username</label>
            <input
              type="text"
              style={INPUT}
              value={fields.username}
              onChange={set('username')}
              required
              pattern="[a-zA-Z0-9_]{3,32}"
              autoComplete="username"
            />
            <span style={HELPER}>3–32 characters, letters, numbers, or underscore</span>
          </div>
          <div>
            <label style={LABEL}>Password</label>
            <input
              type="password"
              style={INPUT}
              value={fields.password}
              onChange={set('password')}
              required
              minLength={8}
              autoComplete="new-password"
            />
            <span style={HELPER}>Minimum 8 characters</span>
          </div>
          <div>
            <label style={LABEL}>Confirm Password</label>
            <input
              type="password"
              style={INPUT}
              value={fields.confirm}
              onChange={set('confirm')}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
        </FormShell>
      </div>
    </div>
  );
}
