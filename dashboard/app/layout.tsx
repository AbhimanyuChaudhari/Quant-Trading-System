import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Quant Trading System',
  description: 'Live algorithmic trading dashboard — paper trading',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
