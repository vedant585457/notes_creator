import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, TYPE} from '../styles/theme';
import {ramp, fadeWindow} from '../utils/animations';
import {SCHEMATIC, sec} from '../utils/timing';

/**
 * Line-index diagram (plan §6.1). Drawn from the actual mechanism seen in the footage:
 * the crowd input overwrites the refrain line, a semicolon adds a second instruction,
 * and the RETURN jumps execution back to line 0. Schematic labels are generic line indices.
 */
const LINES = [
  {i: 0, label: 'secret_intro'},
  {i: 1, label: '[VERSE1]'},
  {i: 2, label: '…'},
  {i: 3, label: '[REFRAIN]'},
  {i: 4, label: '…'},
  {i: 5, label: 'CROWD  ← input written here'},
  {i: 6, label: '…'},
  {i: 7, label: '[END]'},
];
const ROW = 74;
const X0 = 1040;
const Y0 = 210;

export const Schematic: React.FC = () => {
  const frame = useCurrentFrame();
  const start = 0;
  const end = sec(SCHEMATIC.end - SCHEMATIC.start);
  const op = fadeWindow(frame, start, end, 14, 14);
  // Stagger rows in, then travel a highlight down the list.
  const hl = Math.min(LINES.length - 1, Math.floor(ramp(frame, 30, 60, (x) => x) * LINES.length));
  const arc = ramp(frame, 120, 70);
  const semi = ramp(frame, 200, 30);
  const jump = ramp(frame, 240, 40);
  const arcLen = 1;
  // Arc from crowd line (index 5) back to line 0, drawn as a cubic curve on the right.
  const yA = Y0 + 5 * ROW + 26;
  const y0 = Y0 + 26;
  const xa = X0 + 520;
  const d = `M ${X0 + 520} ${yA} C ${xa + 120} ${yA}, ${xa + 120} ${y0}, ${X0 + 520} ${y0}`;
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 96, top: 210, width: 780, fontFamily: FONT.mono, color: COLOR.muted, fontSize: 18, lineHeight: 1.7}}>
        <div style={{color: COLOR.amber, letterSpacing: '0.2em', fontSize: TYPE.label}}>MECHANISM · SCHEMATIC</div>
        <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: 58, color: COLOR.paper, lineHeight: 1.1, marginTop: 10}}>
          One line,<br />two instructions.
        </div>
        <div style={{marginTop: 26, color: COLOR.muted}}>
          The refrain line takes the crowd's text.<br />
          A semicolon starts a second instruction.<br />
          The return index sends execution back to line 0.
        </div>
      </div>
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        {LINES.map((l, idx) => {
          const rowIn = ramp(frame, 6 + idx * 5, 14);
          const y = Y0 + l.i * ROW;
          const active = hl === idx;
          const isCrowd = l.i === 5;
          return (
            <g key={l.i} opacity={rowIn}>
              <rect
                x={X0 - 14}
                y={y}
                width={620}
                height={52}
                fill={active ? 'rgba(255,122,47,0.10)' : 'rgba(16,19,25,0.85)'}
                stroke={isCrowd && semi > 0.5 ? COLOR.amber : COLOR.hairline}
                strokeWidth={isCrowd ? 2 : 1}
              />
              <text x={X0 + 10} y={y + 34} fontFamily={FONT.mono} fontSize={22} fill={isCrowd ? COLOR.amber : COLOR.paper}>
                {String(l.i).padStart(2, '0')}  {l.label}
              </text>
            </g>
          );
        })}
        {semi > 0 ? (
          <text
            x={X0 + 10 + 330}
            y={Y0 + 5 * ROW + 34 + 0}
            fontFamily={FONT.mono}
            fontSize={22}
            fill={COLOR.amber}
            opacity={semi}
          >
            ; RETURN 0
          </text>
        ) : null}
        <path
          d={d}
          fill="none"
          stroke={COLOR.cyan}
          strokeWidth={4}
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - arc}
          opacity={jump > 0 ? 1 : 0.9}
        />
        {jump > 0 ? (
          <text x={X0 + 560} y={y0 + 4} fontFamily={FONT.mono} fontSize={20} fill={COLOR.cyan} opacity={jump}>
            → line 0
          </text>
        ) : null}
      </svg>
      {arcLen ? null : null}
    </AbsoluteFill>
  );
};
