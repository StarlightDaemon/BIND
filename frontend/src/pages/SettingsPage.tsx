import { type FormEvent, useEffect, useState } from 'react';
import { BindShell }    from '../components/BindShell';
import { SectionHeader } from '../fujin/components/SectionHeader';
import { FormShell }     from '../fujin/components/FormShell';
import { useToast }      from '../fujin/components/FujinToastProvider';
import type { SettingsConfig, SettingsData } from '../api/endpoints';
import { settings } from '../api/endpoints';

const LABEL: React.CSSProperties = {
  display:      'block',
  fontFamily:   'inherit',
  fontSize:     12,
  fontWeight:   600,
  color:        'var(--fujin-text-secondary)',
  marginBottom: 4,
};

const INPUT: React.CSSProperties = {
  display:     'block',
  width:       '100%',
  fontFamily:  'inherit',
  fontSize:    13,
  color:       'var(--fujin-text-primary)',
  background:  'var(--fujin-bg-elevated)',
  border:      '1px solid var(--fujin-border-subtle)',
  padding:     '6px 10px',
  outline:     'none',
  boxSizing:   'border-box',
};

const HELPER: React.CSSProperties = {
  display:    'block',
  marginTop:  4,
  fontSize:   11,
  color:      'var(--fujin-text-muted)',
};

const SECTION_GAP: React.CSSProperties = { marginBottom: 24 };

function Field({ label, helper, children }: { label: string; helper?: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={LABEL}>{label}</label>
      {children}
      {helper && <span style={HELPER}>{helper}</span>}
    </div>
  );
}

export default function SettingsPage() {
  const toast = useToast();
  const [data,          setData]          = useState<SettingsData | null>(null);
  const [cfg,           setCfg]           = useState<Partial<SettingsConfig>>({});
  const [trackersText,  setTrackersText]  = useState('');
  const [savingCfg,     setSavingCfg]     = useState(false);
  const [savingTrackers, setSavingTrackers] = useState(false);
  const [savingPwd,     setSavingPwd]     = useState(false);
  const [pwdFields,     setPwdFields]     = useState({ current: '', next: '', confirm: '' });

  useEffect(() => {
    settings.get().then((d) => {
      setData(d);
      setCfg(d.config);
      setTrackersText(d.trackers_text);
    }).catch(() => {
      toast.show({ status: 'danger', title: 'Load failed', message: 'Could not load settings.' });
    });
  }, [toast]);

  const handleConfig = async (e: FormEvent) => {
    e.preventDefault();
    setSavingCfg(true);
    try {
      const res = await settings.save(cfg);
      toast.show({ status: res.ok ? 'success' : 'danger', message: res.message });
    } catch (err) {
      toast.show({ status: 'danger', message: err instanceof Error ? err.message : 'Save failed.' });
    } finally {
      setSavingCfg(false);
    }
  };

  const handleTrackers = async (e: FormEvent) => {
    e.preventDefault();
    setSavingTrackers(true);
    try {
      const res = await settings.trackers(trackersText);
      toast.show({ status: res.ok ? 'success' : 'danger', message: res.message });
    } catch (err) {
      toast.show({ status: 'danger', message: err instanceof Error ? err.message : 'Save failed.' });
    } finally {
      setSavingTrackers(false);
    }
  };

  const handlePassword = async (e: FormEvent) => {
    e.preventDefault();
    setSavingPwd(true);
    try {
      const res = await settings.password(pwdFields.current, pwdFields.next, pwdFields.confirm);
      toast.show({ status: res.ok ? 'success' : 'danger', message: res.message });
      if (res.ok) setPwdFields({ current: '', next: '', confirm: '' });
    } catch (err) {
      toast.show({ status: 'danger', message: err instanceof Error ? err.message : 'Change failed.' });
    } finally {
      setSavingPwd(false);
    }
  };

  const c = (key: keyof SettingsConfig) => cfg[key] ?? data?.config[key] ?? '';
  const set = (key: keyof SettingsConfig) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setCfg((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <BindShell>
      <SectionHeader title="Settings" description="Configure BIND daemon behaviour." />

      <div style={{ marginTop: 20 }}>

        {/* ── Target & Network Config ───────────────────────────────────── */}
        <div style={SECTION_GAP}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fujin-text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Target Configuration
          </div>
          <FormShell onSubmit={handleConfig} submitLabel="Save & Restart" loading={savingCfg}>
            <Field label="Target URL" helper="AudioBookBay domain (e.g., http://audiobookbay.lu)">
              <input type="url" style={INPUT} value={c('ABB_URL')} onChange={set('ABB_URL')} required />
            </Field>
            <Field label="Scraping Interval (minutes)" helper="How often to check for new content (15–1440 min)">
              <input type="number" style={INPUT} value={c('SCRAPE_INTERVAL')} onChange={set('SCRAPE_INTERVAL')} min={15} max={1440} required />
            </Field>
            <Field label="Proxy (optional)" helper="HTTP/SOCKS5 proxy for scraping">
              <input type="text" style={INPUT} value={c('BIND_PROXY')} onChange={set('BIND_PROXY')} placeholder="socks5://user:pass@proxy:1080" />
            </Field>
            <Field label="RSS Base URL Override (optional)" helper="Override auto-detected RSS feed URL">
              <input type="text" style={INPUT} value={c('BASE_URL')} onChange={set('BASE_URL')} placeholder="http://bind.mydomain.com" />
            </Field>
            <Field label="Circuit Breaker — Failure Threshold" helper="Failures before cooldown (1–10)">
              <input type="number" style={INPUT} value={c('CIRCUIT_BREAKER_THRESHOLD')} onChange={set('CIRCUIT_BREAKER_THRESHOLD')} min={1} max={10} required />
            </Field>
            <Field label="Circuit Breaker — Cooldown (seconds)" helper="Wait time after failures (60–3600)">
              <input type="number" style={INPUT} value={c('CIRCUIT_BREAKER_COOLDOWN')} onChange={set('CIRCUIT_BREAKER_COOLDOWN')} min={60} max={3600} required />
            </Field>
            <Field label="Proxy List (optional)" helper="Comma-separated proxy URLs. Overrides single BIND_PROXY.">
              <input type="text" style={INPUT} value={c('BIND_PROXIES')} onChange={set('BIND_PROXIES')} placeholder="socks5://..., http://..." />
            </Field>
            <Field label="Job Timeout (seconds)" helper="Maximum scrape job duration (60–86400). Default: 3600.">
              <input type="number" style={INPUT} value={c('BIND_JOB_TIMEOUT')} onChange={set('BIND_JOB_TIMEOUT')} min={60} max={86400} required />
            </Field>
            <Field label="IP Filter" helper="Disabling removes IP-based access control. Only for isolated networks.">
              <select style={INPUT} value={c('BIND_IP_FILTER')} onChange={set('BIND_IP_FILTER')}>
                <option value="true">Enabled (true)</option>
                <option value="false">Disabled (false)</option>
              </select>
            </Field>
            <Field label="Authentication" helper="⛔ Disabling removes all login requirements. Do NOT disable on internet-facing servers.">
              <select style={INPUT} value={c('BIND_AUTH_ENABLED')} onChange={set('BIND_AUTH_ENABLED')}>
                <option value="true">Enabled (true)</option>
                <option value="false">Disabled (false)</option>
              </select>
            </Field>
          </FormShell>
        </div>

        {/* ── Tracker Configuration ─────────────────────────────────────── */}
        <div style={SECTION_GAP}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fujin-text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Tracker Configuration
          </div>
          <FormShell onSubmit={handleTrackers} submitLabel="Update Trackers" loading={savingTrackers}>
            <Field label="Magnet Trackers" helper="One tracker URL per line. Supported: udp://, http://, https://. Changes apply retroactively.">
              <textarea
                style={{ ...INPUT, fontFamily: 'monospace', height: 160, resize: 'vertical' }}
                value={trackersText}
                onChange={(e) => setTrackersText(e.target.value)}
                placeholder={'udp://...\nhttp://...'}
              />
            </Field>
          </FormShell>
        </div>

        {/* ── Change Password ───────────────────────────────────────────── */}
        <div style={SECTION_GAP}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fujin-text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Change Password
          </div>
          <FormShell onSubmit={handlePassword} submitLabel="Change Password" loading={savingPwd}>
            <Field label="Current Password">
              <input type="password" style={INPUT} value={pwdFields.current} onChange={(e) => setPwdFields((p) => ({ ...p, current: e.target.value }))} autoComplete="current-password" required />
            </Field>
            <Field label="New Password" helper="Min 8 characters, must include a number or special character.">
              <input type="password" style={INPUT} value={pwdFields.next} onChange={(e) => setPwdFields((p) => ({ ...p, next: e.target.value }))} autoComplete="new-password" minLength={8} required />
            </Field>
            <Field label="Confirm New Password">
              <input type="password" style={INPUT} value={pwdFields.confirm} onChange={(e) => setPwdFields((p) => ({ ...p, confirm: e.target.value }))} autoComplete="new-password" minLength={8} required />
            </Field>
          </FormShell>
        </div>

      </div>
    </BindShell>
  );
}
