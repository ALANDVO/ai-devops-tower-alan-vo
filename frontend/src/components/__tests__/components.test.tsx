import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../auth/AuthContext';
import Sidebar from '../../components/Sidebar';
import SLOChart from '../../components/SLOChart';
import ReleaseNotes from '../../components/ReleaseNotes';
import IncidentTimeline from '../../components/IncidentTimeline';

// Mock api client
const { mockSloBurnRate } = vi.hoisted(() => ({
  mockSloBurnRate: vi.fn().mockResolvedValue({ objective: 0.999, burn_rate: 1.0, severity: 'none' }),
}));

vi.mock('../../api/client', () => ({
  api: {
    me: vi.fn().mockResolvedValue({ email: 'test@example.com', role: 'devops', permissions: ['pipelines:read', 'pipelines:write'] }),
    slos: vi.fn().mockResolvedValue({ slos: [] }),
    sloBurnRate: mockSloBurnRate,
  },
  User: {},
}));

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>
        {ui}
      </AuthProvider>
    </BrowserRouter>
  );
}

describe('Sidebar', () => {
  it('renders navigation links', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Pipelines')).toBeInTheDocument();
    expect(screen.getByText('Builds')).toBeInTheDocument();
    expect(screen.getByText('SLOs')).toBeInTheDocument();
    expect(screen.getByText('Incidents')).toBeInTheDocument();
    expect(screen.getByText('Releases')).toBeInTheDocument();
  });

  it('renders brand', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('DevOps Tower')).toBeInTheDocument();
    expect(screen.getByText('AI Control Center')).toBeInTheDocument();
  });

  it('shows sign out button', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('Sign Out')).toBeInTheDocument();
  });
});

describe('SLOChart', () => {
  it('renders chart container', () => {
    renderWithProviders(<SLOChart sloId="test-slo" />);
    expect(screen.getByText('Reliability Over Time')).toBeInTheDocument();
    expect(screen.getByTestId('chart-container')).toBeInTheDocument();
  });

  it('shows error state on failure', async () => {
    mockSloBurnRate.mockRejectedValueOnce(new Error('Network error'));
    
    renderWithProviders(<SLOChart sloId="test-slo" />);
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    mockSloBurnRate.mockResolvedValue({ objective: 0.999, burn_rate: 1.0, severity: 'none' });
  });
});

describe('ReleaseNotes', () => {
  it('renders plain text', () => {
    renderWithProviders(<ReleaseNotes notes="Simple release notes" />);
    expect(screen.getByText('Simple release notes')).toBeInTheDocument();
  });

  it('renders markdown headings', () => {
    renderWithProviders(<ReleaseNotes notes={`## Features
### New Feature
- Item 1
- Item 2`} />);
    expect(screen.getByText('Features')).toBeInTheDocument();
    expect(screen.getByText('New Feature')).toBeInTheDocument();
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('renders bold text', () => {
    renderWithProviders(<ReleaseNotes notes="**Bold text** and normal" />);
    expect(screen.getByText('Bold text')).toBeInTheDocument();
    expect(screen.getByText('and normal')).toBeInTheDocument();
  });

  it('renders code blocks', () => {
    renderWithProviders(<ReleaseNotes notes={`code here`} />);
    expect(screen.getByText('code here')).toBeInTheDocument();
  });
});

describe('IncidentTimeline', () => {
  it('renders timeline events', () => {
    const events = [
      { timestamp: Date.now() / 1000, actor: 'user', action: 'Created incident', details: 'Initial report' },
      { timestamp: Date.now() / 1000 - 3600, actor: 'system', action: 'Auto-assigned', details: 'Assigned to oncall' },
    ];
    renderWithProviders(<IncidentTimeline events={events} />);
    expect(screen.getByText('Created incident')).toBeInTheDocument();
    expect(screen.getByText('Auto-assigned')).toBeInTheDocument();
    expect(screen.getByText('Initial report')).toBeInTheDocument();
  });

  it('renders nothing for empty events', () => {
    renderWithProviders(<IncidentTimeline events={[]} />);
    expect(screen.queryByTestId('timeline')).not.toBeInTheDocument();
  });

  it('shows actor styling', () => {
    const events = [
      { timestamp: Date.now() / 1000, actor: 'ai', action: 'Analysis complete', details: '' },
    ];
    renderWithProviders(<IncidentTimeline events={events} />);
    const item = screen.getByTestId('timeline').firstElementChild;
    expect(item).toHaveClass('actor-ai');
  });
});