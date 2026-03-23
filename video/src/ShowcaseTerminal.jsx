import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';

const colors = {
  bg0: '#08111d',
  bg1: '#0e1a2a',
  card: 'rgba(11, 18, 32, 0.94)',
  card2: 'rgba(16, 28, 46, 0.95)',
  stroke: 'rgba(132, 166, 205, 0.18)',
  text: '#eff6ff',
  muted: '#bfd0e6',
  cyan: '#6ee7ff',
  green: '#5ff0b1',
  green2: '#81f7c2',
  amber: '#ffce6b',
};

export const SHOWCASE_SCENE_LENGTH = 150;
export const SHOWCASE_TRANSITION_LENGTH = 20;
export const SHOWCASE_TOTAL_FRAMES =
  SHOWCASE_SCENE_LENGTH * 5 - SHOWCASE_TRANSITION_LENGTH * 4;

const SCENE_LENGTH = SHOWCASE_SCENE_LENGTH;
const SCENE_FADE = 24;

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function typedText(text, frame, startFrame, charsPerFrame) {
  const visibleChars = Math.max(0, Math.floor((frame - startFrame) * charsPerFrame));
  return text.slice(0, Math.min(text.length, visibleChars));
}

function cursor(frame, active) {
  return active && Math.floor(frame / 6) % 2 === 0 ? '▍' : '';
}

function Shell({children, title, subtitle, frame, duration, accent = colors.green}) {
  const opacity = interpolate(frame, [0, SCENE_FADE, duration - SCENE_FADE, duration], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const lift = interpolate(frame, [0, 18], [18, 0], {extrapolateRight: 'clamp'});
  const scale = spring({frame, fps: 30, config: {damping: 200}, durationInFrames: 26});

  return (
    <AbsoluteFill style={{opacity, transform: `translateY(${lift}px)`}}>
      <div
        style={{
          position: 'absolute',
          inset: 62,
          borderRadius: 34,
          background: colors.card,
          border: `1px solid ${colors.stroke}`,
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.44)',
          overflow: 'hidden',
          transform: `scale(${0.985 + scale * 0.015})`,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            padding: '0 24px',
            background: 'rgba(255,255,255,0.02)',
            borderBottom: `1px solid rgba(255,255,255,0.06)`,
          }}
        >
          <Dot color="#ff5f56" />
          <Dot color="#ffbd2e" />
          <Dot color="#27c93f" />
          <div
            style={{
              marginLeft: 12,
              color: '#9fb5d1',
              fontFamily: 'Consolas, monospace',
              fontSize: 17,
              letterSpacing: 0.2,
            }}
          >
            bootstrap.py -&gt; run.py -&gt; analysis
          </div>
        </div>
        <div style={{padding: 32}}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 14px',
              borderRadius: 999,
              background: 'rgba(255,255,255,0.04)',
              color: accent,
              fontFamily: 'Segoe UI, system-ui, sans-serif',
              fontSize: 15,
              fontWeight: 700,
              letterSpacing: 0.8,
              textTransform: 'uppercase',
            }}
          >
            {title}
          </div>
          <div
            style={{
              marginTop: 14,
              color: colors.text,
              fontFamily: 'Segoe UI, system-ui, sans-serif',
              fontSize: 23,
              lineHeight: 1.35,
              fontWeight: 600,
            }}
          >
            {subtitle}
          </div>
          <div style={{marginTop: 22}}>{children}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Dot({color}) {
  return <div style={{width: 12, height: 12, borderRadius: 999, background: color, boxShadow: `0 0 18px ${color}`}} />;
}

function CommandLine({frame, startFrame, text, prefix = '$', accent = colors.cyan, speed = 1.0}) {
  const visible = typedText(text, frame, startFrame, speed);
  const done = visible.length >= text.length;
  return (
    <div style={{display: 'flex', gap: 10, marginBottom: 10, alignItems: 'baseline'}}>
      <span style={{color: accent, fontFamily: 'Consolas, monospace', fontSize: 19}}>{prefix}</span>
      <span style={{color: colors.text, fontFamily: 'Consolas, monospace', fontSize: 19, lineHeight: 1.5}}>
        {visible}
        {!done ? cursor(frame, true) : ''}
      </span>
    </div>
  );
}

function OutputLine({frame, startFrame, text, accent = colors.muted, prefix = '>' , speed = 0.9}) {
  const visible = typedText(text, frame, startFrame, speed);
  const done = visible.length >= text.length;
  return (
    <div style={{display: 'flex', gap: 10, marginBottom: 8, alignItems: 'baseline'}}>
      <span style={{color: accent, fontFamily: 'Consolas, monospace', fontSize: 18, opacity: 0.9}}>{prefix}</span>
      <span style={{color: colors.text, fontFamily: 'Consolas, monospace', fontSize: 18, lineHeight: 1.5}}>
        {visible}
        {!done ? cursor(frame, true) : ''}
      </span>
    </div>
  );
}

function Pill({children, active = false, color = colors.cyan}) {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '8px 12px',
        borderRadius: 999,
        marginRight: 10,
        marginBottom: 10,
        background: active ? `linear-gradient(135deg, ${color}22, ${color}10)` : 'rgba(255,255,255,0.04)',
        border: `1px solid ${active ? `${color}66` : 'rgba(255,255,255,0.06)'}`,
        color: active ? colors.text : colors.muted,
        fontFamily: 'Consolas, monospace',
        fontSize: 15,
      }}
    >
      {children}
    </div>
  );
}

function Metric({label, value, fill, color = colors.cyan}) {
  return (
    <div style={{marginBottom: 14}}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: colors.muted,
          fontFamily: 'Segoe UI, system-ui, sans-serif',
          fontSize: 15,
          marginBottom: 8,
        }}
      >
        <span>{label}</span>
        <span style={{color: colors.text, fontWeight: 600}}>{value}</span>
      </div>
      <div style={{height: 10, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${Math.max(0, Math.min(1, fill)) * 100}%`, borderRadius: 999, background: color}} />
      </div>
    </div>
  );
}

function Panel({title, children}) {
  return (
    <div
      style={{
        borderRadius: 22,
        background: colors.card2,
        border: `1px solid ${colors.stroke}`,
        padding: 18,
      }}
    >
      <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16, color: colors.muted, marginBottom: 10}}>
        {title}
      </div>
      {children}
    </div>
  );
}

function TerminalSceneOne({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 200}, durationInFrames: 32});
  const cmdStart = 8;
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 20% 20%, rgba(110,231,255,0.18), transparent 22%), radial-gradient(circle at 78% 18%, rgba(95,240,177,0.14), transparent 25%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <Backdrop frame={frame} />
      <Shell title="DVRR Autopilot" subtitle="Public.com portfolio copilot for any AI agent" frame={frame} duration={SCENE_LENGTH} accent={colors.green}>
        <div style={{display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: 24, alignItems: 'stretch'}}>
          <div>
            <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 54, lineHeight: 1.02, fontWeight: 800, color: colors.text, maxWidth: 560, transform: `translateY(${(1 - intro) * 18}px)`}}>
              One command. One holding. One answer.
            </div>
            <div style={{marginTop: 16, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 20, lineHeight: 1.45, maxWidth: 560}}>
              The skill loads the live portfolio, classifies the market, and gives a buy / hold / sell call without placing trades.
            </div>
            <div style={{marginTop: 24, borderRadius: 22, background: 'rgba(6, 12, 20, 0.98)', border: `1px solid ${colors.stroke}`, padding: 20, boxShadow: '0 18px 40px rgba(0,0,0,0.28)'}}>
              <CommandLine frame={frame} startFrame={cmdStart} text="python bootstrap.py --symbol GOOG" prefix="$" accent={colors.cyan} speed={1.2} />
              <OutputLine frame={frame} startFrame={32} text="installing deps and preparing env" prefix=">" accent={colors.green} speed={1.0} />
              <OutputLine frame={frame} startFrame={58} text="loading live Public.com portfolio" prefix=">" accent={colors.text} speed={1.0} />
              <OutputLine frame={frame} startFrame={82} text="analyzing SPY + one holding" prefix=">" accent={colors.text} speed={1.0} />
              <OutputLine frame={frame} startFrame={108} text="result: HOLD candidate" prefix=">" accent={colors.green} speed={1.05} />
            </div>
            <div style={{marginTop: 18, display: 'flex', flexWrap: 'wrap'}}>
              <Pill active color={colors.green}>ANALYZE default</Pill>
              <Pill>live portfolio</Pill>
              <Pill>single-symbol focus</Pill>
              <Pill>no trades required</Pill>
            </div>
          </div>
          <Panel title="Run summary">
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14}}>
              <SummaryCard label="Equity" value={`$${data.accountEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} accent={colors.green} />
              <SummaryCard label="Positions" value={`${data.positionCount}`} accent={colors.cyan} />
              <SummaryCard label="Mode" value="ANALYZE" accent={colors.green2} />
              <SummaryCard label="Target" value={data.symbol} accent={colors.amber} />
            </div>
            <div style={{marginTop: 18, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16, lineHeight: 1.5}}>
              Built for any AI agent that can run Python.
            </div>
          </Panel>
        </div>
      </Shell>
    </AbsoluteFill>
  );
}

function TerminalSceneTwo({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 200}, durationInFrames: 34});
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <Backdrop frame={frame} />
      <Shell title="Portfolio context" subtitle="The skill loads the account first, then narrows to one symbol" frame={frame} duration={SCENE_LENGTH} accent={colors.cyan}>
        <div style={{display: 'grid', gridTemplateColumns: '1.02fr 0.98fr', gap: 24}}>
          <Panel title="Terminal session">
            <div style={{opacity: reveal}}>
              <CommandLine frame={frame} startFrame={8} text="inspect live portfolio" prefix="$" accent={colors.cyan} speed={1.05} />
              <OutputLine frame={frame} startFrame={32} text="account id: 5OR90034" prefix="account" accent={colors.green} speed={0.95} />
              <OutputLine frame={frame} startFrame={54} text="equity: $2,151.71" prefix="equity" accent={colors.green} speed={0.95} />
              <OutputLine frame={frame} startFrame={76} text="positions: 9 holdings" prefix="positions" accent={colors.text} speed={0.95} />
              <OutputLine frame={frame} startFrame={98} text="random selection: GOOG" prefix="focus" accent={colors.cyan} speed={0.95} />
              <OutputLine frame={frame} startFrame={120} text="analysis scope: SINGLE_SYMBOL" prefix="scope" accent={colors.green} speed={0.95} />
            </div>
          </Panel>
          <div>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14}}>
              <SummaryCard label="Account" value="Live" accent={colors.green} />
              <SummaryCard label="Mode" value="Read-only" accent={colors.cyan} />
              <SummaryCard label="Input" value="GOOG" accent={colors.amber} />
              <SummaryCard label="Result" value="1 holding" accent={colors.green2} />
            </div>
            <div style={{marginTop: 18}}>
              <Panel title="Holdings sample">
                <div style={{marginBottom: 12}}>
                  <Pill active color={colors.green}>GOOG</Pill>
                  <Pill>NVDA</Pill>
                  <Pill>OKLO</Pill>
                  <Pill>XOM</Pill>
                  <Pill>and 5 more</Pill>
                </div>
                <div style={{marginTop: 8, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 22, lineHeight: 1.4, fontWeight: 700}}>
                  The job is not to scan everything. It is to answer the next decision clearly.
                </div>
              </Panel>
            </div>
          </div>
        </div>
      </Shell>
    </AbsoluteFill>
  );
}

function TerminalSceneThree({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const prog = spring({frame, fps, config: {damping: 200}, durationInFrames: 30});
  const trendFill = data.sleeveTrend;
  const breakoutFill = data.sleeveBreakout;
  const reversionFill = data.sleeveReversion;
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <Backdrop frame={frame} />
      <Shell title="Regime detection" subtitle="SPY determines whether the portfolio leans trend, breakout, or reversion" frame={frame} duration={SCENE_LENGTH} accent={colors.green}>
        <div style={{display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 24}}>
          <Panel title="Terminal session">
            <div style={{transform: `translateX(${(1 - prog) * -14}px)`}}>
              <CommandLine frame={frame} startFrame={8} text="fetch SPY + GOOG bars" prefix="$" accent={colors.cyan} speed={1.05} />
              <OutputLine frame={frame} startFrame={32} text="classify market regime" prefix=">" accent={colors.text} speed={0.92} />
              <OutputLine frame={frame} startFrame={56} text={`trend: ${data.regimeTrend} (${Math.round(data.trendConfidence * 100)}%)`} prefix="trend" accent={colors.green} speed={0.92} />
              <OutputLine frame={frame} startFrame={82} text={`volatility: ${data.regimeVolatility}`} prefix="vol" accent={colors.cyan} speed={0.92} />
              <OutputLine frame={frame} startFrame={106} text="weights: 55 / 30 / 15" prefix="weights" accent={colors.amber} speed={0.92} />
              <OutputLine frame={frame} startFrame={128} text="trade gate: OPEN" prefix="gate" accent={colors.green} speed={0.95} />
            </div>
          </Panel>
          <div>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12}}>
              <SummaryCard label="Trend" value={data.regimeTrend} accent={colors.green} />
              <SummaryCard label="Volatility" value={data.regimeVolatility} accent={colors.cyan} />
              <SummaryCard label="Tradability" value={data.tradability.toFixed(2)} accent={colors.amber} />
            </div>
            <div style={{marginTop: 16, padding: 18, borderRadius: 22, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
              <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 10, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 15}}>
                <span>Sleeve allocation</span>
                <span>Trend 55 / Breakout 30 / Reversion 15</span>
              </div>
              <div style={{height: 14, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
                <div style={{height: '100%', width: `${trendFill * 100}%`, background: colors.green}} />
                <div style={{height: '100%', width: `${breakoutFill * 100}%`, background: colors.cyan, marginTop: -14, marginLeft: `${trendFill * 100}%`}} />
                <div style={{height: '100%', width: `${reversionFill * 100}%`, background: colors.amber, marginTop: -14, marginLeft: `${(trendFill + breakoutFill) * 100}%`}} />
              </div>
              <div style={{marginTop: 16, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 22, lineHeight: 1.4, fontWeight: 700}}>
                A downtrend does not force a sell. It tells the skill to stay selective.
              </div>
            </div>
          </div>
        </div>
      </Shell>
    </AbsoluteFill>
  );
}

function TerminalSceneFour({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pulse = spring({frame, fps, config: {damping: 200}, durationInFrames: 30});
  const points = [0.42, 0.44, 0.43, 0.46, 0.45, 0.48, 0.49, 0.48, 0.5, 0.52, 0.51, 0.53, 0.54, 0.55, 0.54, 0.56];
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${70 + (i * 520) / (points.length - 1)} ${250 - p * 170}`)
    .join(' ');
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <Backdrop frame={frame} />
      <Shell title={`Single-stock analysis: ${data.symbol}`} subtitle="The skill narrows to one ticker, computes indicators, then returns a call" frame={frame} duration={SCENE_LENGTH} accent={colors.green}>
        <div style={{display: 'grid', gridTemplateColumns: '0.93fr 1.07fr', gap: 24}}>
          <Panel title="Terminal session">
            <CommandLine frame={frame} startFrame={8} text={`score ${data.symbol} with indicators`} prefix="$" accent={colors.cyan} speed={1.05} />
            <OutputLine frame={frame} startFrame={32} text={`price ${data.price.toFixed(2)} | sma50 ${data.sma50.toFixed(2)} | sma200 ${data.sma200.toFixed(2)}`} prefix="price" accent={colors.text} speed={0.92} />
            <OutputLine frame={frame} startFrame={58} text={`rsi ${data.rsi.toFixed(1)} | macd +${data.macdHist.toFixed(4)}`} prefix="rsi" accent={colors.amber} speed={0.92} />
            <OutputLine frame={frame} startFrame={82} text={`3m ${data.momentum3m.toFixed(2)}% | 6m ${data.momentum6m.toFixed(2)}%`} prefix="momentum" accent={colors.cyan} speed={0.92} />
            <OutputLine frame={frame} startFrame={108} text={`trend score +${data.trendScore.toFixed(4)}`} prefix="score" accent={colors.green} speed={0.95} />
          </Panel>
          <div>
            <Panel title="Trend footprint">
              <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 8, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 15}}>
                <span>recent pullback</span>
                <span>longer-term uptrend</span>
              </div>
              <svg viewBox="0 0 640 320" style={{width: '100%', marginTop: 10}}>
                <defs>
                  <linearGradient id="line" x1="0" x2="1">
                    <stop offset="0%" stopColor={colors.cyan} stopOpacity="0.9" />
                    <stop offset="100%" stopColor={colors.green} stopOpacity="1" />
                  </linearGradient>
                  <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor={colors.green} stopOpacity="0.28" />
                    <stop offset="100%" stopColor={colors.green} stopOpacity="0.02" />
                  </linearGradient>
                </defs>
                <path d={`${path} L 590 310 L 70 310 Z`} fill="url(#fill)" />
                <path d={path} stroke="url(#line)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx={570} cy={250 - points[points.length - 1] * 170} r="8" fill={colors.green} />
              </svg>
            </Panel>
            <div style={{marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12}}>
              <SummaryCard label="Signal" value="HOLD" accent={colors.green} />
              <SummaryCard label="Bias" value="Neutral" accent={colors.cyan} />
              <SummaryCard label="Read" value="Mixed" accent={colors.amber} />
              <SummaryCard label="Scope" value="Single" accent={colors.green2} />
            </div>
            <div style={{marginTop: 16}}>
              <Metric label="Trend score" value={data.trendScore.toFixed(4)} fill={clamp01((data.trendScore + 0.25) / 0.5)} color={colors.green} />
            </div>
            <div style={{marginTop: 8, transform: `scale(${0.98 + pulse * 0.02})`}}>
              <Panel title="Decision context">
                <div style={{color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 22, lineHeight: 1.4, fontWeight: 700}}>
                  Trend score is just above zero, which makes HOLD the disciplined call.
                </div>
              </Panel>
            </div>
          </div>
        </div>
      </Shell>
    </AbsoluteFill>
  );
}

function TerminalSceneFive({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 200}, durationInFrames: 36});
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 40% 30%, rgba(95,240,177,0.14), transparent 26%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <Backdrop frame={frame} />
      <Shell title="Outcome" subtitle="The safest call on this holding is to stay patient" frame={frame} duration={SCENE_LENGTH} accent={colors.green}>
        <div style={{display: 'grid', gridTemplateColumns: '1.02fr 0.98fr', gap: 24, alignItems: 'stretch'}}>
          <Panel title="Final terminal session">
            <CommandLine frame={frame} startFrame={8} text="final decision" prefix="$" accent={colors.cyan} speed={1.0} />
            <OutputLine frame={frame} startFrame={34} text={`GOOG is a ${data.verdict} candidate`} prefix=">" accent={colors.green} speed={0.95} />
            <OutputLine frame={frame} startFrame={58} text="no trades proposed" prefix=">" accent={colors.text} speed={0.95} />
            <OutputLine frame={frame} startFrame={82} text="ANALYZE first, SUGGEST second" prefix=">" accent={colors.text} speed={0.95} />
            <OutputLine frame={frame} startFrame={108} text="python bootstrap.py --symbol GOOG" prefix=">" accent={colors.green} speed={1.0} />
          </Panel>
          <Panel title="Judge-friendly close">
            <div style={{transform: `translateY(${(1 - reveal) * 8}px)`}}>
              <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 66, lineHeight: 1, fontWeight: 900, color: colors.green}}>
                {data.verdict}
              </div>
              <div style={{marginTop: 14, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 27, lineHeight: 1.35, fontWeight: 800}}>
                {data.symbol} is a hold candidate, not an aggressive buy.
              </div>
              <div style={{marginTop: 16, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18, lineHeight: 1.55}}>
                This is a portfolio-aware, single-symbol decision produced from live account context and market regime detection.
              </div>
            </div>
            <div style={{marginTop: 22, display: 'flex', flexWrap: 'wrap'}}>
              <Pill active color={colors.green}>single-symbol</Pill>
              <Pill>0 trades proposed</Pill>
              <Pill>analysis_scope: portfolio-aware</Pill>
            </div>
            <div style={{marginTop: 20, padding: 18, borderRadius: 18, background: 'rgba(95,240,177,0.08)', border: '1px solid rgba(95,240,177,0.24)'}}>
              <div style={{color: colors.green2, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 15, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase'}}>
                Reproducible
              </div>
              <div style={{marginTop: 8, color: colors.text, fontFamily: 'Consolas, monospace', fontSize: 20, fontWeight: 700}}>
                python bootstrap.py --symbol GOOG
              </div>
            </div>
            <div style={{marginTop: 18, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 17, lineHeight: 1.45}}>
              Use the DVRR Autopilot skill with any AI agent that can execute Python.
            </div>
          </Panel>
        </div>
      </Shell>
    </AbsoluteFill>
  );
}

function SummaryCard({label, value, accent = colors.text}) {
  return (
    <div style={{borderRadius: 18, padding: 16, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)'}}>
      <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 15, color: colors.muted}}>{label}</div>
      <div style={{marginTop: 8, fontFamily: 'Consolas, monospace', fontSize: 24, fontWeight: 700, color: accent}}>{value}</div>
    </div>
  );
}

function Backdrop({frame}) {
  const drift = interpolate(frame, [0, 500], [0, 48]);
  const lines = [];
  for (let x = 0; x <= 1280; x += 96) {
    lines.push(<line key={`v-${x}`} x1={x} y1={0} x2={x} y2={720} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />);
  }
  for (let y = 0; y <= 720; y += 96) {
    lines.push(<line key={`h-${y}`} x1={0} y1={y} x2={1280} y2={y} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />);
  }
  return (
    <svg width={1280} height={720} style={{position: 'absolute', inset: 0, opacity: 0.22}}>
      <g transform={`translate(${drift * 0.2}, ${drift * 0.1})`}>{lines}</g>
    </svg>
  );
}

export function DVRRShowcaseTerminal(props) {
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`,
        color: colors.text,
      }}
      >
        <IntroGlow />
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={SCENE_LENGTH}>
          <TerminalSceneOne data={props} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: SHOWCASE_TRANSITION_LENGTH})}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_LENGTH}>
          <TerminalSceneTwo data={props} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: SHOWCASE_TRANSITION_LENGTH})}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_LENGTH}>
          <TerminalSceneThree data={props} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: SHOWCASE_TRANSITION_LENGTH})}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_LENGTH}>
          <TerminalSceneFour data={props} />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: SHOWCASE_TRANSITION_LENGTH})}
        />
        <TransitionSeries.Sequence durationInFrames={SCENE_LENGTH}>
          <TerminalSceneFive data={props} />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
}

function IntroGlow() {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const shift = interpolate(frame, [0, durationInFrames], [0, 48]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 18% 18%, rgba(110,231,255,0.16), transparent 24%), radial-gradient(circle at 80% 18%, rgba(95,240,177,0.12), transparent 26%), radial-gradient(circle at 82% 82%, rgba(122,163,255,0.12), transparent 26%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`,
      }}
    >
      <svg width={1280} height={720} style={{position: 'absolute', inset: 0, opacity: 0.34}}>
        <circle cx={260 + shift * 0.4} cy={140} r={180} fill="rgba(110,231,255,0.08)" />
        <circle cx={1040 - shift * 0.2} cy={160} r={220} fill="rgba(95,240,177,0.08)" />
        <circle cx={990} cy={620 - shift * 0.3} r={260} fill="rgba(122,163,255,0.05)" />
      </svg>
    </AbsoluteFill>
  );
}
