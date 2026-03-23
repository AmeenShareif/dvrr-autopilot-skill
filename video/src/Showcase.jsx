import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

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

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function SceneShell({children, title, subtitle, frame, duration, accent = colors.green}) {
  const opacity = interpolate(frame, [0, 8, duration - 8, duration], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, [0, 12], [18, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity, transform: `translateY(${y}px)`}}>
      <div
        style={{
          position: 'absolute',
          inset: 72,
          borderRadius: 32,
          background: colors.card,
          border: `1px solid ${colors.stroke}`,
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.42)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: 62,
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
              fontFamily: 'Segoe UI, system-ui, sans-serif',
              fontSize: 18,
              letterSpacing: 0.3,
            }}
          >
            bootstrap.py -&gt; run.py -&gt; analysis
          </div>
        </div>
        <div style={{padding: 34}}>
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
              fontSize: 16,
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
              fontSize: 22,
              lineHeight: 1.35,
              fontWeight: 600,
            }}
          >
            {subtitle}
          </div>
          <div style={{marginTop: 24}}>{children}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Dot({color}) {
  return <div style={{width: 12, height: 12, borderRadius: 999, background: color, boxShadow: `0 0 18px ${color}`}} />;
}

function Metric({label, value, width = 1, color = colors.cyan}) {
  return (
    <div style={{marginBottom: 16}}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: colors.muted,
          fontFamily: 'Segoe UI, system-ui, sans-serif',
          fontSize: 16,
          marginBottom: 8,
        }}
      >
        <span>{label}</span>
        <span style={{color: colors.text, fontWeight: 600}}>{value}</span>
      </div>
      <div style={{height: 10, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${Math.max(0, Math.min(1, width)) * 100}%`, borderRadius: 999, background: color}} />
      </div>
    </div>
  );
}

function Chip({children, active = false, color = colors.cyan}) {
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
        fontSize: 16,
      }}
    >
      {children}
    </div>
  );
}

function Gauge({value, min, max, label, accent, lowLabel, highLabel}) {
  const normalized = clamp01((value - min) / (max - min));
  return (
    <div style={{marginTop: 20}}>
      <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 8}}>
        <span style={{color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16}}>{label}</span>
        <span style={{color: colors.text, fontFamily: 'Consolas, monospace', fontSize: 16}}>{value.toFixed(2)}</span>
      </div>
      <div
        style={{
          position: 'relative',
          height: 14,
          borderRadius: 999,
          background: 'rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        <div style={{position: 'absolute', inset: 0, width: `${normalized * 100}%`, background: accent, borderRadius: 999}} />
        <div
          style={{
            position: 'absolute',
            left: `${normalized * 100}%`,
            top: -4,
            width: 22,
            height: 22,
            marginLeft: -11,
            borderRadius: 999,
            background: '#fff',
            boxShadow: `0 0 0 5px ${accent}33`,
          }}
        />
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 8, color: colors.muted, fontSize: 13, fontFamily: 'Segoe UI, system-ui, sans-serif'}}>
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  );
}

function HeroScene({data}) {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 200}, durationInFrames: 34});
  const commandChars = Math.floor(interpolate(frame, [0, 30], [0, 58], {extrapolateRight: 'clamp'}));
  const command = 'python bootstrap.py --symbol GOOG';
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 20% 20%, rgba(110,231,255,0.18), transparent 22%), radial-gradient(circle at 78% 18%, rgba(95,240,177,0.14), transparent 25%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <FloatingGrid frame={frame} />
      <SceneShell
        title="DVRR Autopilot"
        subtitle="Public.com portfolio copilot for any AI agent"
        frame={frame}
        duration={70}
        accent={colors.green}
      >
        <div style={{display: 'grid', gridTemplateColumns: '1.08fr 0.92fr', gap: 24, alignItems: 'stretch'}}>
          <div>
            <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 56, lineHeight: 1.02, fontWeight: 800, color: colors.text, maxWidth: 560, transform: `translateY(${(1 - intro) * 18}px)`}}>
              One command. One holding. One answer.
            </div>
            <div style={{marginTop: 18, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 20, lineHeight: 1.45, maxWidth: 570}}>
              Load the live Public.com portfolio, classify the market, and return a buy / hold / sell call without placing trades.
            </div>
            <div style={{marginTop: 26, padding: 18, borderRadius: 20, background: colors.card2, border: `1px solid ${colors.stroke}`, fontFamily: 'Consolas, monospace', color: colors.text, fontSize: 21, boxShadow: '0 18px 40px rgba(0,0,0,0.26)'}}>
              <span style={{color: colors.cyan}}>$ </span>
              <span>{command.slice(0, commandChars)}</span>
              <span style={{opacity: 0.7}}>|</span>
            </div>
            <div style={{marginTop: 22, display: 'flex', gap: 12, flexWrap: 'wrap'}}>
              <Chip active color={colors.green}>ANALYZE default</Chip>
              <Chip>live portfolio</Chip>
              <Chip>single-symbol focus</Chip>
              <Chip>no trades required</Chip>
            </div>
          </div>
          <div style={{alignSelf: 'stretch'}}>
            <div style={{height: '100%', borderRadius: 24, background: 'linear-gradient(180deg, rgba(8,17,29,0.95), rgba(14,26,42,0.96))', border: '1px solid rgba(255,255,255,0.07)', padding: 24}}>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14}}>
                <SummaryCard label="Equity" value={`$${data.accountEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} />
                <SummaryCard label="Positions" value={`${data.positionCount}`} />
                <SummaryCard label="Mode" value="ANALYZE" accent={colors.green} />
                <SummaryCard label="Target" value={data.symbol} accent={colors.cyan} />
              </div>
              <div style={{marginTop: 18, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16}}>
                Built for any AI agent that can run Python.
              </div>
            </div>
          </div>
        </div>
      </SceneShell>
    </AbsoluteFill>
  );
}

function SummaryCard({label, value, accent = colors.text}) {
  return (
    <div style={{borderRadius: 18, padding: 18, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)'}}>
      <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16, color: colors.muted}}>{label}</div>
      <div style={{marginTop: 10, fontFamily: 'Consolas, monospace', fontSize: 26, fontWeight: 700, color: accent}}>{value}</div>
    </div>
  );
}

function PortfolioScene({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const prog = spring({frame, fps, config: {damping: 200}, durationInFrames: 32});
  const chipOpacity = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <FloatingGrid frame={frame} />
      <SceneShell
        title="Portfolio context"
        subtitle="The skill loads the live account first, then narrows the analysis to one symbol"
        frame={frame}
        duration={70}
        accent={colors.cyan}
      >
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24}}>
          <div style={{transform: `translateX(${(1 - prog) * -18}px)`}}>
            <Metric label="Account equity" value={`$${data.accountEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} width={0.98} color={colors.green} />
            <Metric label="Positions" value={`${data.positionCount}`} width={0.72} color={colors.cyan} />
            <Metric label="Mode" value="SUGGEST / ANALYZE" width={0.88} color={colors.amber} />
            <Metric label="API flow" value="Public.com + Polygon" width={0.94} color={colors.green2} />
          </div>
          <div style={{opacity: chipOpacity}}>
            <div style={{color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16, marginBottom: 10}}>Example holdings</div>
            <div>
              <Chip active color={colors.green}>GOOG</Chip>
              <Chip>NVDA</Chip>
              <Chip>OKLO</Chip>
              <Chip>XOM</Chip>
              <Chip>and 5 more</Chip>
            </div>
            <div style={{marginTop: 20, padding: 18, borderRadius: 20, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
              <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 17, color: colors.muted}}>Why it matters</div>
              <div style={{marginTop: 10, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 24, lineHeight: 1.4, fontWeight: 700}}>
                Judges can see the skill is portfolio-aware, not just ticker-aware.
              </div>
            </div>
          </div>
        </div>
      </SceneShell>
    </AbsoluteFill>
  );
}

function RegimeScene({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const grow = spring({frame, fps, config: {damping: 200}, durationInFrames: 28});
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <FloatingGrid frame={frame} />
      <SceneShell
        title="Regime detection"
        subtitle="SPY determines whether the portfolio leans trend, breakout, or reversion"
        frame={frame}
        duration={75}
        accent={colors.green}
      >
        <div style={{display: 'grid', gridTemplateColumns: '1.12fr 0.88fr', gap: 24}}>
          <div>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14}}>
              <SummaryCard label="Trend" value={data.regimeTrend} accent={colors.green} />
              <SummaryCard label="Volatility" value={data.regimeVolatility} accent={colors.cyan} />
              <SummaryCard label="Tradability" value={data.tradability.toFixed(2)} accent={colors.amber} />
            </div>
            <div style={{marginTop: 22, padding: 20, borderRadius: 22, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
              <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 8, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16}}>
                <span>Sleeve weights</span>
                <span>Trend 55 / Breakout 30 / Reversion 15</span>
              </div>
              <div style={{height: 14, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
                <div style={{height: '100%', width: `${data.sleeveTrend * 100}%`, background: colors.green}} />
                <div style={{height: '100%', width: `${data.sleeveBreakout * 100}%`, background: colors.cyan, marginTop: -14, marginLeft: `${data.sleeveTrend * 100}%`}} />
                <div style={{height: '100%', width: `${data.sleeveReversion * 100}%`, background: colors.amber, marginTop: -14, marginLeft: `${(data.sleeveTrend + data.sleeveBreakout) * 100}%`}} />
              </div>
              <div style={{marginTop: 16, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 24, lineHeight: 1.4, fontWeight: 700}}>
                A downtrend does not force a sell. It tells the skill to stay selective.
              </div>
            </div>
          </div>
          <div style={{transform: `scale(${0.98 + grow * 0.02})`}}>
            <Gauge
              label="Trend confidence"
              value={data.trendConfidence * 100}
              min={0}
              max={100}
              accent={colors.green}
              lowLabel="low"
              highLabel="high"
            />
            <div style={{marginTop: 22, padding: 18, borderRadius: 20, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
              <div style={{color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16}}>Model context</div>
              <div style={{marginTop: 10, fontFamily: 'Consolas, monospace', fontSize: 18, color: colors.text, lineHeight: 1.65}}>
                regime = {data.regimeTrend} / {data.regimeVolatility}
                <br />
                trading = {'>'} 0.50 tradability
                <br />
                no execution unless requested
              </div>
            </div>
          </div>
        </div>
      </SceneShell>
    </AbsoluteFill>
  );
}

function StockScene({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const floatIn = spring({frame, fps, config: {damping: 200}, durationInFrames: 30});
  const meter = interpolate(data.trendScore, [-0.25, 0, 0.25], [0, 0.5, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const points = [0.42, 0.44, 0.43, 0.46, 0.45, 0.48, 0.49, 0.48, 0.5, 0.52, 0.51, 0.53, 0.54, 0.55, 0.54, 0.56];
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${70 + (i * 520) / (points.length - 1)} ${250 - p * 170}`)
    .join(' ');
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <FloatingGrid frame={frame} />
      <SceneShell
        title={`Single-stock analysis: ${data.symbol}`}
        subtitle="The skill narrows to one ticker, computes indicators, then returns a call"
        frame={frame}
        duration={75}
        accent={colors.green}
      >
        <div style={{display: 'grid', gridTemplateColumns: '0.95fr 1.05fr', gap: 24}}>
          <div style={{padding: 20, borderRadius: 24, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
              <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 42, fontWeight: 800, color: colors.text}}>{data.symbol}</div>
              <div style={{fontFamily: 'Consolas, monospace', fontSize: 30, color: colors.green}}>${data.price.toFixed(2)}</div>
            </div>
            <div style={{marginTop: 12, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18}}>
              Trend score is barely positive, which means hold is safer than aggressive adding.
            </div>
            <div style={{marginTop: 18}}>
              <Metric label="SMA(50)" value={`$${data.sma50.toFixed(2)}`} width={0.66} color={colors.cyan} />
              <Metric label="SMA(200)" value={`$${data.sma200.toFixed(2)}`} width={0.84} color={colors.green} />
              <Metric label="RSI(14)" value={data.rsi.toFixed(1)} width={data.rsi / 100} color={colors.amber} />
              <Metric label="MACD hist" value={data.macdHist.toFixed(4)} width={0.58} color={colors.green2} />
            </div>
          </div>
          <div style={{padding: 20, borderRadius: 24, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
            <div style={{display: 'flex', justifyContent: 'space-between', color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16}}>
              <span>Trend footprint</span>
              <span>3m {data.momentum3m.toFixed(2)}% | 6m {data.momentum6m.toFixed(2)}%</span>
            </div>
            <svg viewBox="0 0 640 320" style={{width: '100%', marginTop: 14}}>
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
            <div style={{marginTop: 6, display: 'flex', justifyContent: 'space-between', color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 14}}>
              <span>recent pullback</span>
              <span>longer-term uptrend</span>
            </div>
            <div style={{marginTop: 18, transform: `scale(${0.98 + floatIn * 0.02})`}}>
              <Gauge
                label="Trend score"
                value={data.trendScore}
                min={-0.25}
                max={0.25}
                accent={colors.green}
                lowLabel="sell bias"
                highLabel="buy bias"
              />
            </div>
          </div>
        </div>
      </SceneShell>
    </AbsoluteFill>
  );
}

function VerdictScene({data}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 200}, durationInFrames: 40});
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 40% 30%, rgba(95,240,177,0.14), transparent 26%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`}}>
      <FloatingGrid frame={frame} />
      <SceneShell
        title="Outcome"
        subtitle="No trade was proposed. The safest call on this holding is to stay patient."
        frame={frame}
        duration={80}
        accent={colors.green}
      >
        <div style={{display: 'grid', gridTemplateColumns: '1.02fr 0.98fr', gap: 24, alignItems: 'stretch'}}>
          <div style={{padding: 22, borderRadius: 26, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
            <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18, color: colors.muted}}>Final call</div>
            <div style={{marginTop: 12, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 64, lineHeight: 1, fontWeight: 900, color: colors.green, transform: `translateY(${(1 - reveal) * 10}px)`}}>
              {data.verdict}
            </div>
            <div style={{marginTop: 12, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 26, lineHeight: 1.35, fontWeight: 700}}>
              {data.symbol} is a hold candidate, not an aggressive buy.
            </div>
            <div style={{marginTop: 16, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18, lineHeight: 1.55}}>
              Trend score is positive but weak, momentum is mixed, and the skill keeps the result read-only.
            </div>
            <div style={{marginTop: 22, display: 'flex', gap: 12, flexWrap: 'wrap'}}>
              <Chip active color={colors.green}>single-symbol</Chip>
              <Chip>0 trades proposed</Chip>
              <Chip>analysis_scope: portfolio-aware</Chip>
            </div>
          </div>
          <div style={{padding: 22, borderRadius: 26, background: colors.card2, border: `1px solid ${colors.stroke}`}}>
            <div style={{fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18, color: colors.muted}}>Agent prompt</div>
            <div style={{marginTop: 12, padding: 18, borderRadius: 18, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', color: colors.text, fontFamily: 'Consolas, monospace', fontSize: 18, lineHeight: 1.65}}>
              Use the DVRR Autopilot skill to analyze my Public.com portfolio.
              <br />
              Start in ANALYZE mode.
              <br />
              Pick one holding if needed.
              <br />
              Do not place trades.
            </div>
            <div style={{marginTop: 20, color: colors.muted, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 18, lineHeight: 1.45}}>
              This is the exact shape judges want: a clear prompt, a clear output, and a safe default.
            </div>
            <div style={{marginTop: 24, padding: 18, borderRadius: 18, background: 'rgba(95,240,177,0.08)', border: '1px solid rgba(95,240,177,0.24)'}}>
              <div style={{color: colors.green2, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 16, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase'}}>Reproducible</div>
              <div style={{marginTop: 8, color: colors.text, fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: 22, fontWeight: 700}}>
                `python bootstrap.py --symbol GOOG`
              </div>
            </div>
          </div>
        </div>
      </SceneShell>
    </AbsoluteFill>
  );
}

function FloatingGrid({frame}) {
  const drift = interpolate(frame, [0, 300], [0, 40]);
  const opacity = 0.22;
  const lines = [];
  for (let x = 0; x <= 1280; x += 96) {
    lines.push(<line key={`v-${x}`} x1={x} y1={0} x2={x} y2={720} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />);
  }
  for (let y = 0; y <= 720; y += 96) {
    lines.push(<line key={`h-${y}`} x1={0} y1={y} x2={1280} y2={y} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />);
  }
  return (
    <svg width={1280} height={720} style={{position: 'absolute', inset: 0, opacity}}>
      <g transform={`translate(${drift * 0.2}, ${drift * 0.1})`}>{lines}</g>
    </svg>
  );
}

export function DVRRShowcase(props) {
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`,
        color: colors.text,
      }}
    >
      <IntroBackground />
      <Sequence from={0} durationInFrames={70} premountFor={20}>
        <HeroScene data={props} />
      </Sequence>
      <Sequence from={55} durationInFrames={70} premountFor={20}>
        <PortfolioScene data={props} />
      </Sequence>
      <Sequence from={115} durationInFrames={75} premountFor={20}>
        <RegimeScene data={props} />
      </Sequence>
      <Sequence from={180} durationInFrames={75} premountFor={20}>
        <StockScene data={props} />
      </Sequence>
      <Sequence from={245} durationInFrames={75} premountFor={20}>
        <VerdictScene data={props} />
      </Sequence>
    </AbsoluteFill>
  );
}

function IntroBackground() {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const shift = interpolate(frame, [0, durationInFrames], [0, 50]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 18% 18%, rgba(110,231,255,0.16), transparent 24%), radial-gradient(circle at 80% 18%, rgba(95,240,177,0.12), transparent 26%), radial-gradient(circle at 82% 82%, rgba(122,163,255,0.12), transparent 26%), linear-gradient(180deg, ${colors.bg0} 0%, ${colors.bg1} 100%)`,
      }}
    >
      <svg width={1280} height={720} style={{position: 'absolute', inset: 0, opacity: 0.35}}>
        <circle cx={260 + shift * 0.4} cy={140} r={180} fill="rgba(110,231,255,0.08)" />
        <circle cx={1040 - shift * 0.2} cy={160} r={220} fill="rgba(95,240,177,0.08)" />
        <circle cx={990} cy={620 - shift * 0.3} r={260} fill="rgba(122,163,255,0.05)" />
      </svg>
    </AbsoluteFill>
  );
}
