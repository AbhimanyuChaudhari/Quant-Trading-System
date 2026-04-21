'use client';
import { useEffect, useRef } from 'react';
import { EquityPoint } from '@/lib/types';

interface Props {
  data: EquityPoint[];
  initialEquity: number;
}

export function EquityChart({ data, initialEquity }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width  = canvas.offsetWidth  * window.devicePixelRatio;
    const H = canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;

    ctx.clearRect(0, 0, w, h);

    const values   = data.map(d => d.equity);
    const minVal   = Math.min(...values, initialEquity) * 0.999;
    const maxVal   = Math.max(...values, initialEquity) * 1.001;
    const range    = maxVal - minVal;
    const padL = 60, padR = 12, padT = 12, padB = 28;
    const chartW   = w - padL - padR;
    const chartH   = h - padT - padB;

    const toX = (i: number) => padL + (i / (values.length - 1)) * chartW;
    const toY = (v: number) => padT + (1 - (v - minVal) / range) * chartH;

    // Grid lines
    ctx.strokeStyle = 'rgba(30,45,61,0.6)';
    ctx.lineWidth   = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padT + (i / 4) * chartH;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + chartW, y);
      ctx.stroke();

      const val = maxVal - (i / 4) * range;
      ctx.fillStyle = 'rgba(139,148,158,0.7)';
      ctx.font      = '10px IBM Plex Mono';
      ctx.textAlign = 'right';
      ctx.fillText('$' + val.toLocaleString('en', {maximumFractionDigits: 0}), padL - 4, y + 3);
    }

    // Baseline (initial equity)
    const baseY = toY(initialEquity);
    ctx.strokeStyle = 'rgba(139,148,158,0.3)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, baseY);
    ctx.lineTo(padL + chartW, baseY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Area fill
    const lastVal  = values[values.length - 1];
    const isUp     = lastVal >= initialEquity;
    const lineColor= isUp ? '#3fb950' : '#f85149';
    const fillColor= isUp ? 'rgba(63,185,80,0.08)' : 'rgba(248,81,73,0.08)';

    const gradient = ctx.createLinearGradient(0, padT, 0, padT + chartH);
    gradient.addColorStop(0,   isUp ? 'rgba(63,185,80,0.15)' : 'rgba(248,81,73,0.15)');
    gradient.addColorStop(1,   'rgba(0,0,0,0)');

    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(toX(i), toY(values[i]));
    }
    ctx.lineTo(toX(values.length - 1), padT + chartH);
    ctx.lineTo(toX(0), padT + chartH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(toX(i), toY(values[i]));
    }
    ctx.strokeStyle = lineColor;
    ctx.lineWidth   = 1.5;
    ctx.stroke();

    // Current price dot
    const lastX = toX(values.length - 1);
    const lastY = toY(lastVal);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();

    // Time labels
    ctx.fillStyle = 'rgba(139,148,158,0.6)';
    ctx.font      = '10px IBM Plex Mono';
    ctx.textAlign = 'center';
    const labelCount = Math.min(5, data.length);
    for (let i = 0; i < labelCount; i++) {
      const idx = Math.round(i / (labelCount - 1) * (data.length - 1));
      const ts  = new Date(data[idx].timestamp);
      const label = ts.getHours().toString().padStart(2,'0') + ':' +
                    ts.getMinutes().toString().padStart(2,'0');
      ctx.fillText(label, toX(idx), h - 6);
    }

  }, [data, initialEquity]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
}
