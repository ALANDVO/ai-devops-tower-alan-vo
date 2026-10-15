import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Polyfill ResizeObserver for jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock fetch for API calls
globalThis.fetch = vi.fn();

// Mock react-router
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({}),
    BrowserRouter: actual.BrowserRouter,
    NavLink: ({ children, to, className, ...props }: { children: React.ReactNode; to: string; className?: string; [key: string]: unknown }) => (
      <a href={to} className={className} {...props}>
        {children}
      </a>
    ),
  };
});